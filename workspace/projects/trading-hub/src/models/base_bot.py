"""
Trading Hub — 봇 프레임워크

BaseBot 추상 클래스: 모든 봇이 구현해야 하는 생명주기(init/tick/stop).
ExchangeAdapter 추상 클래스: 거래소별 통일 인터페이스.
BotManager: 봇 인스턴스 관리, 시작/중지.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from src.shared.types import (
    AssetInfo,
    BotConfig,
    BotStatus,
    OrderResult,
    TickerInfo,
    TradeSide,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# ExchangeAdapter (추상 인터페이스)
# ──────────────────────────────────────────────

class ExchangeAdapter(ABC):
    """거래소별 구현을 통일하는 인터페이스."""

    @abstractmethod
    async def get_balance(self) -> List[AssetInfo]:
        """잔고 목록 반환."""
        ...

    @abstractmethod
    async def get_ticker(self, symbol: str) -> TickerInfo:
        """시세 정보 반환."""
        ...

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: TradeSide,
        quantity: float,
        price: Optional[float] = None,
    ) -> OrderResult:
        """주문 실행."""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """주문 취소."""
        ...

    @abstractmethod
    async def get_order_status(self, order_id: str) -> str:
        """주문 상태 반환 (filled, pending, cancelled)."""
        ...


# ──────────────────────────────────────────────
# BaseBot (추상 클래스)
# ──────────────────────────────────────────────

class BaseBot(ABC):
    """모든 봇이 구현해야 하는 추상 클래스."""

    def __init__(
        self,
        bot_id: int,
        name: str,
        config: BotConfig,
        adapter: ExchangeAdapter,
    ) -> None:
        self.bot_id = bot_id
        self.name = name
        self.config = config
        self.adapter = adapter
        self.status: BotStatus = BotStatus.idle
        self.error_message: Optional[str] = None
        self.started_at: Optional[float] = None
        self.last_tick_at: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None

    # ── 추상 메서드 (서브클래스가 구현) ──

    @abstractmethod
    async def on_init(self) -> None:
        """봇 초기화. 거래소 연결, 설정 로드 등."""
        ...

    @abstractmethod
    async def on_tick(self) -> None:
        """주기적 실행 로직. 시세 확인, 전략 판단, 주문."""
        ...

    @abstractmethod
    async def on_stop(self) -> None:
        """정리 작업. 연결 해제, 열린 주문 처리."""
        ...

    # ── 구현된 메서드 ──

    async def start(self) -> None:
        """봇을 시작한다. status → running, on_init 호출, tick 루프 시작."""
        if self.status == BotStatus.running:
            logger.warning("Bot %s (%d) already running", self.name, self.bot_id)
            return

        try:
            self.status = BotStatus.running
            self.error_message = None
            self.started_at = time.time()
            await self.on_init()
            self._task = asyncio.create_task(self._run_loop())
            logger.info("Bot started: %s (%d)", self.name, self.bot_id)
        except Exception as e:
            self.status = BotStatus.error
            self.error_message = str(e)
            logger.error("Bot %s (%d) start failed: %s", self.name, self.bot_id, e)
            raise

    async def stop(self) -> None:
        """봇을 중지한다. status → stopped, on_stop 호출, tick 루프 중지."""
        if self.status not in (BotStatus.running, BotStatus.error):
            logger.warning("Bot %s (%d) not running (status=%s)", self.name, self.bot_id, self.status)
            return

        self.status = BotStatus.stopped
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        try:
            await self.on_stop()
        except Exception as e:
            logger.error("Bot %s (%d) on_stop error: %s", self.name, self.bot_id, e)

        self._task = None
        self.started_at = None
        logger.info("Bot stopped: %s (%d)", self.name, self.bot_id)

    async def _run_loop(self) -> None:
        """tick 루프. status == running 인 동안 on_tick 반복."""
        interval = self.config.interval
        while self.status == BotStatus.running:
            try:
                await self.on_tick()
                self.last_tick_at = datetime.utcnow()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.status = BotStatus.error
                self.error_message = str(e)
                logger.error(
                    "Bot %s (%d) tick error: %s", self.name, self.bot_id, e
                )
                # 에러 시 루프 중지
                break
            await asyncio.sleep(interval)

    @property
    def uptime_seconds(self) -> Optional[float]:
        """실행 시간(초). running 상태가 아니면 None."""
        if self.started_at is not None and self.status == BotStatus.running:
            return time.time() - self.started_at
        return None


# ──────────────────────────────────────────────
# BotManager (봇 인스턴스 관리)
# ──────────────────────────────────────────────

class BotManager:
    """
    봇 인스턴스를 메모리에서 관리한다.
    봇 시작/중지, 상태 조회 등.
    """

    def __init__(self) -> None:
        self._bots: Dict[int, BaseBot] = {}

    def register(self, bot: BaseBot) -> None:
        """봇 인스턴스를 등록한다."""
        self._bots[bot.bot_id] = bot
        logger.info("BotManager: registered bot %s (%d)", bot.name, bot.bot_id)

    def unregister(self, bot_id: int) -> None:
        """봇 인스턴스를 해제한다."""
        if bot_id in self._bots:
            del self._bots[bot_id]
            logger.info("BotManager: unregistered bot %d", bot_id)

    def get(self, bot_id: int) -> Optional[BaseBot]:
        """봇 인스턴스를 가져온다."""
        return self._bots.get(bot_id)

    def get_all(self) -> List[BaseBot]:
        """모든 봇 인스턴스 목록."""
        return list(self._bots.values())

    async def start_bot(self, bot_id: int) -> BaseBot:
        """봇을 시작한다."""
        bot = self._bots.get(bot_id)
        if bot is None:
            raise ValueError(f"Bot {bot_id} not registered in BotManager")
        await bot.start()
        return bot

    async def stop_bot(self, bot_id: int) -> BaseBot:
        """봇을 중지한다."""
        bot = self._bots.get(bot_id)
        if bot is None:
            raise ValueError(f"Bot {bot_id} not registered in BotManager")
        await bot.stop()
        return bot

    async def stop_all(self) -> None:
        """모든 봇을 중지한다."""
        for bot in self._bots.values():
            if bot.status == BotStatus.running:
                try:
                    await bot.stop()
                except Exception as e:
                    logger.error("Failed to stop bot %d: %s", bot.bot_id, e)


# 전역 BotManager 싱글턴
bot_manager = BotManager()
