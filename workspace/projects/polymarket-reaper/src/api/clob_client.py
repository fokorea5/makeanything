"""
Polymarket Reaper Bot v1.1 -- CLOB API Async Wrapper

Wraps the synchronous py-clob-client SDK with asyncio.run_in_executor
so that blocking HTTP calls do not stall the event loop.

Rate limiting is enforced via asyncio.Semaphore + sliding window counters.
HTTP 429 responses trigger exponential back-off (max 3 retries).

DESIGN.md 3.2 / AC-02
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from typing import Any

from config import Config
from src.shared.types import OrderBookLevel, OrderBookSnapshot, PricePoint

# @confidence: low -- py-clob-client import; API surface may differ across versions
try:
    from py_clob_client.client import ClobClient  # type: ignore[import-untyped]
except ImportError:
    ClobClient = None  # Allows import to succeed in test / dry-run environments

logger = logging.getLogger("reaper.api.clob")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_PUBLIC_SEMAPHORE_LIMIT = 50       # concurrent public requests
_ORDER_SEMAPHORE_LIMIT = 15        # concurrent order requests
_RATE_WINDOW_SEC = 60              # sliding window length
_PUBLIC_RATE_LIMIT = 65            # max public requests per window
_ORDER_RATE_LIMIT = 20             # max order requests per window
_BACKOFF_BASE = 1.0                # 429 back-off initial seconds
_MAX_RETRIES = 3                   # max retry count on 429
_REQUEST_TIMEOUT = 10              # seconds


# ---------------------------------------------------------------------------
# Sliding-window rate limiter
# ---------------------------------------------------------------------------

class _SlidingWindowLimiter:
    """Simple sliding-window request counter."""

    def __init__(self, max_requests: int, window_sec: float = 60.0) -> None:
        self._max = max_requests
        self._window = window_sec
        self._timestamps: deque[float] = deque()

    async def acquire(self) -> None:
        """Wait until a slot is available in the window."""
        while True:
            now = time.monotonic()
            # Purge old entries
            while self._timestamps and self._timestamps[0] < now - self._window:
                self._timestamps.popleft()
            if len(self._timestamps) < self._max:
                self._timestamps.append(now)
                return
            # Sleep until the oldest entry expires
            sleep_for = self._timestamps[0] + self._window - now + 0.05
            await asyncio.sleep(sleep_for)


# ---------------------------------------------------------------------------
# AsyncClobClient
# ---------------------------------------------------------------------------

class AsyncClobClient:
    """Async facade over the synchronous ``py-clob-client.ClobClient``.

    Every SDK call is dispatched to the default ThreadPoolExecutor via
    ``loop.run_in_executor(None, ...)``.

    Usage::

        client = AsyncClobClient()
        await client.init()
        book = await client.get_order_book(token_id)
        await client.close()
    """

    def __init__(self) -> None:
        self._client: Any | None = None  # ClobClient instance
        self._public_sem = asyncio.Semaphore(_PUBLIC_SEMAPHORE_LIMIT)
        self._order_sem = asyncio.Semaphore(_ORDER_SEMAPHORE_LIMIT)
        self._public_limiter = _SlidingWindowLimiter(_PUBLIC_RATE_LIMIT, _RATE_WINDOW_SEC)
        self._order_limiter = _SlidingWindowLimiter(_ORDER_RATE_LIMIT, _RATE_WINDOW_SEC)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init(self) -> None:
        """Initialise the underlying synchronous ClobClient."""
        if ClobClient is None:
            logger.warning("py-clob-client not installed -- operating in stub mode")
            return

        loop = asyncio.get_running_loop()

        def _create() -> Any:  # @risk: auth
            kwargs: dict[str, Any] = {
                "host": Config.CLOB_HOST,
                "chain_id": 137,  # Polygon mainnet
            }
            if Config.PRIVATE_KEY:
                kwargs["key"] = Config.PRIVATE_KEY
            if Config.POLY_API_KEY:
                kwargs["creds"] = {
                    "api_key": Config.POLY_API_KEY,
                    "api_secret": Config.POLY_API_SECRET,
                    "api_passphrase": Config.POLY_API_PASSPHRASE,
                }
            kwargs["signature_type"] = Config.SIGNATURE_TYPE
            if Config.FUNDER_ADDRESS:
                kwargs["funder"] = Config.FUNDER_ADDRESS
            return ClobClient(**kwargs)

        try:
            self._client = await asyncio.wait_for(
                loop.run_in_executor(None, _create),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            logger.error("ClobClient init timed out after 30s -- operating in stub mode")
            return
        logger.info(
            "ClobClient initialised  host=%s  wallet=%s",
            Config.CLOB_HOST,
            Config.WALLET_ADDRESS[:6] + "***" if Config.WALLET_ADDRESS else "(unset)",
        )

    async def close(self) -> None:
        """Cleanup (no-op for the sync SDK but keeps the interface consistent)."""
        self._client = None
        logger.info("ClobClient closed")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_public(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute a public (read-only) SDK call with rate limiting + back-off."""
        async with self._public_sem:
            await self._public_limiter.acquire()
            return await self._exec_with_backoff(func, *args, **kwargs)

    async def _run_order(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute an order (write) SDK call with rate limiting + back-off."""
        async with self._order_sem:
            await self._order_limiter.acquire()
            return await self._exec_with_backoff(func, *args, **kwargs)

    async def _exec_with_backoff(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Run *func* in executor with exponential back-off on HTTP 429."""
        loop = asyncio.get_running_loop()
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: func(*args, **kwargs)),
                    timeout=_REQUEST_TIMEOUT,
                )
                return result
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                err_str = str(exc).lower()
                # Detect 429 / rate-limit from exception message
                if "429" in err_str or "rate" in err_str:
                    wait = _BACKOFF_BASE * (2 ** attempt)
                    logger.warning(
                        "CLOB 429 rate-limit on attempt %d/%d -- backing off %.1fs",
                        attempt + 1, _MAX_RETRIES, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                # 401/403 -- do not retry
                if "401" in err_str or "403" in err_str:
                    logger.warning("CLOB auth error: %s", exc)  # @risk: auth
                    raise
                # 500+ -- 1 retry
                if "500" in err_str or "502" in err_str or "503" in err_str:
                    if attempt < 1:
                        logger.warning("CLOB server error -- retrying once: %s", exc)
                        await asyncio.sleep(1)
                        continue
                    raise
                # Unknown error
                raise

        # Exhausted retries
        logger.error("CLOB request failed after %d retries: %s", _MAX_RETRIES, last_exc)
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public API methods (DESIGN.md 3.2)
    # ------------------------------------------------------------------

    async def get_markets(self, next_cursor: str = "") -> dict:
        """Fetch paginated market list."""
        if self._client is None:
            return {"data": [], "next_cursor": ""}
        return await self._run_public(self._client.get_markets, next_cursor=next_cursor)

    async def get_order_book(self, token_id: str) -> OrderBookSnapshot:
        """Fetch current order book for a token and return typed snapshot."""
        if self._client is None:
            return OrderBookSnapshot(market="", asset_id=token_id, bids=[], asks=[])
        raw = await self._run_public(self._client.get_order_book, token_id)
        return self._parse_orderbook(token_id, raw)

    async def get_midpoint(self, token_id: str) -> float:
        """Get midpoint price for a token."""
        if self._client is None:
            return 0.0
        raw = await self._run_public(self._client.get_midpoint, token_id)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    async def get_price(self, token_id: str, side: str) -> float:
        """Get best price for a given side."""
        if self._client is None:
            return 0.0
        raw = await self._run_public(self._client.get_price, token_id, side)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    async def get_last_trade_price(self, token_id: str) -> float:
        """Get last trade price for a token."""
        if self._client is None:
            return 0.0
        raw = await self._run_public(self._client.get_last_trade_price, token_id)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    async def get_prices_history(
        self, token_id: str, interval: str = "1d"
    ) -> list[PricePoint]:
        """Fetch price history and return as list of PricePoint."""
        if self._client is None:
            return []
        raw = await self._run_public(
            self._client.get_prices_history, token_id, interval=interval
        )
        points: list[PricePoint] = []
        if isinstance(raw, dict):
            history = raw.get("history", [])
        elif isinstance(raw, list):
            history = raw
        else:
            history = []
        for item in history:
            try:
                points.append(
                    PricePoint(
                        timestamp=int(item.get("t", 0)),
                        price=float(item.get("p", 0.0)),
                    )
                )
            except (TypeError, ValueError, AttributeError):
                continue
        return points

    async def get_spread(self, token_id: str) -> float:
        """Get current spread for a token."""
        if self._client is None:
            return 0.0
        raw = await self._run_public(self._client.get_spread, token_id)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    async def get_fee_rate(self, token_id: str) -> float:
        """Get fee rate in basis points for a token. Returns 0.0 on failure."""
        if self._client is None:
            return 0.0
        try:
            # @confidence: low -- fee rate endpoint may vary across SDK versions
            raw = await self._run_public(
                lambda: getattr(self._client, "get_fee_rate_bps", lambda _: "0")(token_id)
            )
            return float(raw)
        except Exception:  # noqa: BLE001
            return 0.0

    # ------------------------------------------------------------------
    # Order API methods (DESIGN.md 3.2)
    # ------------------------------------------------------------------

    async def post_order(self, signed_order: Any, order_type: str = "GTC") -> dict:
        """Submit a signed order. Returns the API response dict.

        In DRY_RUN mode, callers should not invoke this method.
        """
        if self._client is None:
            logger.warning("post_order called but ClobClient is not initialised")
            return {}
        # @risk: auth -- order submission involves EIP-712 signature
        result = await self._run_order(
            self._client.post_order, signed_order, order_type=order_type
        )
        logger.info(
            "Order submitted  type=%s  result=%s",
            order_type,
            str(result)[:120],
        )
        return result if isinstance(result, dict) else {"raw": result}

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a single open order."""
        if self._client is None:
            return False
        try:
            await self._run_order(self._client.cancel, order_id=order_id)
            logger.info("Order cancelled: %s", order_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to cancel order %s: %s", order_id, exc)
            return False

    async def cancel_all(self) -> bool:
        """Cancel ALL open orders (Circuit Breaker -- AC-26)."""
        if self._client is None:
            return False
        try:
            await self._run_order(self._client.cancel_all)
            logger.info("All orders cancelled (circuit breaker)")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to cancel all orders: %s", exc)
            return False

    async def cancel_market_orders(self, condition_id: str) -> bool:
        """Cancel all orders for a specific market (AC-40)."""
        if self._client is None:
            return False
        try:
            open_orders = await self.get_open_orders(market=condition_id)
            for order in open_orders:
                oid = order.get("id", order.get("order_id", ""))
                if oid:
                    await self.cancel_order(oid)
            logger.info("Cancelled orders for market %s", condition_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to cancel market orders %s: %s", condition_id, exc)
            return False

    async def get_open_orders(self, market: str | None = None) -> list[dict]:
        """Retrieve open orders, optionally filtered by market."""
        if self._client is None:
            return []
        try:
            if market:
                raw = await self._run_public(self._client.get_orders, market=market)
            else:
                raw = await self._run_public(self._client.get_orders)
            if isinstance(raw, list):
                return raw
            if isinstance(raw, dict):
                return raw.get("data", raw.get("orders", []))
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch open orders: %s", exc)
            return []

    async def get_trades(self, market: str | None = None) -> list[dict]:
        """Retrieve trade history, optionally filtered by market."""
        if self._client is None:
            return []
        try:
            if market:
                raw = await self._run_public(self._client.get_trades, market=market)
            else:
                raw = await self._run_public(self._client.get_trades)
            if isinstance(raw, list):
                return raw
            if isinstance(raw, dict):
                return raw.get("data", raw.get("trades", []))
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch trades: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_orderbook(token_id: str, raw: Any) -> OrderBookSnapshot:
        """Convert raw SDK order book response to an ``OrderBookSnapshot``."""
        bids: list[OrderBookLevel] = []
        asks: list[OrderBookLevel] = []

        if isinstance(raw, dict):
            market = raw.get("market", "")
            asset_id = raw.get("asset_id", token_id)
            for b in raw.get("bids", []):
                try:
                    bids.append(OrderBookLevel(price=float(b["price"]), size=float(b["size"])))
                except (KeyError, TypeError, ValueError):
                    continue
            for a in raw.get("asks", []):
                try:
                    asks.append(OrderBookLevel(price=float(a["price"]), size=float(a["size"])))
                except (KeyError, TypeError, ValueError):
                    continue
        else:
            market = ""
            asset_id = token_id

        # Sort: bids descending, asks ascending
        bids.sort(key=lambda l: l.price, reverse=True)
        asks.sort(key=lambda l: l.price)

        return OrderBookSnapshot(
            market=market,
            asset_id=asset_id,
            bids=bids,
            asks=asks,
        )
