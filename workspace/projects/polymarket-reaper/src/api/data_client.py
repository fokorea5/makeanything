"""
Polymarket Reaper Bot v1.1 -- Data API Async Wrapper

Native async HTTP client (aiohttp) for the Polymarket Data API.
Retrieves positions, portfolio value, activity, and market holder data.

DESIGN.md 3.4 / AC-03, AC-13 (graceful degradation for /holders)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from config import Config
from src.shared.types import PositionData

logger = logging.getLogger("reaper.api.data")

# ---------------------------------------------------------------------------
# Constants (DESIGN.md 11.1)
# ---------------------------------------------------------------------------
_REQUEST_TIMEOUT = 10
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0


# ---------------------------------------------------------------------------
# AsyncDataClient
# ---------------------------------------------------------------------------

class AsyncDataClient:
    """Async client for the Polymarket Data API.

    Uses ``aiohttp`` directly (no run_in_executor).

    Usage::

        client = AsyncDataClient()
        await client.init()
        positions = await client.get_positions(wallet)
        await client.close()
    """

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._base_url: str = Config.DATA_HOST

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init(self) -> None:
        """Create the underlying aiohttp session."""
        timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT)
        self._session = aiohttp.ClientSession(timeout=timeout)
        logger.info("DataClient initialised  host=%s", self._base_url)

    async def close(self) -> None:
        """Close the aiohttp session gracefully."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("DataClient session closed")
        self._session = None

    # ------------------------------------------------------------------
    # Internal: request with retry + back-off (DESIGN.md 11.1)
    # ------------------------------------------------------------------

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        graceful_404: bool = False,
    ) -> Any:
        """GET with retry/back-off.  If *graceful_404* is True, 404 returns None."""
        if self._session is None:
            raise RuntimeError("DataClient not initialised -- call init() first")

        url = f"{self._base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with self._session.get(url, params=params) as resp:
                    # 429 rate-limit
                    if resp.status == 429:
                        wait = _BACKOFF_BASE * (2 ** attempt)
                        logger.warning(
                            "Data API 429 on %s attempt %d/%d -- backing off %.1fs",
                            path, attempt + 1, _MAX_RETRIES, wait,
                        )
                        await asyncio.sleep(wait)
                        continue

                    # 404 with graceful handling (AC-13: /holders)
                    if resp.status == 404 and graceful_404:
                        logger.debug("Data API 404 (graceful) on %s", path)
                        return None

                    # 401/403
                    if resp.status in (401, 403):
                        logger.warning("Data API auth error %d on %s", resp.status, path)
                        return None

                    # 500+
                    if resp.status >= 500:
                        if attempt < 1:
                            logger.warning(
                                "Data API server error %d on %s -- retrying",
                                resp.status, path,
                            )
                            await asyncio.sleep(1)
                            continue
                        logger.error(
                            "Data API server error %d on %s -- giving up",
                            resp.status, path,
                        )
                        return None

                    resp.raise_for_status()
                    return await resp.json()

            except asyncio.TimeoutError:
                last_exc = TimeoutError(f"Data API timeout: {path}")
                if attempt < 1:
                    logger.warning("Data API timeout on %s -- retrying", path)
                    continue
                break
            except aiohttp.ClientError as exc:
                last_exc = exc
                wait = _BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "Data API network error on %s attempt %d: %s -- backoff %.1fs",
                    path, attempt + 1, exc, wait,
                )
                await asyncio.sleep(wait)

        logger.error("Data API request failed after retries: %s -- %s", path, last_exc)
        return None

    # ------------------------------------------------------------------
    # Public API methods (DESIGN.md 3.4)
    # ------------------------------------------------------------------

    async def get_positions(
        self, wallet: str, market: str | None = None
    ) -> list[PositionData]:
        """Fetch positions for a wallet address, optionally filtered by market."""
        params: dict[str, Any] = {"user": wallet}
        if market:
            params["market"] = market
        data = await self._get("/positions", params=params)
        if not data:
            return []
        items = data if isinstance(data, list) else data.get("positions", [])
        return [self._parse_position(p) for p in items if isinstance(p, dict)]

    async def get_portfolio_value(self, wallet: str) -> float:
        """Fetch total portfolio value (USDC) for a wallet."""
        data = await self._get("/value", params={"user": wallet})
        if not data:
            return 0.0
        try:
            if isinstance(data, dict):
                return float(data.get("value", data.get("portfolio_value", 0.0)))
            return float(data)
        except (TypeError, ValueError):
            return 0.0

    async def get_activity(self, wallet: str) -> list[dict]:
        """Fetch recent trading activity for a wallet."""
        data = await self._get("/activity", params={"user": wallet})
        if not data:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("activity", data.get("data", []))
        return []

    async def get_holders(self, token_id: str) -> list[dict] | None:
        """Fetch holder information for a token.

        Returns ``None`` on 404 or any failure (AC-13: graceful degradation).
        This endpoint may not exist on all Polymarket API versions.
        """
        data = await self._get(
            f"/holders",
            params={"token_id": token_id},
            graceful_404=True,
        )
        if data is None:
            return None
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("holders", data.get("data", None))
        return None

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_position(raw: dict[str, Any]) -> PositionData:
        """Convert raw JSON dict to PositionData dataclass."""
        return PositionData(
            condition_id=str(raw.get("conditionId", raw.get("condition_id", ""))),
            asset=str(raw.get("asset", raw.get("token_id", ""))),
            outcome=str(raw.get("outcome", "")),
            size=float(raw.get("size", 0.0)),
            avg_price=float(raw.get("avgPrice", raw.get("avg_price", 0.0))),
            current_price=float(raw.get("currentPrice", raw.get("current_price", 0.0))),
            initial_value=float(raw.get("initialValue", raw.get("initial_value", 0.0))),
            current_value=float(raw.get("currentValue", raw.get("current_value", 0.0))),
            unrealized_pnl=float(raw.get("unrealizedPnl", raw.get("unrealized_pnl", 0.0))),
            realized_pnl=float(raw.get("realizedPnl", raw.get("realized_pnl", 0.0))),
            title=str(raw.get("title", raw.get("question", ""))),
        )
