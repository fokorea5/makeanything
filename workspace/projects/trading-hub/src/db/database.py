"""
Trading Hub — DB 연결 및 CRUD 함수

SQLite + aiosqlite 비동기 연결.
테이블: bots, assets, trades, alerts
"""

import json
import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)

# DB 파일 경로 (프로젝트 루트 기준)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
DB_PATH = os.path.join(_DATA_DIR, "trading_hub.db")


# ──────────────────────────────────────────────
# 연결 관리
# ──────────────────────────────────────────────

async def get_connection() -> aiosqlite.Connection:
    """aiosqlite 연결을 반환한다. WAL 모드 활성화."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ──────────────────────────────────────────────
# 테이블 생성
# ──────────────────────────────────────────────

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    type VARCHAR(30) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'idle',
    config TEXT NOT NULL DEFAULT '{}',
    api_key_encrypted TEXT,
    api_secret_encrypted TEXT,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER NOT NULL,
    currency VARCHAR(20) NOT NULL,
    balance REAL NOT NULL DEFAULT 0,
    locked REAL NOT NULL DEFAULT 0,
    value_usd REAL NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (bot_id) REFERENCES bots(id),
    UNIQUE (bot_id, currency)
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,
    price REAL NOT NULL,
    quantity REAL NOT NULL,
    total REAL NOT NULL,
    fee REAL NOT NULL DEFAULT 0,
    timestamp DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE INDEX IF NOT EXISTS idx_trades_bot_id ON trades(bot_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER,
    type VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    sent BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);
"""


async def init_db() -> None:
    """DB 초기화: 테이블 생성."""
    conn = await get_connection()
    try:
        await conn.executescript(_CREATE_TABLES_SQL)
        await conn.commit()
        logger.info("DB 초기화 완료: %s", DB_PATH)
    finally:
        await conn.close()


# ──────────────────────────────────────────────
# Bot CRUD
# ──────────────────────────────────────────────

async def create_bot(
    name: str,
    exchange: str,
    bot_type: str,
    config: Dict[str, Any],
    api_key_encrypted: Optional[str] = None,
    api_secret_encrypted: Optional[str] = None,
) -> Dict[str, Any]:
    """봇을 등록하고 생성된 레코드를 반환한다."""
    now = datetime.utcnow().isoformat()
    config_json = json.dumps(config) if isinstance(config, dict) else config
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO bots (name, exchange, type, status, config,
                              api_key_encrypted, api_secret_encrypted,
                              created_at, updated_at)
            VALUES (?, ?, ?, 'idle', ?, ?, ?, ?, ?)
            """,
            (name, exchange, bot_type, config_json,
             api_key_encrypted, api_secret_encrypted, now, now),
        )
        await conn.commit()
        bot_id = cursor.lastrowid
        return await get_bot(bot_id)  # type: ignore
    finally:
        await conn.close()


async def get_bot(bot_id: int) -> Optional[Dict[str, Any]]:
    """봇 상세 조회."""
    conn = await get_connection()
    try:
        cursor = await conn.execute("SELECT * FROM bots WHERE id = ?", (bot_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_dict(row)
    finally:
        await conn.close()


async def get_bots() -> List[Dict[str, Any]]:
    """전체 봇 목록."""
    conn = await get_connection()
    try:
        cursor = await conn.execute("SELECT * FROM bots ORDER BY id")
        rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        await conn.close()


async def update_bot_status(bot_id: int, status: str) -> Optional[Dict[str, Any]]:
    """봇 상태 변경."""
    now = datetime.utcnow().isoformat()
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE bots SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, bot_id),
        )
        await conn.commit()
        return await get_bot(bot_id)
    finally:
        await conn.close()


async def delete_bot(bot_id: int) -> bool:
    """봇 삭제."""
    conn = await get_connection()
    try:
        cursor = await conn.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


# ──────────────────────────────────────────────
# Asset CRUD
# ──────────────────────────────────────────────

async def upsert_asset(
    bot_id: int,
    currency: str,
    balance: float,
    locked: float = 0.0,
    value_usd: float = 0.0,
) -> Dict[str, Any]:
    """자산을 INSERT 또는 UPDATE (bot_id, currency 유니크)."""
    now = datetime.utcnow().isoformat()
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO assets (bot_id, currency, balance, locked, value_usd, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(bot_id, currency)
            DO UPDATE SET balance = excluded.balance,
                          locked = excluded.locked,
                          value_usd = excluded.value_usd,
                          updated_at = excluded.updated_at
            """,
            (bot_id, currency, balance, locked, value_usd, now),
        )
        await conn.commit()
        cursor = await conn.execute(
            "SELECT * FROM assets WHERE bot_id = ? AND currency = ?",
            (bot_id, currency),
        )
        row = await cursor.fetchone()
        return _row_to_dict(row)
    finally:
        await conn.close()


