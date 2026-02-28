-- schema.sql — Polymarket 트레이딩 봇 DB 스키마
-- DESIGN.md 섹션 9 기반.

-- ============================================================
-- 거래 기록
-- ============================================================
CREATE TABLE IF NOT EXISTS trade_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    condition_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    market_question TEXT,
    direction TEXT NOT NULL,           -- 'BUY' or 'SELL'
    token_side TEXT NOT NULL,          -- 'YES' or 'NO'
    price REAL NOT NULL,
    size REAL NOT NULL,
    order_type TEXT NOT NULL,          -- 'GTC', 'FOK', etc.
    order_id TEXT,
    status TEXT NOT NULL,              -- 'FILLED', 'PARTIAL', 'FAILED', 'PENDING'
    composite_score REAL,
    contributing_strategies TEXT,       -- JSON: ["resolution_arb", "contrarian"]
    dry_run INTEGER NOT NULL DEFAULT 0, -- 1 = 드라이런
    error_message TEXT
);

-- ============================================================
-- 시그널 로그
-- ============================================================
CREATE TABLE IF NOT EXISTS signal_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    strategy_name TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    token_id TEXT,
    market_question TEXT,
    direction TEXT NOT NULL,
    token_side TEXT NOT NULL,
    strength REAL NOT NULL,
    confidence REAL NOT NULL,
    reason TEXT,
    suggested_price REAL,
    raw_data TEXT                       -- JSON: 전략별 분석 상세
);

-- ============================================================
-- 가상 포지션 (드라이런용)
-- ============================================================
CREATE TABLE IF NOT EXISTS virtual_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opened_at TEXT NOT NULL DEFAULT (datetime('now')),
    closed_at TEXT,
    condition_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    market_question TEXT,
    direction TEXT NOT NULL,
    token_side TEXT NOT NULL,
    entry_price REAL NOT NULL,
    current_price REAL,
    size REAL NOT NULL,
    unrealized_pnl REAL DEFAULT 0.0,
    realized_pnl REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'OPEN'  -- 'OPEN' or 'CLOSED'
);

-- ============================================================
-- 일일 P&L 요약
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_pnl (
    date TEXT PRIMARY KEY,              -- 'YYYY-MM-DD'
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0.0,
    max_drawdown REAL DEFAULT 0.0,
    dry_run INTEGER NOT NULL DEFAULT 0
);

-- ============================================================
-- 인덱스
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_trade_logs_timestamp ON trade_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_trade_logs_condition ON trade_logs(condition_id);
CREATE INDEX IF NOT EXISTS idx_signal_logs_timestamp ON signal_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_signal_logs_strategy ON signal_logs(strategy_name);
CREATE INDEX IF NOT EXISTS idx_virtual_positions_status ON virtual_positions(status);
