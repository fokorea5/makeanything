"""
Trading Hub — SimBot / BaseBot / BotManager 테스트

공격자 관점:
- 봇 이중 시작 / 이중 중지
- 미등록 봇 시작/중지
- tick 중 예외 발생 시 error 전환
- on_init 실패 시 상태 처리
- BotManager 등록/해제 정합성
"""

import os
import sys
import asyncio
import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import database as db
from src.models.base_bot import BaseBot, BotManager, ExchangeAdapter, bot_manager
from src.models.sim_bot import SimBot, SimulationAdapter
from src.shared.types import (
    AssetInfo,
    BotConfig,
    BotStatus,
    OrderResult,
    TickerInfo,
    TradeSide,
)


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
    test_db_path = str(tmp_path / "test_bot.db")
    db.DB_PATH = test_db_path
    db._DATA_DIR = str(tmp_path)
    await db.init_db()
    # BotManager 초기화
    bot_manager._bots.clear()
    yield


def _make_config(**kwargs) -> BotConfig:
    """테스트용 BotConfig 생성."""
    defaults = {
        "symbol": "BTC/USDT",
        "strategy": "simple_ma",
        "interval": 1,  # 1초 (테스트용)
        "params": {"short_window": 3, "long_window": 7},
    }
    defaults.update(kwargs)
    return BotConfig(**defaults)


# ──────────────────────────────────────────────
# SimulationAdapter 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sim_adapter_initial_balance():
    """SimulationAdapter 초기 잔고 확인."""
    adapter = SimulationAdapter()
    balances = await adapter.get_balance()
    currencies = {a.currency: a for a in balances}
    assert "USDT" in currencies
    assert currencies["USDT"].balance == 10000.0
    assert "BTC" in currencies
    assert currencies["BTC"].balance == 0.0


@pytest.mark.asyncio
async def test_sim_adapter_get_ticker():
    """시세 조회: 유효한 TickerInfo 반환."""
    adapter = SimulationAdapter()
    ticker = await adapter.get_ticker("BTC/USDT")
    assert ticker.symbol == "BTC/USDT"
    assert ticker.price > 0
    # 기준가 45000 +/- 2%
    assert 44100 <= ticker.price <= 45900


@pytest.mark.asyncio
async def test_sim_adapter_get_ticker_unknown_symbol():
    """알 수 없는 심볼: 기본가 100 기준 변동."""
    adapter = SimulationAdapter()
    ticker = await adapter.get_ticker("UNKNOWN/TEST")
    assert ticker.symbol == "UNKNOWN/TEST"
    assert ticker.price > 0
    assert 98 <= ticker.price <= 102


@pytest.mark.asyncio
async def test_sim_adapter_place_buy_order():
    """매수 주문: 잔고 변동 확인."""
    adapter = SimulationAdapter()
    # BTC/USDT 매수
    order = await adapter.place_order(
        symbol="BTC/USDT",
        side=TradeSide.buy,
        quantity=0.1,
        price=45000.0,
    )
    assert order.status == "filled"
    assert order.side == TradeSide.buy
    assert order.quantity == 0.1

    # 잔고 확인: USDT 감소, BTC 증가
    balances = await adapter.get_balance()
    currencies = {a.currency: a for a in balances}
    assert currencies["USDT"].balance < 10000.0
    assert currencies["BTC"].balance == 0.1


@pytest.mark.asyncio
async def test_sim_adapter_place_sell_insufficient_balance():
    """잔고 부족 매도: 잔고 변동 없음 (경고만)."""
    adapter = SimulationAdapter()
    # BTC 잔고 0인데 매도 시도
    initial_balances = await adapter.get_balance()
    order = await adapter.place_order(
        symbol="BTC/USDT",
        side=TradeSide.sell,
        quantity=1.0,
        price=45000.0,
    )
    # 주문은 생성되지만 잔고는 변하지 않아야 함
    assert order.status == "filled"
    after_balances = await adapter.get_balance()
    currencies_after = {a.currency: a for a in after_balances}
    assert currencies_after["BTC"].balance == 0.0


@pytest.mark.asyncio
async def test_sim_adapter_cancel_order():
    """시뮬레이션 주문 취소: 항상 True."""
    adapter = SimulationAdapter()
    result = await adapter.cancel_order("fake-order-id")
    assert result is True