async def get_assets(bot_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """자산 목록. bot_id 지정 시 해당 봇만."""
    conn = await get_connection()
    try:
        if bot_id is not None:
            cursor = await conn.execute(
                """
                SELECT a.*, b.name as bot_name
                FROM assets a
                JOIN bots b ON a.bot_id = b.id
                WHERE a.bot_id = ?
                ORDER BY a.id
                """,
                (bot_id,),
            )
        else:
            cursor = await conn.execute(
                """
                SELECT a.*, b.name as bot_name
                FROM assets a
                JOIN bots b ON a.bot_id = b.id
                ORDER BY a.id
                """
            )
        rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        await conn.close()


async def get_asset_summary() -> Dict[str, Any]:
    """전체 자산 요약."""
    conn = await get_connection()
    try:
        # 전체 합계
        cursor = await conn.execute("SELECT COALESCE(SUM(value_usd), 0) as total FROM assets")
        row = await cursor.fetchone()
        total_value_usd = row["total"]

        # 봇 수
        cursor = await conn.execute("SELECT COUNT(*) as cnt FROM bots")
        row = await cursor.fetchone()
        bot_count = row["cnt"]

        # 통화별 합산
        cursor = await conn.execute(
            "SELECT currency, SUM(value_usd) as total FROM assets GROUP BY currency"
        )
        rows = await cursor.fetchall()
        assets_by_currency = {r["currency"]: r["total"] for r in rows}

        # 봇별 합산
        cursor = await conn.execute(
            """
            SELECT a.bot_id, b.name as bot_name,
                   SUM(a.value_usd) as total_value_usd,
                   GROUP_CONCAT(DISTINCT a.currency) as currencies
            FROM assets a
            JOIN bots b ON a.bot_id = b.id
            GROUP BY a.bot_id
            """
        )
        rows = await cursor.fetchall()
        assets_by_bot = []
        for r in rows:
            assets_by_bot.append({
                "bot_id": r["bot_id"],
                "bot_name": r["bot_name"],
                "total_value_usd": r["total_value_usd"],
                "currencies": r["currencies"].split(",") if r["currencies"] else [],
            })

        return {
            "total_value_usd": total_value_usd,
            "bot_count": bot_count,
            "assets_by_currency": assets_by_currency,
            "assets_by_bot": assets_by_bot,
        }
    finally:
        await conn.close()


# ──────────────────────────────────────────────
# Trade CRUD
# ──────────────────────────────────────────────

async def create_trade(
    bot_id: int,
    exchange: str,
    symbol: str,
    side: str,
    price: float,
    quantity: float,
    total: float,
    fee: float = 0.0,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """거래 기록 저장."""
    ts = timestamp or datetime.utcnow().isoformat()
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO trades (bot_id, exchange, symbol, side, price, quantity, total, fee, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (bot_id, exchange, symbol, side, price, quantity, total, fee, ts),
        )
        await conn.commit()
        trade_id = cursor.lastrowid
        cursor = await conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        row = await cursor.fetchone()
        return _row_to_dict(row)
    finally:
        await conn.close()


async def get_trades(
    bot_id: Optional[int] = None,
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    size: int = 20,
) -> Dict[str, Any]:
    """거래 목록 (필터 + 페이지네이션)."""
    conditions: List[str] = []
    params: List[Any] = []

    if bot_id is not None:
        conditions.append("bot_id = ?")
        params.append(bot_id)
    if symbol is not None:
        conditions.append("symbol = ?")
        params.append(symbol)
    if side is not None:
        conditions.append("side = ?")
        params.append(side)
    if start_date is not None:
        conditions.append("timestamp >= ?")
        params.append(start_date)
    if end_date is not None:
        conditions.append("timestamp <= ?")
        params.append(end_date)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    conn = await get_connection()
    try:
        # 전체 건수
        cursor = await conn.execute(
            f"SELECT COUNT(*) as cnt FROM trades {where}", params
        )
        row = await cursor.fetchone()
        total_count = row["cnt"]

        # 페이지 계산
        offset = (page - 1) * size
        total_pages = max(1, (total_count + size - 1) // size)

        # 데이터 조회
        cursor = await conn.execute(
            f"SELECT * FROM trades {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params + [size, offset],
        )
        rows = await cursor.fetchall()
        items = [_row_to_dict(r) for r in rows]

        return {
            "items": items,
            "total": total_count,
            "page": page,
            "size": size,
            "pages": total_pages,
        }
    finally:
        await conn.close()


# ──────────────────────────────────────────────
# Alert CRUD
# ──────────────────────────────────────────────

async def create_alert(
    alert_type: str,
    message: str,
    bot_id: Optional[int] = None,
    sent: bool = False,
) -> Dict[str, Any]:
    """알림 레코드 생성."""
    now = datetime.utcnow().isoformat()
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO alerts (bot_id, type, message, sent, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (bot_id, alert_type, message, int(sent), now),
        )
        await conn.commit()
        alert_id = cursor.lastrowid
        cursor = await conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        row = await cursor.fetchone()
        return _row_to_dict(row)
    finally:
        await conn.close()


async def update_alert_sent(alert_id: int, sent: bool = True) -> None:
    """알림 전송 완료 표시."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE alerts SET sent = ? WHERE id = ?", (int(sent), alert_id)
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_alerts(
    bot_id: Optional[int] = None,
    alert_type: Optional[str] = None,
    page: int = 1,
    size: int = 20,
) -> Dict[str, Any]:
    """알림 목록 (필터 + 페이지네이션)."""
    conditions: List[str] = []
    params: List[Any] = []

    if bot_id is not None:
        conditions.append("bot_id = ?")
        params.append(bot_id)
    if alert_type is not None:
        conditions.append("type = ?")
        params.append(alert_type)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    conn = await get_connection()
    try:
        cursor = await conn.execute(
            f"SELECT COUNT(*) as cnt FROM alerts {where}", params
        )
        row = await cursor.fetchone()
        total_count = row["cnt"]

        offset = (page - 1) * size
        total_pages = max(1, (total_count + size - 1) // size)

        cursor = await conn.execute(
            f"SELECT * FROM alerts {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [size, offset],
        )
        rows = await cursor.fetchall()
        items = [_row_to_dict(r) for r in rows]

        return {
            "items": items,
            "total": total_count,
            "page": page,
            "size": size,
            "pages": total_pages,
        }
    finally:
        await conn.close()


# ──────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────

def _row_to_dict(row) -> Dict[str, Any]:
    """aiosqlite.Row를 dict로 변환."""
    if row is None:
        return {}
    return dict(row)
