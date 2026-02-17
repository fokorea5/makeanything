"""
Trading Hub — FastAPI API 엔드포인트 테스트 (TestClient)

공격자 관점:
- 잘못된 요청 본문 (필수 필드 누락, 잘못된 타입)
- 존재하지 않는 리소스 접근
- 경계값 (빈 이름, 음수 ID, page=0)
- API 응답에 API 키가 포함되지 않는지 확인 (보안)
"""

import os
import sys
import asyncio
import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 환경변수 설정 (앱 로드 전)
from cryptography.fernet import Fernet

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""

from httpx import AsyncClient, ASGITransport
from src.db import database as db
from src.models.base_bot import bot_manager


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_test_db(tmp_path):
    """각 테스트마다 새 DB."""
    test_db_path = str(tmp_path / "test_api.db")
    db.DB_PATH = test_db_path
    db._DATA_DIR = str(tmp_path)
    await db.init_db()
    bot_manager._bots.clear()
    yield


@pytest.fixture
async def client():
    """httpx AsyncClient with FastAPI app."""
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ──────────────────────────────────────────────
# Bot API 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_bot_success(client):
    """POST /api/bots — 정상 봇 생성."""
    resp = await client.post("/api/bots", json={
        "name": "TestBot",
        "exchange": "simulation",
        "type": "custom",
        "config": {
            "symbol": "BTC/KRW",
            "strategy": "simple_ma",
            "interval": 10,
            "params": {},
        },
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "TestBot"
    assert data["exchange"] == "simulation"
    assert data["status"] == "idle"
    # API 키가 응답에 없어야 함
    assert "api_key_encrypted" not in data
    assert "api_secret_encrypted" not in data
    assert "api_key" not in data
    assert "api_secret" not in data


@pytest.mark.asyncio
async def test_create_bot_empty_name(client):
    """POST /api/bots — 빈 이름: 400."""
    resp = await client.post("/api/bots", json={
        "name": "   ",
        "exchange": "simulation",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_bot_missing_exchange(client):
    """POST /api/bots — exchange 누락: 422."""
    resp = await client.post("/api/bots", json={
        "name": "NoExchange",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_bot_invalid_exchange(client):
    """POST /api/bots — 잘못된 exchange 값: 422."""
    resp = await client.post("/api/bots", json={
        "name": "BadExchange",
        "exchange": "invalid_exchange_xyz",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_bots_empty(client):
    """GET /api/bots — 봇 없을 때 빈 리스트."""
    resp = await client.get("/api/bots")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_bots_after_create(client):
    """GET /api/bots — 봇 생성 후 목록에 포함."""
    await client.post("/api/bots", json={
        "name": "ListBot",
        "exchange": "simulation",
    })
    resp = await client.get("/api/bots")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    names = [b["name"] for b in data]
    assert "ListBot" in names


@pytest.mark.asyncio
async def test_get_bot_detail(client):
    """GET /api/bots/{id} — 봇 상세 조회."""
    create_resp = await client.post("/api/bots", json={
        "name": "DetailBot",
        "exchange": "simulation",
    })
    bot_id = create_resp.json()["id"]

    resp = await client.get(f"/api/bots/{bot_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "DetailBot"


@pytest.mark.asyncio
async def test_get_bot_not_found(client):
    """GET /api/bots/99999 — 존재하지 않는 봇: 404."""
    resp = await client.get("/api/bots/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_bot_invalid_id(client):
    """GET /api/bots/-1 — 음수 ID: 400."""
    resp = await client.get("/api/bots/-1")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_start_bot(client):
    """PATCH /api/bots/{id}/start — 봇 시작."""
    create_resp = await client.post("/api/bots", json={
        "name": "StartBot",
        "exchange": "simulation",
        "config": {"symbol": "BTC/USDT", "interval": 60},
    })
    bot_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/bots/{bot_id}/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"

    # cleanup: stop
    await client.patch(f"/api/bots/{bot_id}/stop")


@pytest.mark.asyncio
async def test_start_bot_already_running(client):
    """PATCH /api/bots/{id}/start — 이미 running: 400."""
    create_resp = await client.post("/api/bots", json={
        "name": "DoubleStartBot",
        "exchange": "simulation",
        "config": {"symbol": "BTC/USDT", "interval": 60},
    })
    bot_id = create_resp.json()["id"]

    await client.patch(f"/api/bots/{bot_id}/start")

    resp = await client.patch(f"/api/bots/{bot_id}/start")
    assert resp.status_code == 400

    # cleanup
    await client.patch(f"/api/bots/{bot_id}/stop")


@pytest.mark.asyncio
async def test_stop_bot(client):
    """PATCH /api/bots/{id}/stop — 봇 중지."""
    create_resp = await client.post("/api/bots", json={
        "name": "StopBot",
        "exchange": "simulation",
        "config": {"symbol": "BTC/USDT", "interval": 60},
    })
    bot_id = create_resp.json()["id"]

    await client.patch(f"/api/bots/{bot_id}/start")
    resp = await client.patch(f"/api/bots/{bot_id}/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"


@pytest.mark.asyncio
async def test_stop_bot_not_running(client):
    """PATCH /api/bots/{id}/stop — running이 아닌 봇: 400."""
    create_resp = await client.post("/api/bots", json={
        "name": "IdleStopBot",
        "exchange": "simulation",
    })
    bot_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/bots/{bot_id}/stop")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_bot_status(client):
    """GET /api/bots/{id}/status — 봇 상태 조회."""
    create_resp = await client.post("/api/bots", json={
        "name": "StatusBot",
        "exchange": "simulation",
    })
    bot_id = create_resp.json()["id"]

    resp = await client.get(f"/api/bots/{bot_id}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "idle"
    assert data["name"] == "StatusBot"


@pytest.mark.asyncio
async def test_delete_bot(client):
    """DELETE /api/bots/{id} — 봇 삭제."""
    create_resp = await client.post("/api/bots", json={
        "name": "DeleteBot",
        "exchange": "simulation",
    })
    bot_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/bots/{bot_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # 삭제 후 조회 → 404
    resp = await client.get(f"/api/bots/{bot_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_running_bot(client):
    """DELETE — running 봇 삭제: 자동 중지 후 삭제."""
    create_resp = await client.post("/api/bots", json={
        "name": "DeleteRunning",
        "exchange": "simulation",
        "config": {"symbol": "BTC/USDT", "interval": 60},
    })
    bot_id = create_resp.json()["id"]

    await client.patch(f"/api/bots/{bot_id}/start")
    resp = await client.delete(f"/api/bots/{bot_id}")
    assert resp.status_code == 200

    resp = await client.get(f"/api/bots/{bot_id}")
    assert resp.status_code == 404


# ──────────────────────────────────────────────
# Trade API 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_trade_success(client):
    """POST /api/trades — 정상 거래 기록."""
    # 먼저 봇 생성
    bot_resp = await client.post("/api/bots", json={
        "name": "TradeTestBot",
        "exchange": "simulation",
    })
    bot_id = bot_resp.json()["id"]

    resp = await client.post("/api/trades", json={
        "bot_id": bot_id,
        "exchange": "simulation",
        "symbol": "BTC/KRW",
        "side": "buy",
        "price": 60000000,
        "quantity": 0.001,
        "total": 60000,
        "fee": 60,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["bot_id"] == bot_id
    assert data["side"] == "buy"
    assert data["price"] == 60000000


@pytest.mark.asyncio
async def test_create_trade_invalid_bot(client):
    """POST /api/trades — 존재하지 않는 봇 ID: 404."""
    resp = await client.post("/api/trades", json={
        "bot_id": 99999,
        "exchange": "simulation",
        "symbol": "BTC/KRW",
        "side": "buy",
        "price": 100,
        "quantity": 1,
        "total": 100,
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_trade_negative_price(client):
    """POST /api/trades — 음수 가격: 422."""
    bot_resp = await client.post("/api/bots", json={
        "name": "NegPriceBot",
        "exchange": "simulation",
    })
    resp = await client.post("/api/trades", json={
        "bot_id": bot_resp.json()["id"],
        "exchange": "simulation",
        "symbol": "BTC/KRW",
        "side": "buy",
        "price": -100,
        "quantity": 1,
        "total": -100,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_trades_with_filters(client):
    """GET /api/trades — 필터와 페이지네이션."""
    bot_resp = await client.post("/api/bots", json={
        "name": "FilterTradeBot",
        "exchange": "simulation",
    })
    bot_id = bot_resp.json()["id"]

    # 여러 거래 생성
    for i in range(5):
        await client.post("/api/trades", json={
            "bot_id": bot_id,
            "exchange": "simulation",
            "symbol": "BTC/KRW",
            "side": "buy" if i % 2 == 0 else "sell",
            "price": 50000 + i,
            "quantity": 0.01,
            "total": 500 + i,
            "fee": 0.5,
        })

    # 전체 조회
    resp = await client.get("/api/trades", params={"page": 1, "size": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 5

    # side 필터
    resp = await client.get("/api/trades", params={"side": "buy"})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["side"] == "buy"


@pytest.mark.asyncio
async def test_list_trades_invalid_side(client):
    """GET /api/trades?side=invalid — 잘못된 side: 400."""
    resp = await client.get("/api/trades", params={"side": "invalid"})
    assert resp.status_code == 400


# ──────────────────────────────────────────────
# Asset API 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_assets_empty(client):
    """GET /api/assets — 자산 없을 때 빈 리스트."""
    resp = await client.get("/api/assets")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_assets_with_data(client):
    """GET /api/assets — 자산 데이터 있을 때."""
    bot_resp = await client.post("/api/bots", json={
        "name": "AssetBot",
        "exchange": "simulation",
    })
    bot_id = bot_resp.json()["id"]
    await db.upsert_asset(bot_id=bot_id, currency="USDT", balance=10000, value_usd=10000)

    resp = await client.get("/api/assets")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["currency"] == "USDT"


@pytest.mark.asyncio
async def test_asset_summary(client):
    """GET /api/assets/summary — 자산 요약."""
    resp = await client.get("/api/assets/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_value_usd" in data
    assert "bot_count" in data
    assert "assets_by_currency" in data
    assert "assets_by_bot" in data


# ──────────────────────────────────────────────
# Alert API 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_test_alert(client):
    """POST /api/alerts/test — 테스트 알림."""
    resp = await client.post("/api/alerts/test", json={
        "message": "QA test alert",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


@pytest.mark.asyncio
async def test_send_test_alert_default_message(client):
    """POST /api/alerts/test — 기본 메시지."""
    resp = await client.post("/api/alerts/test", json={})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_alerts(client):
    """GET /api/alerts — 알림 목록."""
    # 알림 하나 생성
    await client.post("/api/alerts/test", json={"message": "list test"})

    resp = await client.get("/api/alerts", params={"page": 1, "size": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_alerts_invalid_type(client):
    """GET /api/alerts?type=invalid — 잘못된 type: 400."""
    resp = await client.get("/api/alerts", params={"type": "invalid_type"})
    assert resp.status_code == 400


# ──────────────────────────────────────────────
# 보안: API 키 노출 방지 확인
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bot_response_no_api_keys(client):
    """봇 API 응답에 api_key/api_secret이 절대 포함되지 않는지 확인."""
    resp = await client.post("/api/bots", json={
        "name": "SecretBot",
        "exchange": "simulation",
        "api_key": "super_secret_key_12345",
        "api_secret": "super_secret_secret_67890",
    })
    data = resp.json()

    # 응답에 API 키 관련 필드가 없어야 함
    assert "api_key" not in data
    assert "api_secret" not in data
    assert "api_key_encrypted" not in data
    assert "api_secret_encrypted" not in data

    # 목록에서도 확인
    bot_id = data["id"]
    list_resp = await client.get("/api/bots")
    for bot in list_resp.json():
        assert "api_key" not in bot
        assert "api_secret" not in bot
        assert "api_key_encrypted" not in bot
        assert "api_secret_encrypted" not in bot

    # 상세에서도 확인
    detail_resp = await client.get(f"/api/bots/{bot_id}")
    detail_data = detail_resp.json()
    assert "api_key" not in detail_data
    assert "api_secret" not in detail_data
    assert "api_key_encrypted" not in detail_data
    assert "api_secret_encrypted" not in detail_data


# ──────────────────────────────────────────────
# 루트 리다이렉트 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_root_redirect(client):
    """GET / — 대시보드로 리다이렉트 또는 메시지."""
    resp = await client.get("/", follow_redirects=False)
    # 리다이렉트 또는 JSON 메시지
    assert resp.status_code in (200, 301, 302, 307, 308)