@pytest.mark.asyncio
async def test_sim_adapter_get_order_status():
    """시뮬레이션 주문 상태: 항상 filled."""
    adapter = SimulationAdapter()
    status = await adapter.get_order_status("fake-order-id")
    assert status == "filled"


# ──────────────────────────────────────────────
# SimBot 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_simbot_creation():
    """SimBot 생성 및 초기 상태."""
    config = _make_config()
    bot = SimBot(bot_id=1, name="TestSimBot", config=config)
    assert bot.bot_id == 1
    assert bot.name == "TestSimBot"
    assert bot.status == BotStatus.idle
    assert isinstance(bot.adapter, SimulationAdapter)


@pytest.mark.asyncio
async def test_simbot_on_init():
    """SimBot on_init: DB에 초기 자산 저장."""
    # DB에 봇 먼저 생성
    row = await db.create_bot(name="InitBot", exchange="simulation", bot_type="custom", config={})
    config = _make_config()
    bot = SimBot(bot_id=row["id"], name="InitBot", config=config)
    await bot.on_init()

    # 자산이 DB에 저장되었는지 확인
    assets = await db.get_assets(bot_id=row["id"])
    assert len(assets) >= 1  # 최소 USDT
    currencies = [a["currency"] for a in assets]
    assert "USDT" in currencies


@pytest.mark.asyncio
async def test_simbot_start_stop():
    """SimBot 시작/중지 생명주기."""
    row = await db.create_bot(name="LifecycleBot", exchange="simulation", bot_type="custom", config={})
    config = _make_config(interval=1)
    bot = SimBot(bot_id=row["id"], name="LifecycleBot", config=config)

    # 시작
    await bot.start()
    assert bot.status == BotStatus.running
    assert bot.started_at is not None
    assert bot._task is not None

    # 잠시 대기 (tick 실행 기회 부여)
    await asyncio.sleep(0.2)

    # 중지
    await bot.stop()
    assert bot.status == BotStatus.stopped
    assert bot._task is None


@pytest.mark.asyncio
async def test_simbot_double_start():
    """이미 running인 봇을 다시 start: 무시."""
    row = await db.create_bot(name="DoubleStart", exchange="simulation", bot_type="custom", config={})
    config = _make_config(interval=1)
    bot = SimBot(bot_id=row["id"], name="DoubleStart", config=config)

    await bot.start()
    assert bot.status == BotStatus.running

    # 두 번째 start — 경고만, 상태 유지
    await bot.start()
    assert bot.status == BotStatus.running

    await bot.stop()


@pytest.mark.asyncio
async def test_simbot_stop_when_not_running():
    """running이 아닌 봇 중지 시도: 무시."""
    config = _make_config()
    bot = SimBot(bot_id=999, name="NotRunning", config=config)
    assert bot.status == BotStatus.idle
    await bot.stop()  # 경고만, 에러 없음
    assert bot.status == BotStatus.idle


@pytest.mark.asyncio
async def test_simbot_uptime():
    """running 상태에서 uptime_seconds > 0."""
    row = await db.create_bot(name="UptimeBot", exchange="simulation", bot_type="custom", config={})
    config = _make_config(interval=1)
    bot = SimBot(bot_id=row["id"], name="UptimeBot", config=config)

    # idle 상태에서는 None
    assert bot.uptime_seconds is None

    await bot.start()
    await asyncio.sleep(0.1)
    assert bot.uptime_seconds is not None
    assert bot.uptime_seconds >= 0

    await bot.stop()
    # stopped 상태에서는 None
    assert bot.uptime_seconds is None


# ──────────────────────────────────────────────
# BotManager 테스트
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bot_manager_register_and_get():
    """BotManager 등록/조회."""
    mgr = BotManager()
    config = _make_config()
    bot = SimBot(bot_id=100, name="MgrBot", config=config)
    mgr.register(bot)

    assert mgr.get(100) is bot
    assert mgr.get(999) is None
    assert len(mgr.get_all()) == 1


@pytest.mark.asyncio
async def test_bot_manager_unregister():
    """BotManager 해제."""
    mgr = BotManager()
    config = _make_config()
    bot = SimBot(bot_id=200, name="UnregBot", config=config)
    mgr.register(bot)
    assert mgr.get(200) is not None

    mgr.unregister(200)
    assert mgr.get(200) is None


