"""
Trading Hub — 시뮬레이션 봇

SimulationAdapter: 가짜 잔고/시세 생성 (실제 거래소 호출 없음).
SimBot: BaseBot 구현체. 랜덤 매매 시뮬레이션 (단순 이동평균 크로스 전략).
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from src.db import database as db
from src.models.base_bot import BaseBot, ExchangeAdapter
from src.shared.types import (
    AssetInfo,
    BotConfig,
    OrderResult,
    TickerInfo,
    TradeSide,
)

logger = logging.getLogger(__name__)

# 큰 거래 알림 임계값 (USD)
LARGE_TRADE_THRESHOLD = 1000.0


# ──────────────────────────────────────────────
# SimulationAdapter
# ──────────────────────────────────────────────

class SimulationAdapter(ExchangeAdapter):
    """
    시뮬레이션용 거래소 어댑터.
    실제 거래소 호출 없이 가짜 잔고/시세를 생성한다.
    """

    # @confidence: low — 시뮬레이션 가격 생성 로직

    def __init__(self) -> None:
        # 초기 잔고: 시뮬레이션용
        self._balances: Dict[str, AssetInfo] = {
            "USDT": AssetInfo(currency="USDT", balance=10000.0, locked=0.0),
            "BTC": AssetInfo(currency="BTC", balance=0.0, locked=0.0),
        }
        # 시세 기준가 (변동 시뮬레이션용)
        self._base_prices: Dict[str, float] = {
            "BTC/USDT": 45000.0,
            "ETH/USDT": 2500.0,
            "BTC/KRW": 60000000.0,
        }
        self._current_prices: Dict[str, float] = dict(self._base_prices)

    async def get_balance(self) -> List[AssetInfo]:
        """가짜 잔고 반환."""
        return list(self._balances.values())

    async def get_ticker(self, symbol: str) -> TickerInfo:
        """가짜 시세 생성 (기준가 +/- 2% 랜덤 변동)."""
        base = self._base_prices.get(symbol, 100.0)
        change_pct = random.uniform(-0.02, 0.02)
        price = base * (1 + change_pct)
        self._current_prices[symbol] = price

        return TickerInfo(
            symbol=symbol,
            price=round(price, 2),
            volume_24h=round(random.uniform(100, 10000), 2),
            change_24h=round(change_pct * 100, 4),
        )

    async def place_order(
        self,
        symbol: str,
        side: TradeSide,
        quantity: float,
        price: Optional[float] = None,
    ) -> OrderResult:
        """시뮬레이션 주문 실행. 즉시 체결."""
        if price is None:
            ticker = await self.get_ticker(symbol)
            price = ticker.price

        # 통화 추출 (예: BTC/USDT → base=BTC, quote=USDT)
        parts = symbol.split("/")
        base_currency = parts[0] if len(parts) == 2 else symbol[:3]
        quote_currency = parts[1] if len(parts) == 2 else symbol[3:]

        total = price * quantity
        fee = total * 0.001  # 0.1% 수수료

        if side == TradeSide.buy:
            # quote 통화 차감, base 통화 증가
            quote_asset = self._balances.get(quote_currency)
            if quote_asset and quote_asset.balance >= total + fee:
                quote_asset.balance -= total + fee
                base_asset = self._balances.setdefault(
                    base_currency,
                    AssetInfo(currency=base_currency, balance=0.0, locked=0.0),
                )
                # setdefault returns existing so need to handle AssetInfo immutability
                if base_currency not in self._balances or self._balances[base_currency].balance == 0.0:
                    self._balances[base_currency] = AssetInfo(
                        currency=base_currency,
                        balance=quantity,
                        locked=0.0,
                    )
                else:
                    existing = self._balances[base_currency]
                    self._balances[base_currency] = AssetInfo(
                        currency=base_currency,
                        balance=existing.balance + quantity,
                        locked=existing.locked,
                    )
                self._balances[quote_currency] = AssetInfo(
                    currency=quote_currency,
                    balance=quote_asset.balance,
                    locked=quote_asset.locked,
                )
            else:
                logger.warning("Insufficient %s balance for buy", quote_currency)
        else:
            # sell: base 통화 차감, quote 통화 증가
            base_asset = self._balances.get(base_currency)
            if base_asset and base_asset.balance >= quantity:
                self._balances[base_currency] = AssetInfo(
                    currency=base_currency,
                    balance=base_asset.balance - quantity,
                    locked=base_asset.locked,
                )
                quote_asset = self._balances.get(quote_currency)
                if quote_asset:
                    self._balances[quote_currency] = AssetInfo(
                        currency=quote_currency,
                        balance=quote_asset.balance + total - fee,
                        locked=quote_asset.locked,
                    )
                else:
                    self._balances[quote_currency] = AssetInfo(
                        currency=quote_currency,
                        balance=total - fee,
                        locked=0.0,
                    )
            else:
                logger.warning("Insufficient %s balance for sell", base_currency)

        return OrderResult(
            order_id=str(uuid.uuid4())[:8],
            symbol=symbol,
            side=side,
            price=round(price, 2),
            quantity=quantity,
            total=round(total, 2),
            fee=round(fee, 2),
            status="filled",
        )

    async def cancel_order(self, order_id: str) -> bool:
        """시뮬레이션 주문 취소. 항상 성공."""
        return True

    async def get_order_status(self, order_id: str) -> str:
        """시뮬레이션 주문 상태. 항상 filled."""
        return "filled"


# ──────────────────────────────────────────────
# SimBot
# ──────────────────────────────────────────────

class SimBot(BaseBot):
    """
    시뮬레이션 봇. BaseBot 구현체.
    단순 이동평균 크로스 전략으로 랜덤 매매를 시뮬레이션한다.
    거래 결과를 DB에 저장하고, 큰 거래 발생 시 알림을 트리거한다.
    """

    def __init__(self, bot_id: int, name: str, config: BotConfig) -> None:
        adapter = SimulationAdapter()
        super().__init__(bot_id=bot_id, name=name, config=config, adapter=adapter)
        self._price_history: List[float] = []
        self._short_window = config.params.get("short_window", 3)
        self._long_window = config.params.get("long_window", 7)

    async def on_init(self) -> None:
        """봇 초기화. 초기 자산을 DB에 저장."""
        logger.info("SimBot %s (%d) initializing...", self.name, self.bot_id)
        balances = await self.adapter.get_balance()
        for asset in balances:
            value_usd = asset.balance  # USDT = 1:1 USD 가정
            if asset.currency == "BTC":
                ticker = await self.adapter.get_ticker(self.config.symbol)
                value_usd = asset.balance * ticker.price
            await db.upsert_asset(
                bot_id=self.bot_id,
                currency=asset.currency,
                balance=asset.balance,
                locked=asset.locked,
                value_usd=round(value_usd, 2),
            )
        logger.info("SimBot %s (%d) initialized", self.name, self.bot_id)

    async def on_tick(self) -> None:
        """
        주기적 실행.
        1. 시세 확인
        2. 이동평균 크로스 전략 판단
        3. 매매 실행
        4. DB 갱신
        """
        symbol = self.config.symbol
        ticker = await self.adapter.get_ticker(symbol)
        current_price = ticker.price
        self._price_history.append(current_price)

        # 충분한 가격 데이터가 쌓일 때까지 대기
        if len(self._price_history) < self._long_window:
            logger.debug(
                "SimBot %s: collecting price data (%d/%d)",
                self.name,
                len(self._price_history),
                self._long_window,
            )
            return

        # 최근 가격만 유지
        if len(self._price_history) > self._long_window * 3:
            self._price_history = self._price_history[-self._long_window * 3:]

        # 이동평균 계산
        short_ma = sum(self._price_history[-self._short_window:]) / self._short_window
        long_ma = sum(self._price_history[-self._long_window:]) / self._long_window

        # 거래 결정
        parts = symbol.split("/")
        base_currency = parts[0] if len(parts) == 2 else symbol[:3]
        quote_currency = parts[1] if len(parts) == 2 else symbol[3:]

        sim_adapter: SimulationAdapter = self.adapter  # type: ignore
        side: Optional[TradeSide] = None

        if short_ma > long_ma:
            # 골든 크로스 → 매수
            quote_asset = sim_adapter._balances.get(quote_currency)
            if quote_asset and quote_asset.balance > current_price * 0.001:
                # 잔고의 10%만 사용
                trade_amount = quote_asset.balance * 0.1
                quantity = trade_amount / current_price
                if quantity > 0:
                    side = TradeSide.buy
        elif short_ma < long_ma:
            # 데드 크로스 → 매도
            base_asset = sim_adapter._balances.get(base_currency)
            if base_asset and base_asset.balance > 0.0001:
                # 보유량의 50% 매도
                quantity = base_asset.balance * 0.5
                if quantity > 0:
                    side = TradeSide.sell

        if side is not None:
            order = await self.adapter.place_order(
                symbol=symbol,
                side=side,
                quantity=round(quantity, 8),
                price=current_price,
            )

            # DB에 거래 기록 저장
            await db.create_trade(
                bot_id=self.bot_id,
                exchange="simulation",
                symbol=symbol,
                side=order.side.value,
                price=order.price,
                quantity=order.quantity,
                total=order.total,
                fee=order.fee,
                timestamp=datetime.utcnow().isoformat(),
            )

            logger.info(
                "SimBot %s: %s %s %.8f @ %.2f (total: %.2f)",
                self.name,
                order.side.value.upper(),
                symbol,
                order.quantity,
                order.price,
                order.total,
            )

            # 큰 거래 알림 트리거
            if order.total >= LARGE_TRADE_THRESHOLD:
                await db.create_alert(
                    alert_type="large_trade",
                    message=(
                        f"[TRADE] {self.name}: {symbol} "
                        f"{order.side.value.upper()} ${order.total:,.2f}"
                    ),
                    bot_id=self.bot_id,
                    sent=False,
                )

        # 자산 DB 갱신
        balances = await self.adapter.get_balance()
        for asset in balances:
            value_usd = asset.balance
            if asset.currency != "USDT" and asset.currency != "KRW":
                value_usd = asset.balance * current_price
            await db.upsert_asset(
                bot_id=self.bot_id,
                currency=asset.currency,
                balance=round(asset.balance, 8),
                locked=round(asset.locked, 8),
                value_usd=round(value_usd, 2),
            )

    async def on_stop(self) -> None:
        """봇 정리. 가격 히스토리 초기화."""
        logger.info("SimBot %s (%d) stopping...", self.name, self.bot_id)
        self._price_history.clear()
