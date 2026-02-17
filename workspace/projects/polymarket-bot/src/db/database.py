"""
Database — SQLite 연결 및 쿼리.
모든 DB 작업은 이 클래스를 통해 수행합니다.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.shared.types import (
    OrderResult,
    Position,
    Signal,
    TradeDecision,
)

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite 기반 트레이딩 봇 DB.
    DB 파일 경로: config.db_path (기본: data/polymarket_bot.db).
    """

    def __init__(self, db_path: str = "data/polymarket_bot.db") -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """DB 연결 + 스키마 초기화."""
        # DB 디렉토리 생성
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")  # 쓰기 성능 향상
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._apply_schema()
        logger.info("DB 연결 완료: %s", os.path.abspath(self.db_path))

    def close(self) -> None:
        """DB 연결 종료."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("DB 연결 종료.")

    def _apply_schema(self) -> None:
        """schema.sql DDL 실행."""
        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            logger.error("schema.sql 파일 없음: %s", schema_path)
            return
        sql = schema_path.read_text(encoding="utf-8")
        with self._conn:
            self._conn.executescript(sql)

    @property
    def conn(self) -> sqlite3.Connection:
        """연결 검증 후 반환."""
        if self._conn is None:
            raise RuntimeError("DB가 연결되지 않았습니다. connect()를 먼저 호출하세요.")
        return self._conn

    # ----------------------------------------------------------------
    # 거래 로그
    # ----------------------------------------------------------------

    def insert_trade_log(self, result: OrderResult) -> int:
        """거래 실행 결과를 trade_logs에 삽입."""
        strategies_json = json.dumps(result.contributing_strategies)
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO trade_logs
                    (condition_id, token_id, direction, token_side, price, size,
                     order_type, order_id, status, composite_score,
                     contributing_strategies, dry_run, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.condition_id,
                    result.token_id,
                    result.direction.value if hasattr(result.direction, "value") else result.direction,
                    result.token_side.value if hasattr(result.token_side, "value") else result.token_side,
                    result.price,
                    result.size,
                    result.order_type.value if hasattr(result.order_type, "value") else result.order_type,
                    result.order_id,
                    result.status.value if hasattr(result.status, "value") else result.status,
                    result.composite_score,
                    strategies_json,
                    1 if result.dry_run else 0,
                    result.error_message or "",
                ),
            )
            return cursor.lastrowid

    def get_recent_trades(self, limit: int = 50, dry_run: Optional[bool] = None) -> List[Dict]:
        """최근 거래 기록 조회."""
        if dry_run is None:
            rows = self.conn.execute(
                "SELECT * FROM trade_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM trade_logs WHERE dry_run=? ORDER BY timestamp DESC LIMIT ?",
                (1 if dry_run else 0, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ----------------------------------------------------------------
    # 시그널 로그
    # ----------------------------------------------------------------

    def insert_signal_logs(self, signals: List[Signal]) -> None:
        """시그널 리스트를 signal_logs에 배치 삽입."""
        rows = []
        for s in signals:
            raw_json = json.dumps(s.raw_data) if s.raw_data else None
            rows.append((
                s.strategy_name,
                s.condition_id,
                s.token_id,
                s.market_question,
                s.direction.value if hasattr(s.direction, "value") else s.direction,
                s.token_side.value if hasattr(s.token_side, "value") else s.token_side,
                s.strength,
                s.confidence,
                s.reason,
                s.suggested_price,
                raw_json,
            ))
        with self.conn:
            self.conn.executemany(
                """
                INSERT INTO signal_logs
                    (strategy_name, condition_id, token_id, market_question,
                     direction, token_side, strength, confidence, reason,
                     suggested_price, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    # ----------------------------------------------------------------
    # 가상 포지션 (드라이런)
    # ----------------------------------------------------------------

    def insert_virtual_position(
        self, decision: TradeDecision, entry_price: float
    ) -> int:
        """드라이런 가상 포지션 삽입."""
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO virtual_positions
                    (condition_id, token_id, market_question, direction, token_side,
                     entry_price, current_price, size, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
                """,
                (
                    decision.condition_id,
                    decision.token_id,
                    decision.market_question,
                    decision.direction.value if hasattr(decision.direction, "value") else decision.direction,
                    decision.token_side.value if hasattr(decision.token_side, "value") else decision.token_side,
                    entry_price,
                    entry_price,
                    decision.size,
                ),
            )
            return cursor.lastrowid

    def update_virtual_position_price(
        self, token_id: str, current_price: float
    ) -> None:
        """가상 포지션 현재가 + 미실현 P&L 업데이트."""
        # direction_sign: BUY=+1, SELL=-1
        rows = self.conn.execute(
            "SELECT id, direction, entry_price, size FROM virtual_positions "
            "WHERE token_id=? AND status='OPEN'",
            (token_id,)
        ).fetchall()

        with self.conn:
            for row in rows:
                sign = 1.0 if row["direction"] == "BUY" else -1.0
                pnl = (current_price - row["entry_price"]) * row["size"] * sign
                self.conn.execute(
                    "UPDATE virtual_positions SET current_price=?, unrealized_pnl=? WHERE id=?",
                    (current_price, pnl, row["id"]),
                )

    def get_open_virtual_positions(self) -> List[Dict]:
        """오픈 가상 포지션 목록 조회."""
        rows = self.conn.execute(
            "SELECT * FROM virtual_positions WHERE status='OPEN' ORDER BY opened_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def close_virtual_position(self, position_id: int, exit_price: float) -> None:
        """가상 포지션 청산."""
        row = self.conn.execute(
            "SELECT direction, entry_price, size FROM virtual_positions WHERE id=?",
            (position_id,)
        ).fetchone()
        if not row:
            return
        sign = 1.0 if row["direction"] == "BUY" else -1.0
        realized = (exit_price - row["entry_price"]) * row["size"] * sign
        with self.conn:
            self.conn.execute(
                """
                UPDATE virtual_positions
                SET status='CLOSED', closed_at=datetime('now'),
                    current_price=?, realized_pnl=?, unrealized_pnl=0.0
                WHERE id=?
                """,
                (exit_price, realized, position_id),
            )

    # ----------------------------------------------------------------
    # 일일 P&L
    # ----------------------------------------------------------------

    def upsert_daily_pnl(
        self,
        date_str: str,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
        total_pnl: float,
        max_drawdown: float,
        dry_run: bool,
    ) -> None:
        """일일 P&L 요약 upsert."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO daily_pnl
                    (date, total_trades, winning_trades, losing_trades,
                     total_pnl, max_drawdown, dry_run)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_trades=excluded.total_trades,
                    winning_trades=excluded.winning_trades,
                    losing_trades=excluded.losing_trades,
                    total_pnl=excluded.total_pnl,
                    max_drawdown=excluded.max_drawdown
                """,
                (
                    date_str,
                    total_trades,
                    winning_trades,
                    losing_trades,
                    total_pnl,
                    max_drawdown,
                    1 if dry_run else 0,
                ),
            )

    def get_today_pnl(self, dry_run: bool = True) -> float:
        """오늘 실현 + 가상 P&L 합계. 리스크 관리에서 일일 손실 한도 확인에 사용."""
        today = date.today().isoformat()
        # trade_logs에서 오늘 실현 P&L (현재는 price * size의 합으로 근사; 실제 구현에서는 별도 계산)
        row = self.conn.execute(
            "SELECT total_pnl FROM daily_pnl WHERE date=? AND dry_run=?",
            (today, 1 if dry_run else 0)
        ).fetchone()
        if row:
            return float(row["total_pnl"])

        # daily_pnl이 없으면 가상 포지션에서 계산
        if dry_run:
            row2 = self.conn.execute(
                "SELECT SUM(unrealized_pnl) + SUM(realized_pnl) as pnl "
                "FROM virtual_positions WHERE date(opened_at)=?",
                (today,)
            ).fetchone()
            return float(row2["pnl"] or 0.0) if row2 else 0.0
        return 0.0

    def get_open_order_count(self) -> int:
        """오픈(PENDING) 상태 주문 수."""
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM trade_logs WHERE status='PENDING'"
        ).fetchone()
        return int(row["cnt"]) if row else 0