@pytest.mark.asyncio
async def test_bot_manager_unregister_nonexistent():
    """존재하지 않는 봇 해제: 에러 없음."""
    mgr = BotManager()
    mgr.unregister(999)  # 에러 없어야 함


@pytest.mark.asyncio
async def test_bot_manager_start_unregistered():
    """미등록 봇 시작 시 ValueError."""
    mgr = BotManager()
    with pytest.raises(ValueError, match="not registered"):
        await mgr.start_bot(999)


@pytest.mark.asyncio
async def test_bot_manager_stop_unregistered():
    """미등록 봇 중지 시 ValueError."""
    mgr = BotManager()
    with pytest.raises(ValueError, match="not registered"):
        await mgr.stop_bot(999)


@pytest.mark.asyncio
async def test_bot_manager_start_stop():
    """BotManager를 통한 봇 시작/중지."""
    row = await db.create_bot(name="MgrLifecycle", exchange="simulation", bot_type="custom", config={})
    mgr = BotManager()
    config = _make_config(interval=1)
    bot = SimBot(bot_id=row["id"], name="MgrLifecycle", config=config)
    mgr.register(bot)

    result = await mgr.start_bot(row["id"])
    assert result.status == BotStatus.running

    await asyncio.sleep(0.1)

    result = await mgr.stop_bot(row["id"])
    assert result.status == BotStatus.stopped


@pytest.mark.asyncio
async def test_bot_manager_stop_all():
    """모든 봇 중지."""
    mgr = BotManager()
    bots = []
    for i in range(3):
        row = await db.create_bot(name=f"StopAll{i}", exchange="simulation", bot_type="custom", config={})
        config = _make_config(interval=1)
        bot = SimBot(bot_id=row["id"], name=f"StopAll{i}", config=config)
        mgr.register(bot)
        bots.append(bot)

    # 2개만 시작
    await mgr.start_bot(bots[0].bot_id)
    await mgr.start_bot(bots[1].bot_id)
    await asyncio.sleep(0.1)

    await mgr.stop_all()

    for bot in bots:
        assert bot.status in (BotStatus.idle, BotStatus.stopped)


# ──────────────────────────────────────────────
# 에러 핸들링 테스트
# ──────────────────────────────────────────────

class _FailingAdapter(ExchangeAdapter):
    """on_init에서 실패하는 어댑터."""
    async def get_balance(self):
        raise RuntimeError("Adapter failure")
    async def get_ticker(self, symbol):
        raise RuntimeError("Adapter failure")
    async def place_order(self, symbol, side, quantity, price=None):
        raise RuntimeError("Adapter failure")
    async def cancel_order(self, order_id):
        return False
    async def get_order_status(self, order_id):
        return "unknown"


class _FailingBot(BaseBot):
    """on_init에서 실패하는 봇."""
    async def on_init(self):
        raise RuntimeError("Init failed!")
    async def on_tick(self):
        pass
    async def on_stop(self):
        pass


class _TickFailBot(BaseBot):
    """on_tick에서 실패하는 봇."""
    async def on_init(self):
        pass
    async def on_tick(self):
        raise RuntimeError("Tick exploded!")
    async def on_stop(self):
        pass


@pytest.mark.asyncio
async def test_bot_start_on_init_failure():
    """on_init 실패 시 status → error."""
    adapter = SimulationAdapter()
    bot = _FailingBot(bot_id=500, name="FailInit", config=_make_config(), adapter=adapter)
    with pytest.raises(RuntimeError, match="Init failed"):
        await bot.start()
    assert bot.status == BotStatus.error
    assert bot.error_message == "Init failed!"


@pytest.mark.asyncio
async def test_bot_tick_failure_sets_error():
    """on_tick 예외 시 status → error."""
    adapter = SimulationAdapter()
    bot = _TickFailBot(bot_id=501, name="FailTick", config=_make_config(interval=0), adapter=adapter)
    await bot.start()
    # tick이 실행될 시간
    await asyncio.sleep(0.3)
    assert bot.status == BotStatus.error
    assert "Tick exploded" in bot.error_message
