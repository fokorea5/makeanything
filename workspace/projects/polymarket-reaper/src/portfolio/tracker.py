"""
Polymarket Reaper Bot v1.1 -- Portfolio Tracker

Tracks real and virtual positions, computes P&L and drawdown metrics.
Syncs with Data API for live positions and maintains in-memory virtual
positions for DRY_RUN mode.

DESIGN.md 3.15 / AC-34
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from config import Config
from src.shared.types import Position, TradeResult, TradeStatus

logger = logging.getLogger("reaper.portfolio.tracker")


# ---------------------------------------------------------------------------
# PortfolioTracker
# ---------------------------------------------------------------------------

class PortfolioTracker:
    """Tracks positions and computes portfolio-level risk metrics.

    DESIGN.md 3.15 / AC-34

    - Syncs with Data API every 120 s (via engine)
    - Maintains virtual positions in DRY_RUN mode
    - Provides bankroll, exposure, drawdown to Risk Sentinel & Governor

    Usage::

        tracker = PortfolioTracker(data_client)
        await tracker.sync_positions()
        dd = await tracker.get_current_drawdown()
    """

    def __init__(self, data_client: Any | None = None) -> None:
        self._data_client = data_client
        # condition_id -> Position
        self._positions: dict[str, Position] = {}
        # Virtual positions for DRY_RUN
        self._virtual_positions: dict[str, Position] = {}
        # Portfolio value tracking
        self._bankroll: float = 0.0
        self._peak_bankroll: float = 0.0
        self._daily_pnl: float = 0.0
        self._daily_pnl_reset_date: str = ""
        # Pending orders tracking (condition_id set)
        self._pending_orders: set[str] = set()

    # ------------------------------------------------------------------
    # Synchronisation (AC-34, 120s cycle from engine)
    # ------------------------------------------------------------------

    async def sync_positions(self, retries: int = 3) -> None:
        """Synchronise positions with the Data API.

        In DRY_RUN mode, only updates prices for virtual positions
        but does not fetch live positions. Retries on failure with
        exponential backoff.
        """
        if Config.DRY_RUN:
            logger.debug("DRY_RUN: skipping Data API sync, using virtual positions")
            return

        if self._data_client is None:
            logger.warning("No data_client -- cannot sync positions")
            return

        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                raw_positions = await self._data_client.get_positions(Config.WALLET_ADDRESS)
                new_positions: dict[str, Position] = {}
                for pdata in raw_positions:
                    if pdata.size <= 0:
                        continue
                    pos = Position(
                        condition_id=pdata.condition_id,
                        token_id=pdata.asset,
                        outcome=pdata.outcome,
                        size=pdata.size,
                        avg_price=pdata.avg_price,
                        current_price=pdata.current_price,
                        unrealized_pnl=pdata.unrealized_pnl,
                        market_question=pdata.title,
                        is_dry_run=False,
                    )
                    new_positions[pdata.condition_id] = pos

                self._positions = new_positions

                # Update bankroll from portfolio value
                portfolio_value = await self._data_client.get_portfolio_value(Config.WALLET_ADDRESS)
                if portfolio_value > 0:
                    self._bankroll = portfolio_value
                    if portfolio_value > self._peak_bankroll:
                        self._peak_bankroll = portfolio_value

                logger.info(
                    "Portfolio synced  positions=%d  bankroll=%.2f  peak=%.2f",
                    len(self._positions), self._bankroll, self._peak_bankroll,
                )
                return  # 성공 시 즉시 반환
            except Exception as e:  # noqa: BLE001
                last_error = e
                if attempt < retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        "Sync attempt %d/%d failed: %s — retrying in %ds",
                        attempt + 1, retries, e, wait,
                    )
                    await asyncio.sleep(wait)

        logger.error("Failed to sync positions after %d attempts: %s", retries, last_error)

    # ------------------------------------------------------------------
    # Position queries
    # ------------------------------------------------------------------

    async def get_position(self, condition_id: str) -> Position | None:
        """Get the current position for a market (real or virtual)."""
        if Config.DRY_RUN:
            return self._virtual_positions.get(condition_id)
        return self._positions.get(condition_id)

    async def get_all_positions(self) -> list[Position]:
        """Return all current positions."""
        if Config.DRY_RUN:
            return list(self._virtual_positions.values())
        return list(self._positions.values())

    # ------------------------------------------------------------------
    # Exposure & risk metrics
    # ------------------------------------------------------------------

    async def get_total_exposure(self) -> float:
        """Calculate total position exposure in USDC."""
        positions = await self.get_all_positions()
        return sum(pos.size * pos.current_price for pos in positions)

    async def get_market_exposure(self, condition_id: str) -> float:
        """Get exposure for a single market."""
        pos = await self.get_position(condition_id)
        if pos is None:
            return 0.0
        return pos.size * pos.current_price

    async def get_all_market_exposures(self) -> dict[str, float]:
        """Return condition_id -> exposure USDC for all positions."""
        positions = await self.get_all_positions()
        return {
            pos.condition_id: pos.size * pos.current_price
            for pos in positions
        }

    async def get_daily_pnl(self) -> float:
        """Return today's realised P&L (reset at UTC 00:00)."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self._daily_pnl_reset_date != today:
            self._daily_pnl = 0.0
            self._daily_pnl_reset_date = today
        return self._daily_pnl

    async def get_bankroll(self) -> float:
        """Return the current available bankroll (USDC)."""
        if Config.DRY_RUN and self._bankroll <= 0:
            # Default virtual bankroll for dry-run testing
            return 1000.0
        return self._bankroll

    async def get_peak_bankroll(self) -> float:
        """Return the historical peak bankroll."""
        if Config.DRY_RUN and self._peak_bankroll <= 0:
            return 1000.0
        return self._peak_bankroll

    async def get_current_drawdown(self) -> float:
        """Calculate current drawdown ratio (0.0 ~ 1.0).

        DD = (peak - current) / peak
        Used by both Frequency Governor (AC-29) and Risk Sentinel Layer 5 (AC-27).
        """
        peak = await self.get_peak_bankroll()
        current = await self.get_bankroll()
        if peak <= 0:
            return 0.0
        dd = (peak - current) / peak
        return max(0.0, min(1.0, dd))

    # ------------------------------------------------------------------
    # Order tracking (AC-39)
    # ------------------------------------------------------------------

    async def has_open_orders(self, condition_id: str) -> bool:
        """Check if there are pending/open orders for a market (AC-39)."""
        return condition_id in self._pending_orders

    def mark_order_pending(self, condition_id: str) -> None:
        """Mark a market as having a pending order."""
        self._pending_orders.add(condition_id)

    def clear_order_pending(self, condition_id: str) -> None:
        """Clear the pending order flag for a market."""
        self._pending_orders.discard(condition_id)

    def clear_all_pending_orders(self) -> None:
        """Clear all pending order flags (Circuit Breaker -- AC-26)."""
        self._pending_orders.clear()

    # ------------------------------------------------------------------
    # Virtual trade recording (DRY_RUN -- AC-33, AC-34)
    # ------------------------------------------------------------------

    async def record_virtual_trade(self, trade: TradeResult) -> None:
        """Update virtual positions based on a dry-run trade result."""
        if trade.status not in (TradeStatus.FILLED, TradeStatus.DRY_RUN):
            return

        cid = trade.condition_id
        existing = self._virtual_positions.get(cid)

        if trade.side.value == "BUY":
            if existing:
                # Average in
                total_size = existing.size + trade.size_tokens
                if total_size > 0:
                    avg_price = (
                        (existing.avg_price * existing.size)
                        + (trade.price * trade.size_tokens)
                    ) / total_size
                else:
                    avg_price = trade.price
                existing.size = total_size
                existing.avg_price = avg_price
                existing.current_price = trade.price
                existing.unrealized_pnl = (trade.price - avg_price) * total_size
            else:
                self._virtual_positions[cid] = Position(
                    condition_id=cid,
                    token_id=trade.token_id,
                    outcome="Yes" if "yes" in trade.token_id.lower() else "No",
                    size=trade.size_tokens,
                    avg_price=trade.price,
                    current_price=trade.price,
                    unrealized_pnl=0.0,
                    market_question="",
                    is_dry_run=True,
                )
        elif trade.side.value == "SELL":
            if existing:
                realized = (trade.price - existing.avg_price) * trade.size_tokens
                self._daily_pnl += realized
                existing.size -= trade.size_tokens
                if existing.size <= 0:
                    del self._virtual_positions[cid]
                else:
                    existing.current_price = trade.price
                    existing.unrealized_pnl = (
                        (trade.price - existing.avg_price) * existing.size
                    )

        # Update virtual bankroll
        if trade.side.value == "BUY":
            self._bankroll -= trade.cost_usdc
        elif trade.side.value == "SELL":
            self._bankroll += trade.cost_usdc

        if self._bankroll > self._peak_bankroll:
            self._peak_bankroll = self._bankroll

        logger.info(
            "Virtual trade recorded  market=%s  side=%s  size=%.4f  bankroll=%.2f",
            cid[:16] + "..." if len(cid) > 16 else cid,
            trade.side.value,
            trade.size_tokens,
            self._bankroll,
        )

    # ------------------------------------------------------------------
    # Bankroll management
    # ------------------------------------------------------------------

    def set_initial_bankroll(self, amount: float) -> None:
        """Set the initial bankroll (typically from config or Data API)."""
        self._bankroll = amount
        if amount > self._peak_bankroll:
            self._peak_bankroll = amount
        logger.info("Initial bankroll set to %.2f", amount)

    def update_pnl(self, realized_pnl: float) -> None:
        """Record a realized P&L change (called by executor after fills)."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self._daily_pnl_reset_date != today:
            self._daily_pnl = 0.0
            self._daily_pnl_reset_date = today
        self._daily_pnl += realized_pnl
        self._bankroll += realized_pnl
        if self._bankroll > self._peak_bankroll:
            self._peak_bankroll = self._bankroll
