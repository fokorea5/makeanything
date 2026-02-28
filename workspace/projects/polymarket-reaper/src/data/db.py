"""
Polymarket Reaper Bot v1.1 -- DB Manager

Async SQLite database via aiosqlite.
Manages 4 tables: signals, trades, portfolio, daily_stats.

DESIGN.md 3.14, 4 / AC-06, AC-30, AC-35
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
from datetime import datetime
from typing import Any

import aiosqlite

from config import Config
from src.shared.types import (
    DailyStats,
    Position,
    RiskLayerResult,
    Signal,
    TradeResult,
)

logger = logging.getLogger("reaper.data.db")

# ---------------------------------------------------------------------------
# SQL DDL -- exact schemas from DESIGN.md 4
# ---------------------------------------------------------------------------

_SCHEMA_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    strategy        TEXT NOT NULL,
    reactor_source  TEXT NOT NULL,
    condition_id    TEXT NOT NULL,
    token_id        TEXT NOT NULL,
    side            TEXT NOT NULL,
    confidence      REAL NOT NULL,
    urgency         TEXT NOT NULL,
    price_at_signal REAL NOT NULL,
    metadata        TEXT,
    expires_at      TEXT NOT NULL,
    consumed        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_INDEX_SIGNALS = [
    "CREATE INDEX IF NOT EXISTS idx_signals_market ON signals(condition_id, timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals(strategy, timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_signals_reactor ON signals(reactor_source, timestamp);",
]

_SCHEMA_TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    condition_id    TEXT NOT NULL,
    token_id        TEXT NOT NULL,
    side            TEXT NOT NULL,
    price           REAL NOT NULL,
    size            REAL NOT NULL,
    cost_usdc       REAL NOT NULL,
    order_type      TEXT NOT NULL,
    executor_mode   TEXT NOT NULL,
    reactor_source  TEXT NOT NULL,
    order_id        TEXT,
    status          TEXT NOT NULL,
    confidence      REAL NOT NULL,
    golden_cross    INTEGER NOT NULL DEFAULT 0,
    convergence     INTEGER NOT NULL DEFAULT 0,
    signals_used    TEXT NOT NULL,
    risk_layers     TEXT NOT NULL,
    holding_cost    REAL NOT NULL DEFAULT 0.0,
    fee_cost        REAL NOT NULL DEFAULT 0.0,
    is_dry_run      INTEGER NOT NULL DEFAULT 0,
    pnl             REAL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_INDEX_TRADES = [
    "CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(condition_id, timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_trades_reactor ON trades(reactor_source, timestamp);",
]

_SCHEMA_PORTFOLIO = """
CREATE TABLE IF NOT EXISTS portfolio (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    condition_id    TEXT NOT NULL,
    token_id        TEXT NOT NULL,
    outcome         TEXT NOT NULL,
    size            REAL NOT NULL,
    avg_price       REAL NOT NULL,
    current_price   REAL NOT NULL,
    unrealized_pnl  REAL NOT NULL,
    market_question TEXT NOT NULL,
    is_dry_run      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_INDEX_PORTFOLIO = [
    "CREATE INDEX IF NOT EXISTS idx_portfolio_market ON portfolio(condition_id);",
    "CREATE INDEX IF NOT EXISTS idx_portfolio_time ON portfolio(timestamp);",
]

_SCHEMA_DAILY_STATS = """
CREATE TABLE IF NOT EXISTS daily_stats (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT NOT NULL UNIQUE,
    total_trades        INTEGER NOT NULL DEFAULT 0,
    winning_trades      INTEGER NOT NULL DEFAULT 0,
    losing_trades       INTEGER NOT NULL DEFAULT 0,
    total_pnl           REAL NOT NULL DEFAULT 0.0,
    max_drawdown        REAL NOT NULL DEFAULT 0.0,
    peak_bankroll       REAL NOT NULL DEFAULT 0.0,
    signals_generated   INTEGER NOT NULL DEFAULT 0,
    signals_converted   INTEGER NOT NULL DEFAULT 0,
    alpha_signals       INTEGER NOT NULL DEFAULT 0,
    omega_signals       INTEGER NOT NULL DEFAULT 0,
    golden_crosses      INTEGER NOT NULL DEFAULT 0,
    circuit_breaker_hit INTEGER NOT NULL DEFAULT 0,
    frequency_mode      TEXT NOT NULL DEFAULT 'NORMAL',
    is_dry_run          INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


# ---------------------------------------------------------------------------
# DBManager
# ---------------------------------------------------------------------------

class DBManager:
    """Async SQLite database manager.

    DESIGN.md 3.14 / AC-06

    Usage::

        db = DBManager()
        await db.init_db()
        await db.record_signal(signal)
        await db.close()
    """

    def __init__(self) -> None:
        self._db: aiosqlite.Connection | None = None
        self._db_path: str = Config.DB_PATH

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init_db(self) -> None:
        """Open the database and create tables if they do not exist."""
        # Ensure the parent directory exists
        db_dir = pathlib.Path(self._db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self._db = await aiosqlite.connect(self._db_path)
        # Enable WAL for better concurrent read performance
        await self._db.execute("PRAGMA journal_mode=WAL;")

        # Create tables
        await self._db.executescript(_SCHEMA_SIGNALS)
        for idx in _INDEX_SIGNALS:
            await self._db.execute(idx)

        await self._db.executescript(_SCHEMA_TRADES)
        for idx in _INDEX_TRADES:
            await self._db.execute(idx)

        await self._db.executescript(_SCHEMA_PORTFOLIO)
        for idx in _INDEX_PORTFOLIO:
            await self._db.execute(idx)

        await self._db.executescript(_SCHEMA_DAILY_STATS)

        await self._db.commit()
        logger.info("Database initialised at %s", self._db_path)

    async def close(self) -> None:
        """Commit pending changes and close the database."""
        if self._db:
            await self._db.commit()
            await self._db.close()
            self._db = None
            logger.info("Database closed")

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    async def record_signal(self, signal: Signal) -> None:
        """Insert a signal record into the signals table."""
        if self._db is None:
            return
        try:
            await self._db.execute(
                """
                INSERT INTO signals
                    (timestamp, strategy, reactor_source, condition_id, token_id,
                     side, confidence, urgency, price_at_signal, metadata, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal.created_at.isoformat(),
                    signal.strategy.value,
                    signal.reactor_source.value,
                    signal.condition_id,
                    signal.token_id,
                    signal.side.value,
                    signal.confidence,
                    str(signal.urgency.value),
                    signal.price_at_signal,
                    json.dumps(signal.metadata) if signal.metadata else None,
                    signal.expires_at.isoformat(),
                ),
            )
            await self._db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to record signal %s", signal.id)

    # ------------------------------------------------------------------
    # Trades
    # ------------------------------------------------------------------

    async def record_trade(self, result: TradeResult) -> None:
        """Insert a trade result into the trades table."""
        if self._db is None:
            return
        try:
            risk_layers_json = json.dumps(
                [
                    {
                        "layer": rl.layer,
                        "name": rl.name,
                        "passed": rl.passed,
                        "detail": rl.detail,
                        "adjusted_size": rl.adjusted_size,
                    }
                    for rl in result.risk_layers
                ]
            )
            await self._db.execute(
                """
                INSERT INTO trades
                    (timestamp, condition_id, token_id, side, price, size, cost_usdc,
                     order_type, executor_mode, reactor_source, order_id, status,
                     confidence, golden_cross, convergence, signals_used, risk_layers,
                     holding_cost, fee_cost, is_dry_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.created_at.isoformat(),
                    result.condition_id,
                    result.token_id,
                    result.side.value,
                    result.price,
                    result.size_tokens,
                    result.cost_usdc,
                    result.order_type.value,
                    result.executor_mode.value,
                    result.reactor_source.value,
                    result.order_id,
                    result.status.value,
                    result.confidence,
                    1 if result.golden_cross else 0,
                    result.convergence_count,
                    json.dumps(result.signals_used),
                    risk_layers_json,
                    result.holding_cost,
                    result.fee_cost,
                    1 if result.is_dry_run else 0,
                ),
            )
            await self._db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to record trade %s", result.id)

    # ------------------------------------------------------------------
    # Portfolio snapshots
    # ------------------------------------------------------------------

    async def record_portfolio_snapshot(self, positions: list[Position]) -> None:
        """Insert a portfolio snapshot (all current positions)."""
        if self._db is None:
            return
        try:
            now = datetime.utcnow().isoformat()
            rows = [
                (
                    now,
                    pos.condition_id,
                    pos.token_id,
                    pos.outcome,
                    pos.size,
                    pos.avg_price,
                    pos.current_price,
                    pos.unrealized_pnl,
                    pos.market_question,
                    1 if pos.is_dry_run else 0,
                )
                for pos in positions
            ]
            await self._db.executemany(
                """
                INSERT INTO portfolio
                    (timestamp, condition_id, token_id, outcome, size,
                     avg_price, current_price, unrealized_pnl, market_question, is_dry_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            await self._db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to record portfolio snapshot")

    # ------------------------------------------------------------------
    # Daily stats (AC-35)
    # ------------------------------------------------------------------

    async def update_daily_stats(self, date: str, stats: DailyStats) -> None:
        """Upsert daily statistics for a given date."""
        if self._db is None:
            return
        try:
            await self._db.execute(
                """
                INSERT INTO daily_stats
                    (date, total_trades, winning_trades, losing_trades, total_pnl,
                     max_drawdown, peak_bankroll, signals_generated, signals_converted,
                     alpha_signals, omega_signals, golden_crosses, circuit_breaker_hit,
                     frequency_mode, is_dry_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_trades = excluded.total_trades,
                    winning_trades = excluded.winning_trades,
                    losing_trades = excluded.losing_trades,
                    total_pnl = excluded.total_pnl,
                    max_drawdown = excluded.max_drawdown,
                    peak_bankroll = excluded.peak_bankroll,
                    signals_generated = excluded.signals_generated,
                    signals_converted = excluded.signals_converted,
                    alpha_signals = excluded.alpha_signals,
                    omega_signals = excluded.omega_signals,
                    golden_crosses = excluded.golden_crosses,
                    circuit_breaker_hit = excluded.circuit_breaker_hit,
                    frequency_mode = excluded.frequency_mode,
                    is_dry_run = excluded.is_dry_run
                """,
                (
                    date,
                    stats.total_trades,
                    stats.winning_trades,
                    stats.losing_trades,
                    stats.total_pnl,
                    stats.max_drawdown,
                    stats.peak_bankroll,
                    stats.signals_generated,
                    stats.signals_converted,
                    stats.alpha_signals,
                    stats.omega_signals,
                    stats.golden_crosses,
                    stats.circuit_breaker_hit,
                    stats.frequency_mode,
                    1 if stats.is_dry_run else 0,
                ),
            )
            await self._db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to update daily stats for %s", date)

    async def get_daily_stats(self, date: str) -> DailyStats | None:
        """Retrieve daily statistics for a given date."""
        if self._db is None:
            return None
        try:
            async with self._db.execute(
                "SELECT * FROM daily_stats WHERE date = ?", (date,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return DailyStats(
                    date=row[1],
                    total_trades=row[2],
                    winning_trades=row[3],
                    losing_trades=row[4],
                    total_pnl=row[5],
                    max_drawdown=row[6],
                    peak_bankroll=row[7],
                    signals_generated=row[8],
                    signals_converted=row[9],
                    alpha_signals=row[10],
                    omega_signals=row[11],
                    golden_crosses=row[12],
                    circuit_breaker_hit=row[13],
                    frequency_mode=row[14],
                    is_dry_run=bool(row[15]),
                )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to get daily stats for %s", date)
            return None

    # ------------------------------------------------------------------
    # Frequency Governor persistence (AC-30)
    # ------------------------------------------------------------------

    async def get_frequency_mode(self) -> str | None:
        """Read the most recent frequency_mode from daily_stats (DB flag for AC-30)."""
        if self._db is None:
            return None
        try:
            async with self._db.execute(
                "SELECT frequency_mode FROM daily_stats ORDER BY date DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
        except Exception:  # noqa: BLE001
            logger.exception("Failed to get frequency mode from DB")
            return None

    async def set_frequency_mode(self, mode: str) -> None:
        """Update the frequency_mode for today's daily_stats record (AC-30)."""
        if self._db is None:
            return
        today = datetime.utcnow().strftime("%Y-%m-%d")
        try:
            # Ensure a row exists for today
            await self._db.execute(
                """
                INSERT INTO daily_stats (date, frequency_mode)
                VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET frequency_mode = excluded.frequency_mode
                """,
                (today, mode),
            )
            await self._db.commit()
            logger.info("Frequency mode set to %s in DB", mode)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to set frequency mode in DB")

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_trades_for_date(self, date: str) -> list[dict[str, Any]]:
        """Retrieve all trades for a given date (YYYY-MM-DD)."""
        if self._db is None:
            return []
        try:
            async with self._db.execute(
                "SELECT * FROM trades WHERE timestamp LIKE ?",
                (f"{date}%",),
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return [dict(zip(columns, row)) for row in rows]
        except Exception:  # noqa: BLE001
            logger.exception("Failed to get trades for %s", date)
            return []

    async def get_signal_count_for_date(self, date: str) -> int:
        """Count signals generated on a given date."""
        if self._db is None:
            return 0
        try:
            async with self._db.execute(
                "SELECT COUNT(*) FROM signals WHERE timestamp LIKE ?",
                (f"{date}%",),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception:  # noqa: BLE001
            return 0
