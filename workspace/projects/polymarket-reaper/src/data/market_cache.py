"""
Polymarket Reaper Bot v1.1 -- Market Data Cache

In-memory cache for market data, reducing redundant API calls.
Integrates Gamma + CLOB data into unified MarketData objects.
Supports real-time updates via WebSocket events.

DESIGN.md 3.13 / AC-10
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any

from config import Config
from src.shared.types import (
    GammaMarket,
    MarketData,
    OrderBookLevel,
    OrderBookSnapshot,
    TagInfo,
    TokenInfo,
)

logger = logging.getLogger("reaper.data.cache")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_TTL_SEC = 300  # 5-minute TTL for cached market data


# ---------------------------------------------------------------------------
# MarketDataCache
# ---------------------------------------------------------------------------

class MarketDataCache:
    """In-memory cache for active market data.

    DESIGN.md 3.13

    Features:
    - 5-minute TTL for cached entries (configurable)
    - event_id grouping for Complete Set / Correlated strategies
    - Real-time price/orderbook updates from WebSocket events
    - Thread-safe within a single asyncio event loop (no locks needed)

    Usage::

        cache = MarketDataCache()
        await cache.refresh_markets(gamma_client)
        market = await cache.get_market("0x1234...")
    """

    def __init__(self, ttl_sec: float = _DEFAULT_TTL_SEC) -> None:
        self._ttl_sec = ttl_sec
        self._markets: dict[str, MarketData] = {}           # condition_id -> MarketData
        self._token_to_market: dict[str, str] = {}           # token_id -> condition_id
        self._event_groups: dict[str, list[str]] = {}        # event_id -> [condition_id, ...]
        self._last_refresh: float = 0.0

    # ------------------------------------------------------------------
    # Refresh (Gamma API)
    # ------------------------------------------------------------------

    async def refresh_markets(self, gamma_client: Any) -> None:
        """Reload all active markets from the Gamma API.

        Called periodically by the engine (every TTL interval).
        *gamma_client* should be an ``AsyncGammaClient`` instance.
        """
        try:
            all_markets: list[GammaMarket] = []
            offset = 0
            limit = 100
            while True:
                logger.info("Fetching markets page offset=%d ...", offset)
                batch = await gamma_client.get_markets(
                    active=True, limit=limit, offset=offset
                )
                if not batch:
                    logger.info("No more markets at offset=%d (total so far: %d)", offset, len(all_markets))
                    break
                all_markets.extend(batch)
                logger.info("Got %d markets (total: %d)", len(batch), len(all_markets))
                if len(batch) < limit:
                    break
                offset += limit

            # Build cache
            new_markets: dict[str, MarketData] = {}
            new_token_map: dict[str, str] = {}
            new_event_groups: dict[str, list[str]] = {}

            for gm in all_markets:
                md = self._gamma_to_market_data(gm)
                cid = md.condition_id
                if not cid:
                    continue

                # Preserve existing real-time data if available
                existing = self._markets.get(cid)
                if existing:
                    md.yes_price = existing.yes_price or md.yes_price
                    md.no_price = existing.no_price or md.no_price
                    md.orderbook = existing.orderbook
                    md.prices_history = existing.prices_history

                new_markets[cid] = md

                # Token -> market mapping
                for token in md.tokens:
                    new_token_map[token.token_id] = cid

                # Event grouping
                if md.event_id:
                    new_event_groups.setdefault(md.event_id, []).append(cid)

            self._markets = new_markets
            self._token_to_market = new_token_map
            self._event_groups = new_event_groups
            self._last_refresh = time.monotonic()

            logger.info(
                "Market cache refreshed  markets=%d  events=%d",
                len(self._markets), len(self._event_groups),
            )

        except Exception:  # noqa: BLE001
            logger.exception("Failed to refresh market cache")

    @property
    def is_stale(self) -> bool:
        """True if the cache has not been refreshed within the TTL."""
        if self._last_refresh == 0.0:
            return True
        return (time.monotonic() - self._last_refresh) > self._ttl_sec

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    async def get_market(self, condition_id: str) -> MarketData | None:
        """Retrieve a cached market by condition_id."""
        return self._markets.get(condition_id)

    async def get_all_active_markets(self) -> list[MarketData]:
        """Return all cached active markets."""
        return [m for m in self._markets.values() if m.active and not m.closed]

    async def get_markets_by_event(self, event_id: str) -> list[MarketData]:
        """Return markets grouped under the same event (Complete Set / Correlated)."""
        cids = self._event_groups.get(event_id, [])
        return [self._markets[c] for c in cids if c in self._markets]

    def get_event_groups(self) -> dict[str, list[MarketData]]:
        """Return event_id -> list[MarketData] mapping for all events."""
        result: dict[str, list[MarketData]] = {}
        for eid, cids in self._event_groups.items():
            markets = [self._markets[c] for c in cids if c in self._markets]
            if markets:
                result[eid] = markets
        return result

    def get_market_by_token(self, token_id: str) -> MarketData | None:
        """Find a market by one of its token IDs."""
        cid = self._token_to_market.get(token_id)
        if cid:
            return self._markets.get(cid)
        return None

    # ------------------------------------------------------------------
    # Real-time update methods (WS events)
    # ------------------------------------------------------------------

    async def update_price(self, token_id: str, price: float) -> None:
        """Update a market's price from a WS event."""
        cid = self._token_to_market.get(token_id)
        if not cid or cid not in self._markets:
            return
        market = self._markets[cid]
        # Determine if this token is YES or NO
        for token in market.tokens:
            if token.token_id == token_id:
                if token.outcome == "Yes":
                    market.yes_price = price
                    market.no_price = max(0.0, 1.0 - price)
                elif token.outcome == "No":
                    market.no_price = price
                    market.yes_price = max(0.0, 1.0 - price)
                break
        market.last_updated = datetime.utcnow()

    async def update_orderbook(
        self, token_id: str, book: OrderBookSnapshot
    ) -> None:
        """Update a market's orderbook from a WS event."""
        cid = self._token_to_market.get(token_id)
        if not cid or cid not in self._markets:
            return
        market = self._markets[cid]
        market.orderbook = book
        market.last_updated = datetime.utcnow()

        # Update mid price from orderbook if available
        if book.mid is not None:
            for token in market.tokens:
                if token.token_id == token_id:
                    if token.outcome == "Yes":
                        market.yes_price = book.mid
                    elif token.outcome == "No":
                        market.no_price = book.mid
                    break

    async def update_from_ws_event(self, event: dict[str, Any]) -> None:
        """Dispatch a raw WS event to the appropriate update method.

        Handles: last_trade_price, price_change, book
        (DESIGN.md 9.4 event types)
        """
        event_type = event.get("event_type", "")

        if event_type == "last_trade_price":
            asset_id = event.get("asset_id", "")
            try:
                price = float(event.get("price", 0))
            except (TypeError, ValueError):
                return
            if asset_id and price > 0:
                await self.update_price(asset_id, price)

        elif event_type == "price_change":
            asset_id = event.get("asset_id", "")
            changes = event.get("changes", [])
            if asset_id and changes:
                # Take the latest price from changes
                for change in reversed(changes):
                    try:
                        price = float(change.get("price", 0))
                        if price > 0:
                            await self.update_price(asset_id, price)
                            break
                    except (TypeError, ValueError):
                        continue

        elif event_type == "book":
            asset_id = event.get("asset_id", "")
            market_cid = event.get("market", "")
            if not asset_id:
                return
            bids: list[OrderBookLevel] = []
            asks: list[OrderBookLevel] = []
            for b in event.get("bids", []):
                try:
                    bids.append(
                        OrderBookLevel(price=float(b["price"]), size=float(b["size"]))
                    )
                except (KeyError, TypeError, ValueError):
                    continue
            for a in event.get("asks", []):
                try:
                    asks.append(
                        OrderBookLevel(price=float(a["price"]), size=float(a["size"]))
                    )
                except (KeyError, TypeError, ValueError):
                    continue
            bids.sort(key=lambda l: l.price, reverse=True)
            asks.sort(key=lambda l: l.price)

            book = OrderBookSnapshot(
                market=market_cid,
                asset_id=asset_id,
                bids=bids,
                asks=asks,
            )
            await self.update_orderbook(asset_id, book)

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _gamma_to_market_data(gm: GammaMarket) -> MarketData:
        """Convert a GammaMarket to a MarketData object."""
        # Parse outcomes and prices from JSON strings
        try:
            outcomes = json.loads(gm.outcomes) if isinstance(gm.outcomes, str) else gm.outcomes
        except (json.JSONDecodeError, TypeError):
            outcomes = ["Yes", "No"]

        try:
            prices = json.loads(gm.outcome_prices) if isinstance(gm.outcome_prices, str) else gm.outcome_prices
        except (json.JSONDecodeError, TypeError):
            prices = ["0.5", "0.5"]

        # Build token info list (token_ids are not in Gamma data -- they come from CLOB)
        tokens: list[TokenInfo] = []
        for i, outcome in enumerate(outcomes):
            tokens.append(TokenInfo(token_id="", outcome=str(outcome)))

        # Extract prices
        yes_price = 0.0
        no_price = 0.0
        if prices and len(prices) >= 1:
            try:
                yes_price = float(prices[0])
            except (TypeError, ValueError):
                pass
        if prices and len(prices) >= 2:
            try:
                no_price = float(prices[1])
            except (TypeError, ValueError):
                pass

        # Volume / liquidity
        try:
            volume = float(gm.volume)
        except (TypeError, ValueError):
            volume = 0.0
        try:
            liquidity = float(gm.liquidity)
        except (TypeError, ValueError):
            liquidity = 0.0

        return MarketData(
            condition_id=gm.condition_id,
            question_id="",                # CLOB-specific, filled later
            tokens=tokens,
            question=gm.question,
            description=gm.description,
            slug=gm.slug,
            resolution_source=gm.resolution_source,
            end_date=gm.end_date,
            start_date=gm.start_date,
            category="",                   # Gamma may not provide category directly
            tags=gm.tags,
            active=gm.active,
            closed=gm.closed,
            event_id=None,                 # Filled from events query
            yes_price=yes_price,
            no_price=no_price,
            volume=volume,
            liquidity=liquidity,
            neg_risk=gm.neg_risk,
            neg_risk_market_id=gm.neg_risk_market_id,
        )

    async def enrich_with_events(self, gamma_client: Any) -> None:
        """Load events and set event_id on cached markets."""
        try:
            events = await gamma_client.get_events(limit=500)
            for event in events:
                eid = str(event.id)
                for cid in event.markets:
                    if cid in self._markets:
                        self._markets[cid].event_id = eid

            # Rebuild event groups
            self._event_groups = {}
            for cid, md in self._markets.items():
                if md.event_id:
                    self._event_groups.setdefault(md.event_id, []).append(cid)

            logger.info("Market cache enriched with %d events", len(events))
        except Exception:  # noqa: BLE001
            logger.exception("Failed to enrich markets with events")
