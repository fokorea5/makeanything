"""
Polymarket Reaper Bot v1.1 -- Gamma API Async Wrapper

Native async HTTP client (aiohttp) for the Gamma API.
Retrieves market metadata, events, and tags.

DESIGN.md 3.3 / AC-03
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from config import Config
from src.shared.types import GammaEvent, GammaMarket, GammaTag, TagInfo

logger = logging.getLogger("reaper.api.gamma")

# ---------------------------------------------------------------------------
# Constants (DESIGN.md 11.1 -- error handling)
# ---------------------------------------------------------------------------
_REQUEST_TIMEOUT = 10       # seconds
_MAX_RETRIES = 3            # for 429 / network errors
_BACKOFF_BASE = 1.0         # exponential back-off start


# ---------------------------------------------------------------------------
# AsyncGammaClient
# ---------------------------------------------------------------------------

class AsyncGammaClient:
    """Async client for the Polymarket Gamma API.

    Uses ``aiohttp`` directly for native async performance (no run_in_executor).

    Usage::

        client = AsyncGammaClient()
        await client.init()
        markets = await client.get_markets(active=True)
        await client.close()
    """

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._base_url: str = Config.GAMMA_HOST

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init(self) -> None:
        """Create the underlying aiohttp session."""
        timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT)
        self._session = aiohttp.ClientSession(timeout=timeout)
        logger.info("GammaClient initialised  host=%s", self._base_url)

    async def close(self) -> None:
        """Close the aiohttp session gracefully."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("GammaClient session closed")
        self._session = None

    # ------------------------------------------------------------------
    # Internal: request with retry + back-off
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Issue a GET request with retry / back-off per DESIGN.md 11.1."""
        if self._session is None:
            raise RuntimeError("GammaClient not initialised -- call init() first")

        url = f"{self._base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with self._session.get(url, params=params) as resp:
                    # 429 -- exponential back-off
                    if resp.status == 429:
                        wait = _BACKOFF_BASE * (2 ** attempt)
                        logger.warning(
                            "Gamma 429 on %s attempt %d/%d -- backing off %.1fs",
                            path, attempt + 1, _MAX_RETRIES, wait,
                        )
                        await asyncio.sleep(wait)
                        continue

                    # 401 / 403 -- no retry
                    if resp.status in (401, 403):
                        logger.warning("Gamma auth error %d on %s", resp.status, path)
                        return None

                    # 500+ -- 1 retry
                    if resp.status >= 500:
                        if attempt < 1:
                            logger.warning(
                                "Gamma server error %d on %s -- retrying", resp.status, path
                            )
                            await asyncio.sleep(1)
                            continue
                        logger.error("Gamma server error %d on %s -- giving up", resp.status, path)
                        return None

                    resp.raise_for_status()
                    return await resp.json()

            except asyncio.TimeoutError:
                last_exc = TimeoutError(f"Gamma request timed out: {path}")
                if attempt < 1:
                    logger.warning("Gamma timeout on %s -- retrying", path)
                    continue
                break
            except aiohttp.ClientError as exc:
                last_exc = exc
                wait = _BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "Gamma network error on %s attempt %d: %s -- backoff %.1fs",
                    path, attempt + 1, exc, wait,
                )
                await asyncio.sleep(wait)

        logger.error("Gamma request failed after retries: %s -- %s", path, last_exc)
        return None

    # ------------------------------------------------------------------
    # Public API methods (DESIGN.md 3.3)
    # ------------------------------------------------------------------

    async def get_markets(
        self,
        active: bool = True,
        limit: int = 100,
        offset: int = 0,
        order: str = "volume",
    ) -> list[GammaMarket]:
        """Fetch a paginated list of markets from Gamma."""
        params: dict[str, Any] = {
            "active": str(active).lower(),
            "limit": limit,
            "offset": offset,
            "order": order,
        }
        data = await self._get("/markets", params=params)
        if not data or not isinstance(data, list):
            return []
        return [self._parse_market(m) for m in data if isinstance(m, dict)]

    async def get_market_by_id(self, market_id: int) -> GammaMarket | None:
        """Fetch a single market by its numeric Gamma ID."""
        data = await self._get(f"/markets/{market_id}")
        if not data or not isinstance(data, dict):
            return None
        return self._parse_market(data)

    async def get_market_by_slug(self, slug: str) -> GammaMarket | None:
        """Fetch a single market by URL slug."""
        data = await self._get("/markets", params={"slug": slug})
        if not data:
            return None
        # The endpoint may return a list for slug queries
        if isinstance(data, list):
            if not data:
                return None
            return self._parse_market(data[0])
        if isinstance(data, dict):
            return self._parse_market(data)
        return None

    async def get_events(
        self, limit: int = 100, offset: int = 0
    ) -> list[GammaEvent]:
        """Fetch paginated event list."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        data = await self._get("/events", params=params)
        if not data or not isinstance(data, list):
            return []
        return [self._parse_event(e) for e in data if isinstance(e, dict)]

    async def get_event_by_id(self, event_id: int | str) -> GammaEvent | None:
        """Fetch a single event by ID."""
        data = await self._get(f"/events/{event_id}")
        if not data or not isinstance(data, dict):
            return None
        return self._parse_event(data)

    async def get_tags(self) -> list[GammaTag]:
        """Fetch all available tags."""
        data = await self._get("/tags")
        if not data or not isinstance(data, list):
            return []
        return [self._parse_tag(t) for t in data if isinstance(t, dict)]

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_market(raw: dict[str, Any]) -> GammaMarket:
        """Convert raw JSON dict to GammaMarket dataclass."""
        tags: list[TagInfo] = []
        for t in raw.get("tags", []) or []:
            if isinstance(t, dict):
                tags.append(TagInfo(id=int(t.get("id", 0)), label=str(t.get("label", ""))))
            elif isinstance(t, str):
                tags.append(TagInfo(id=0, label=t))

        return GammaMarket(
            id=int(raw.get("id", 0)),
            question=str(raw.get("question", "")),
            condition_id=str(raw.get("conditionId", raw.get("condition_id", ""))),
            slug=str(raw.get("slug", "")),
            resolution_source=str(raw.get("resolutionSource", raw.get("resolution_source", ""))),
            end_date=str(raw.get("endDate", raw.get("end_date", ""))),
            start_date=str(raw.get("startDate", raw.get("start_date", ""))),
            description=str(raw.get("description", "")),
            outcomes=str(raw.get("outcomes", '["Yes","No"]')),
            outcome_prices=str(raw.get("outcomePrices", raw.get("outcome_prices", '["0.5","0.5"]'))),
            volume=str(raw.get("volume", "0")),
            liquidity=str(raw.get("liquidity", "0")),
            active=bool(raw.get("active", True)),
            closed=bool(raw.get("closed", False)),
            tags=tags,
            neg_risk=bool(raw.get("negRisk", raw.get("neg_risk", False))),
            neg_risk_market_id=str(raw.get("negRiskMarketID", raw.get("neg_risk_market_id", ""))),
            image=str(raw.get("image", "")),
            icon=str(raw.get("icon", "")),
        )

    @staticmethod
    def _parse_event(raw: dict[str, Any]) -> GammaEvent:
        """Convert raw JSON dict to GammaEvent dataclass."""
        markets_raw = raw.get("markets", []) or []
        market_ids: list[str] = []
        for m in markets_raw:
            if isinstance(m, dict):
                cid = m.get("conditionId", m.get("condition_id", ""))
                if cid:
                    market_ids.append(str(cid))
            elif isinstance(m, str):
                market_ids.append(m)

        return GammaEvent(
            id=raw.get("id", 0),
            title=str(raw.get("title", "")),
            markets=market_ids,
        )

    @staticmethod
    def _parse_tag(raw: dict[str, Any]) -> GammaTag:
        """Convert raw JSON dict to GammaTag dataclass."""
        return GammaTag(
            id=int(raw.get("id", 0)),
            label=str(raw.get("label", "")),
            slug=str(raw.get("slug", "")),
        )
