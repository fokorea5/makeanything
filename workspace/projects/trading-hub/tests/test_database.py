"""
Trading Hub — DB CRUD 테스트

공격자 관점:
- 빈 값, NULL, 경계값, 중복 키, 존재하지 않는 레코드
- 페이지네이션 경계 (page=0, page=999, size=0)
- 외래키 제약 위반
"""

import os
import sys
import pytest
import asyncio

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import database as db


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """세션 범위의 이벤트 루프."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_test_db(tmp_path):
    """각 테스트마다 새 DB 사용."""
    test_db_path = str(tmp_path / "test.db")
    db.DB_PATH = test_db_path
    db._DATA_DIR = str(tmp_path)
    # fernet 캐시 초기화
    await db.init_db()
    yield
    # cleanup: DB 파일 삭제는 tmp_path가 알아서 처리


# ──────────────────────────────────────────────
# Bot CRUD 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_bot_normal():
    """정상적인 봇 생성."""
    row = await db.create_bot(
        name="TestBot",
        exchange="simulation",
        bot_type="custom",
        config={"symbol": "BTC/KRW", "strategy": "simple_ma", "interval": 10, "params": {}},
    )
    assert row is not None
    assert row["id"] >= 1
    assert row["name"] == "TestBot"
    assert row["exchange"] == "simulation"
    assert row["status"] == "idle"


@pytest.mark.asyncio
async def test_create_bot_with_api_keys():
    """API 키 포함 봇 생성 - 암호화 값이 DB에 저장되는지 확인."""
    row = await db.create_bot(
        name="KeyBot",
        exchange="upbit",
        bot_type="grid",
        config={},
        api_key_encrypted="enc_key_123",
        api_secret_encrypted="enc_secret_456",
    )
    assert row["api_key_encrypted"] == "enc_key_123"
    assert row["api_secret_encrypted"] == "enc_secret_456"


@pytest.mark.asyncio
async def test_get_bot_not_found():
    """존재하지 않는 봇 ID 조회 시 None 반환."""
    result = await db.get_bot(99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_bots_empty():
    """봇이 없을 때 빈 리스트 반환."""
    rows = await db.get_bots()
    assert rows == []


@pytest.mark.asyncio
async def test_get_bots_list():
    """여러 봇 생성 후 목록 조회."""
    await db.create_bot(name="Bot1", exchange="simulation", bot_type="custom", config={})
    await db.create_bot(name="Bot2", exchange="binance", bot_type="grid", config={})
    rows = await db.get_bots()
    assert len(rows) == 2
    assert rows[0]["name"] == "Bot1"
    assert rows[1]["name"] == "Bot2"


@pytest.mark.asyncio
async def test_update_bot_status():
    """봇 상태 변경."""
    row = await db.create_bot(name="StatusBot", exchange="simulation", bot_type="custom", config={})
    bot_id = row["id"]
    updated = await db.update_bot_status(bot_id, "running")
    assert updated["status"] == "running"


@pytest.mark.asyncio
async def test_delete_bot():
    """봇 삭제."""
    row = await db.create_bot(name="DeleteMe", exchange="simulation", bot_type="custom", config={})
    bot_id = row["id"]
    result = await db.delete_bot(bot_id)
    assert result is True
    assert await db.get_bot(bot_id) is None


@pytest.mark.asyncio
async def test_delete_bot_not_found():
    """존재하지 않는 봇 삭제 시 False."""
    result = await db.delete_bot(99999)
    assert result is False


# ──────────────────────────────────────────────
# Asset CRUD 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_asset_insert():
    """자산 최초 삽입."""
    bot = await db.create_bot(name="AssetBot", exchange="simulation", bot_type="custom", config={})
    asset = await db.upsert_asset(
        bot_id=bot["id"],
        currency="BTC",
        balance=1.5,
        locked=0.1,
        value_usd=67500.0,
    )
    assert asset["currency"] == "BTC"
    assert asset["balance"] == 1.5
    assert asset["locked"] == 0.1
    assert asset["value_usd"] == 67500.0


@pytest.mark.asyncio
async def test_upsert_asset_update():
    """동일 (bot_id, currency) 중복 삽입 시 업데이트."""
    bot = await db.create_bot(name="UpsertBot", exchange="simulation", bot_type="custom", config={})
    await db.upsert_asset(bot_id=bot["id"], currency="ETH", balance=10.0, value_usd=25000.0)
    updated = await db.upsert_asset(bot_id=bot["id"], currency="ETH", balance=20.0, value_usd=50000.0)
    assert updated["balance"] == 20.0
    assert updated["value_usd"] == 50000.0


@pytest.mark.asyncio
async def test_get_assets_filter_by_bot():
    """bot_id로 자산 필터."""
    bot1 = await db.create_bot(name="B1", exchange="simulation", bot_type="custom", config={})
    bot2 = await db.create_bot(name="B2", exchange="simulation", bot_type="custom", config={})
    await db.upsert_asset(bot_id=bot1["id"], currency="BTC", balance=1.0, value_usd=45000.0)
    await db.upsert_asset(bot_id=bot2["id"], currency="ETH", balance=5.0, value_usd=12500.0)
    assets = await db.get_assets(bot_id=bot1["id"])
    assert len(assets) == 1
    assert assets[0]["currency"] == "BTC"


@pytest.mark.asyncio
async def test_get_asset_summary_empty():
    """자산 없을 때 요약."""
    summary = await db.get_asset_summary()
    assert summary["total_value_usd"] == 0
    assert summary["assets_by_currency"] == {}
    assert summary["assets_by_bot"] == []


@pytest.mark.asyncio
async def test_get_asset_summary_with_data():
    """자산이 있을 때 요약 합산 정확성."""
    bot = await db.create_bot(name="SumBot", exchange="simulation", bot_type="custom", config={})
    await db.upsert_asset(bot_id=bot["id"], currency="BTC", balance=1.0, value_usd=45000.0)
    await db.upsert_asset(bot_id=bot["id"], currency="ETH", balance=10.0, value_usd=25000.0)
    summary = await db.get_asset_summary()
    assert summary["total_value_usd"] == 70000.0
    assert "BTC" in summary["assets_by_currency"]
    assert "ETH" in summary["assets_by_currency"]
    assert len(summary["assets_by_bot"]) == 1
    assert summary["assets_by_bot"][0]["total_value_usd"] == 70000.0


# ──────────────────────────────────────────────
# Trade CRUD 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_trade():
    """정상 거래 기록 저장."""
    bot = await db.create_bot(name="TradeBot", exchange="simulation", bot_type="custom", config={})
    trade = await db.create_trade(
        bot_id=bot["id"],
        exchange="simulation",
        symbol="BTC/KRW",
        side="buy",
        price=60000000.0,
        quantity=0.001,
        total=60000.0,
        fee=60.0,
    )
    assert trade["id"] >= 1
    assert trade["bot_id"] == bot["id"]
    assert trade["side"] == "buy"
    assert trade["price"] == 60000000.0


@pytest.mark.asyncio
async def test_get_trades_pagination():
    """거래 페이지네이션 동작 확인."""
    bot = await db.create_bot(name="PageBot", exchange="simulation", bot_type="custom", config={})
    for i in range(25):
        await db.create_trade(
            bot_id=bot["id"],
            exchange="simulation",
            symbol="BTC/KRW",
            side="buy",
            price=50000.0 + i,
            quantity=0.01,
            total=500.0 + i,
            fee=0.5,
        )
    result = await db.get_trades(page=1, size=10)
    assert len(result["items"]) == 10
    assert result["total"] == 25
    assert result["pages"] == 3
    assert result["page"] == 1

    result2 = await db.get_trades(page=3, size=10)
    assert len(result2["items"]) == 5


@pytest.mark.asyncio
async def test_get_trades_filter_by_side():
    """side 필터."""
    bot = await db.create_bot(name="FilterBot", exchange="simulation", bot_type="custom", config={})
    await db.create_trade(bot_id=bot["id"], exchange="simulation", symbol="BTC/KRW", side="buy", price=100, quantity=1, total=100, fee=0)
    await db.create_trade(bot_id=bot["id"], exchange="simulation", symbol="BTC/KRW", side="sell", price=110, quantity=1, total=110, fee=0)
    result = await db.get_trades(side="sell")
    assert result["total"] == 1
    assert result["items"][0]["side"] == "sell"


@pytest.mark.asyncio
async def test_get_trades_filter_by_symbol():
    """symbol 필터."""
    bot = await db.create_bot(name="SymBot", exchange="simulation", bot_type="custom", config={})
    await db.create_trade(bot_id=bot["id"], exchange="simulation", symbol="BTC/KRW", side="buy", price=100, quantity=1, total=100, fee=0)
    await db.create_trade(bot_id=bot["id"], exchange="simulation", symbol="ETH/USDT", side="buy", price=200, quantity=1, total=200, fee=0)
    result = await db.get_trades(symbol="ETH/USDT")
    assert result["total"] == 1
    assert result["items"][0]["symbol"] == "ETH/USDT"


# ──────────────────────────────────────────────
# Alert CRUD 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_alert():
    """알림 생성."""
    alert = await db.create_alert(
        alert_type="error",
        message="Test error",
        bot_id=None,
        sent=False,
    )
    assert alert["id"] >= 1
    assert alert["type"] == "error"
    assert alert["message"] == "Test error"
    assert alert["sent"] == 0  # SQLite stores as int


@pytest.mark.asyncio
async def test_update_alert_sent():
    """알림 전송 상태 업데이트."""
    alert = await db.create_alert(alert_type="large_trade", message="Big trade", sent=False)
    await db.update_alert_sent(alert["id"], True)
    # 확인 위해 직접 조회
    result = await db.get_alerts(page=1, size=100)
    found = [a for a in result["items"] if a["id"] == alert["id"]]
    assert len(found) == 1
    assert found[0]["sent"] == 1


@pytest.mark.asyncio
async def test_get_alerts_pagination():
    """알림 페이지네이션."""
    for i in range(15):
        await db.create_alert(alert_type="error", message=f"Error {i}")
    result = await db.get_alerts(page=1, size=10)
    assert len(result["items"]) == 10
    assert result["total"] == 15
    assert result["pages"] == 2


@pytest.mark.asyncio
async def test_get_alerts_filter_by_type():
    """알림 유형 필터."""
    await db.create_alert(alert_type="error", message="err")
    await db.create_alert(alert_type="large_trade", message="big")
    result = await db.get_alerts(alert_type="large_trade")
    assert result["total"] == 1
    assert result["items"][0]["type"] == "large_trade"


# ──────────────────────────────────────────────
# 경계값 & 실패 케이스 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_bot_empty_config():
    """빈 config dict로 봇 생성."""
    row = await db.create_bot(name="EmptyCfg", exchange="simulation", bot_type="custom", config={})
    assert row["config"] == "{}"


@pytest.mark.asyncio
async def test_upsert_asset_zero_balance():
    """잔고 0인 자산."""
    bot = await db.create_bot(name="ZeroBot", exchange="simulation", bot_type="custom", config={})
    asset = await db.upsert_asset(bot_id=bot["id"], currency="XRP", balance=0.0, value_usd=0.0)
    assert asset["balance"] == 0.0


@pytest.mark.asyncio
async def test_get_trades_empty():
    """거래 없을 때 빈 결과."""
    result = await db.get_trades()
    assert result["items"] == []
    assert result["total"] == 0
    assert result["pages"] == 1  # max(1, ...)
