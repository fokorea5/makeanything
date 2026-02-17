"""
Polymarket Reaper Bot v1.1 -- WebSocket Manager

Manages Market and User WebSocket channels with automatic reconnection,
exponential back-off, and automatic re-subscription after reconnect.

DESIGN.md 3.5 / AC-04
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Awaitable

import websockets
import websockets.exceptions

from config import Config

logger = logging.getLogger("reaper.api.ws")

# ---------------------------------------------------------------------------
# Constants (DESIGN.md 3.5 / 11.2)
# ---------------------------------------------------------------------------
_HEARTBEAT_TIMEOUT = 30.0        # seconds of silence before reconnect
_BACKOFF_BASE = 1.0              # initial back-off
_BACKOFF_MAX = 30.0              # maximum back-off cap
_MAX_RECONNECT_FAILURES = 5      # consecutive failures before on_ws_failure callback


# ---------------------------------------------------------------------------
# Single-channel connection handler
# ---------------------------------------------------------------------------

class _WSChannel:
    """Manages one WebSocket channel (market or user)."""

    def __init__(
        self,
        url: str,
        channel_type: str,
        *,
        auth: dict[str, Any] | None = None,
        on_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_failure: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._url = url
        self._channel_type = channel_type  # "market" | "user"
        self._auth = auth or {}
        self._on_event = on_event
        self._on_failure = on_failure

        self._ws: Any = None
        self._running = False
        self._subscribed_assets: list[str] = []
        self._consecutive_failures = 0
        self._task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def connect(self, asset_ids: list[str] | None = None) -> None:
        """Open the WS connection and start the listener loop.

        For market channels, *asset_ids* specifies the initial subscriptions.
        """
        self._running = True
        if asset_ids:
            self._subscribed_assets = list(set(self._subscribed_assets + asset_ids))
        self._task = asyncio.create_task(self._listen_loop(), name=f"ws-{self._channel_type}")
        logger.info(
            "WS %s channel starting  url=%s  initial_assets=%d",
            self._channel_type, self._url, len(self._subscribed_assets),
        )

    async def subscribe_assets(self, asset_ids: list[str]) -> None:
        """Subscribe to additional asset IDs on an open market channel."""
        new_ids = [aid for aid in asset_ids if aid and aid not in self._subscribed_assets]
        if not new_ids:
            return
        self._subscribed_assets.extend(new_ids)
        if self._ws:
            await self._send_subscribe(new_ids)
            logger.info("WS %s subscribed to %d new assets", self._channel_type, len(new_ids))

    async def unsubscribe_all_and_reconnect(self, new_ids: list[str]) -> None:
        """Replace all subscriptions.  WS does not support unsubscribe, so we reconnect."""
        self._subscribed_assets = list(set(new_ids))
        if self._ws:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
        logger.info("WS %s reconnecting with %d assets", self._channel_type, len(new_ids))

    async def close(self) -> None:
        """Gracefully shutdown the channel."""
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("WS %s channel closed", self._channel_type)

    @property
    def subscribed_assets(self) -> list[str]:
        return list(self._subscribed_assets)

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and self._running

    # ------------------------------------------------------------------
    # Internal: listen loop with auto-reconnect (AC-04, DESIGN.md 11.2)
    # ------------------------------------------------------------------

    async def _listen_loop(self) -> None:
        """Main loop: connect, receive, reconnect on failure."""
        while self._running:
            try:
                # @confidence: low -- websockets library API may change across major versions
                async with websockets.connect(self._url) as ws:
                    self._ws = ws
                    self._consecutive_failures = 0
                    logger.info("WS %s connected", self._channel_type)

                    # Send initial subscription
                    await self._send_subscribe(self._subscribed_assets)

                    # Receive loop
                    while self._running:
                        try:
                            raw = await asyncio.wait_for(
                                ws.recv(), timeout=_HEARTBEAT_TIMEOUT
                            )
                            await self._handle_message(raw)
                        except asyncio.TimeoutError:
                            # Heartbeat timeout -- reconnect
                            logger.warning(
                                "WS %s heartbeat timeout (%.0fs) -- reconnecting",
                                self._channel_type, _HEARTBEAT_TIMEOUT,
                            )
                            break

            except websockets.exceptions.ConnectionClosedError as exc:
                logger.warning("WS %s connection closed: %s", self._channel_type, exc)
            except websockets.exceptions.WebSocketException as exc:
                logger.warning("WS %s error: %s", self._channel_type, exc)
            except OSError as exc:
                logger.warning("WS %s network error: %s", self._channel_type, exc)
            except asyncio.CancelledError:
                break
            finally:
                self._ws = None

            if not self._running:
                break

            # Reconnect with exponential back-off
            self._consecutive_failures += 1
            if self._consecutive_failures >= _MAX_RECONNECT_FAILURES:
                logger.error(
                    "WS %s failed %d times -- invoking on_ws_failure callback",
                    self._channel_type, self._consecutive_failures,
                )
                if self._on_failure:
                    try:
                        await self._on_failure()
                    except Exception:  # noqa: BLE001
                        logger.exception("on_ws_failure callback error")
                # Reset counter and keep trying
                self._consecutive_failures = 0

            backoff = min(_BACKOFF_BASE * (2 ** (self._consecutive_failures - 1)), _BACKOFF_MAX)
            logger.info(
                "WS %s reconnecting in %.1fs (attempt %d)",
                self._channel_type, backoff, self._consecutive_failures,
            )
            await asyncio.sleep(backoff)

    # ------------------------------------------------------------------
    # Internal: subscription & message handling
    # ------------------------------------------------------------------

    async def _send_subscribe(self, asset_ids: list[str]) -> None:
        """Send subscription message per DESIGN.md 9.4."""
        if not self._ws or not asset_ids:
            return

        if self._channel_type == "market":
            msg = {
                "auth": {},
                "assets_ids": asset_ids,
                "type": "market",
            }
        elif self._channel_type == "user":
            # @risk: auth -- L2 auth credentials in WS subscription
            msg = {
                "auth": {
                    "apiKey": Config.POLY_API_KEY,
                    "secret": Config.POLY_API_SECRET,
                    "passphrase": Config.POLY_API_PASSPHRASE,
                },
                "type": "user",
            }
        else:
            return

        try:
            await self._ws.send(json.dumps(msg))
            logger.debug(
                "WS %s subscribe sent  assets=%d", self._channel_type, len(asset_ids)
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("WS %s subscribe failed: %s", self._channel_type, exc)

    async def _handle_message(self, raw: str | bytes) -> None:
        """Parse incoming WS message and dispatch to callback."""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.debug("WS %s ignoring non-JSON message", self._channel_type)
            return

        # Handle arrays of events (some WS endpoints batch)
        events = data if isinstance(data, list) else [data]

        for event in events:
            if not isinstance(event, dict):
                continue
            if self._on_event:
                try:
                    await self._on_event(event)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "WS %s event handler error for event_type=%s",
                        self._channel_type,
                        event.get("event_type", "unknown"),
                    )


# ---------------------------------------------------------------------------
# WSManager (public facade)
# ---------------------------------------------------------------------------

class WSManager:
    """High-level WebSocket manager for Market and User channels.

    DESIGN.md 3.5 / AC-04

    Usage::

        mgr = WSManager()
        await mgr.connect_market(asset_ids, on_event=handler)
        await mgr.subscribe_assets(new_ids)
        await mgr.close()
    """

    def __init__(self) -> None:
        self._market_channel: _WSChannel | None = None
        self._user_channel: _WSChannel | None = None

    # ------------------------------------------------------------------
    # Market channel
    # ------------------------------------------------------------------

    async def connect_market(
        self,
        asset_ids: list[str],
        on_event: Callable[[dict[str, Any]], Awaitable[None]],
        on_failure: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Open the market WS channel and subscribe to *asset_ids*.

        *on_event* is called for every incoming event dict.
        *on_failure* is called after 5 consecutive reconnect failures
        (DESIGN.md 11.2 step 4).
        """
        self._market_channel = _WSChannel(
            url=Config.WS_MARKET_URL,
            channel_type="market",
            on_event=on_event,
            on_failure=on_failure,
        )
        await self._market_channel.connect(asset_ids)

    async def subscribe_assets(self, asset_ids: list[str]) -> None:
        """Subscribe to additional assets on the market channel (Stage 2 -> 3)."""
        if self._market_channel:
            await self._market_channel.subscribe_assets(asset_ids)

    async def unsubscribe_all_and_reconnect(self, new_ids: list[str]) -> None:
        """Replace market channel subscriptions (WS lacks unsubscribe)."""
        if self._market_channel:
            await self._market_channel.unsubscribe_all_and_reconnect(new_ids)

    @property
    def market_subscribed_assets(self) -> list[str]:
        if self._market_channel:
            return self._market_channel.subscribed_assets
        return []

    # ------------------------------------------------------------------
    # User channel
    # ------------------------------------------------------------------

    async def connect_user(
        self,
        on_event: Callable[[dict[str, Any]], Awaitable[None]],
        on_failure: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Open the user WS channel (L2 authenticated)."""
        self._user_channel = _WSChannel(
            url=Config.WS_USER_URL,
            channel_type="user",
            auth={
                "apiKey": Config.POLY_API_KEY,
                "secret": Config.POLY_API_SECRET,
                "passphrase": Config.POLY_API_PASSPHRASE,
            },
            on_event=on_event,
            on_failure=on_failure,
        )
        await self._user_channel.connect()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close both channels gracefully."""
        tasks: list[asyncio.Task[None]] = []
        if self._market_channel:
            tasks.append(asyncio.create_task(self._market_channel.close()))
        if self._user_channel:
            tasks.append(asyncio.create_task(self._user_channel.close()))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("WSManager closed all channels")

    @property
    def is_market_connected(self) -> bool:
        return self._market_channel is not None and self._market_channel.is_connected

    @property
    def is_user_connected(self) -> bool:
        return self._user_channel is not None and self._user_channel.is_connected
