"""
Polymarket Reaper Bot v1.1 -- Unified Configuration Management

All modules access settings via `from config import Config`.
Reads .env file directly (no python-dotenv dependency).
Provides defaults for every parameter; DRY_RUN=true by default.

DESIGN.md 3.1 / AC-05
"""

from __future__ import annotations

import logging
import os
import pathlib
from typing import List

logger = logging.getLogger("reaper.config")

# ---------------------------------------------------------------------------
# .env parser (python-dotenv 미사용 -- DESIGN.md 3.1 준수)
# ---------------------------------------------------------------------------

_ENV_LOADED = False


def _load_env(path: str | None = None) -> None:
    """Parse a .env file and inject values into ``os.environ``.

    Only the first call has an effect; subsequent calls are no-ops.
    Lines starting with ``#`` or empty lines are skipped.
    Values may optionally be quoted with ``"`` or ``'``.
    Already-set environment variables are **not** overwritten
    (real env takes precedence over .env defaults).
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True

    if path is None:
        # Look for .env next to this file (project root)
        path = str(pathlib.Path(__file__).resolve().parent / ".env")

    env_path = pathlib.Path(path)
    if not env_path.is_file():
        logger.info(".env file not found at %s -- using OS environment only", path)
        return

    with env_path.open("r", encoding="utf-8") as fh:
        for lineno, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            # Skip blanks and comments
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                logger.warning(".env line %d skipped (no '='): %s", lineno, line)
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            # Do NOT overwrite existing env vars
            if key not in os.environ:
                os.environ[key] = value

    logger.info(".env loaded from %s", path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool = False) -> bool:
    val = _env(key, str(default)).lower()
    return val in ("1", "true", "yes")


def _env_float(key: str, default: float = 0.0) -> float:
    try:
        return float(_env(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_int(key: str, default: int = 0) -> int:
    try:
        return int(_env(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_list(key: str, default: List[str] | None = None) -> List[str]:
    """Comma-separated environment variable to list[str]."""
    raw = _env(key, "")
    if not raw:
        return default if default is not None else []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _mask_secret(value: str) -> str:
    """Return first 6 chars + '***' for safe logging of secrets."""
    if len(value) <= 6:
        return "***"
    return value[:6] + "***"


# ---------------------------------------------------------------------------
# Config singleton
# ---------------------------------------------------------------------------


class Config:
    """Centralised configuration -- one class, all settings.

    Call ``Config.load()`` once at startup to parse .env and populate values.
    All attributes are class-level so any module can simply do::

        from config import Config
        host = Config.CLOB_HOST
    """

    # === API endpoints (constants -- DESIGN.md 9.3) ===
    CLOB_HOST: str = "https://clob.polymarket.com"
    GAMMA_HOST: str = "https://gamma-api.polymarket.com"
    DATA_HOST: str = "https://data-api.polymarket.com"
    WS_MARKET_URL: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    WS_USER_URL: str = "wss://ws-subscriptions-clob.polymarket.com/ws/user"

    # === Authentication ===
    PRIVATE_KEY: str = ""
    POLY_API_KEY: str = ""
    POLY_API_SECRET: str = ""
    POLY_API_PASSPHRASE: str = ""
    WALLET_ADDRESS: str = ""
    SIGNATURE_TYPE: int = 0          # 0=EOA, 1=POLY_PROXY
    FUNDER_ADDRESS: str = ""         # POLY_PROXY only

    # === Risk Sentinel (AC-23~27) ===
    KELLY_FRACTION: float = 0.4
    MAX_SINGLE_MARKET: float = 0.15
    MAX_TOTAL_EXPOSURE: float = 0.60
    DAILY_LOSS_LIMIT: float = 0.08
    DD_THROTTLE_5: float = 0.05      # x0.5
    DD_THROTTLE_10: float = 0.10     # x0.25
    DD_HALT_15: float = 0.15         # halt

    # === Frequency Governor (AC-28~30) ===
    FREQUENCY_MODE: str = "AUTO"
    AUTO_DD_TURBO: float = 0.03
    AUTO_DD_NORMAL: float = 0.06

    # === Holding cost (AC-41) ===
    RISK_FREE_RATE: float = 0.05     # annual 5 %

    # === Execution cost filter (AC-42) ===
    MIN_PROFIT_THRESHOLD: float = 0.50  # USDC

    # === Engine ===
    DRY_RUN: bool = True
    DB_PATH: str = "data/reaper.db"
    LOG_LEVEL: str = "INFO"

    # === Strategy toggles ===
    STRATEGY_AMBIGUITY: bool = True
    STRATEGY_ORACLE_FEAR: bool = True
    STRATEGY_CONTRARIAN: bool = True
    STRATEGY_CORRELATED: bool = True
    STRATEGY_LIQUIDITY_VACUUM: bool = True
    STRATEGY_COMPLETE_SET: bool = True

    # === Strategy parameters ===
    AMBIGUITY_THRESHOLD: float = 0.6
    AMBIGUITY_SOURCE_PENALTY: float = 0.2
    AMBIGUITY_KEYWORDS: List[str] = [
        "might", "could", "possibly", "approximately", "around",
        "unclear", "ambiguous", "depending on", "subject to",
        "estimated", "roughly", "if", "unless",
    ]
    ORACLE_FEAR_DISCOUNT: float = 0.05
    ORACLE_FEAR_KEYWORDS: List[str] = [
        "oracle", "UMA", "dispute", "resolution",
        "challenged", "appealed", "contested", "arbitration",
    ]
    CONTRARIAN_Z_THRESHOLD: float = 2.0
    CONTRARIAN_WEEKEND_STDEV_MULT: float = 2.0
    CONTRARIAN_WEEKEND_BONUS: float = 0.10
    CORRELATED_CONDITIONAL_THRESHOLD: float = 1.5
    CORRELATED_SUM_THRESHOLD: float = 0.02
    LIQUIDITY_SPREAD_THRESHOLD: float = 0.05
    LIQUIDITY_DEPTH_RATIO: float = 3.0
    COMPLETE_SET_THRESHOLD: float = 0.03
    MARKET_AGE_HOURS: int = 48
    MARKET_AGE_BONUS: float = 0.15
    CROWDING_THRESHOLD: float = 0.80
    CROWDING_BONUS: float = 0.10
    VOL_PRICE_VOLUME_SURGE: float = 3.0
    VOL_PRICE_VOLUME_DROUGHT: float = 0.3
    VOL_PRICE_PRICE_THRESHOLD: float = 0.02
    VOL_PRICE_PRICE_VACUUM: float = 0.05

    # === Meta Brain ===
    META_SIGNAL_WINDOW_SEC: int = 600
    META_GOLDEN_CROSS_KELLY_MULT: float = 1.5

    # === Strategy weights ===
    WEIGHT_AMBIGUITY: float = 1.2
    WEIGHT_ORACLE_FEAR: float = 1.0
    WEIGHT_CONTRARIAN: float = 1.1
    WEIGHT_CORRELATED: float = 1.3
    WEIGHT_LIQUIDITY_VACUUM: float = 0.9
    WEIGHT_COMPLETE_SET: float = 1.4

    # === Executor ===
    SLIPPAGE_TOLERANCE: float = 0.02
    SNIPER_MAX_RETRY: int = 1
    PATIENT_POST_ONLY: bool = True

    # ------------------------------------------------------------------
    # Loader
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, env_path: str | None = None) -> None:
        """Parse ``.env`` and map values onto class attributes.

        Must be called once before any module accesses ``Config.*``.
        """
        _load_env(env_path)

        # --- Authentication --- #  # @risk: auth
        cls.PRIVATE_KEY = _env("POLY_PRIVATE_KEY", cls.PRIVATE_KEY)
        cls.POLY_API_KEY = _env("POLY_API_KEY", cls.POLY_API_KEY)
        cls.POLY_API_SECRET = _env("POLY_API_SECRET", cls.POLY_API_SECRET)
        cls.POLY_API_PASSPHRASE = _env("POLY_API_PASSPHRASE", cls.POLY_API_PASSPHRASE)
        cls.WALLET_ADDRESS = _env("POLY_WALLET_ADDRESS", cls.WALLET_ADDRESS)
        cls.SIGNATURE_TYPE = _env_int("POLY_SIGNATURE_TYPE", cls.SIGNATURE_TYPE)
        cls.FUNDER_ADDRESS = _env("POLY_FUNDER_ADDRESS", cls.FUNDER_ADDRESS)

        # --- Engine --- #
        cls.DRY_RUN = _env_bool("DRY_RUN", cls.DRY_RUN)
        cls.DB_PATH = _env("DB_PATH", cls.DB_PATH)
        cls.LOG_LEVEL = _env("LOG_LEVEL", cls.LOG_LEVEL).upper()

        # --- Frequency Governor --- #
        cls.FREQUENCY_MODE = _env("FREQUENCY_MODE", cls.FREQUENCY_MODE).upper()
        cls.AUTO_DD_TURBO = _env_float("AUTO_DD_TURBO", cls.AUTO_DD_TURBO)
        cls.AUTO_DD_NORMAL = _env_float("AUTO_DD_NORMAL", cls.AUTO_DD_NORMAL)

        # --- Risk --- #
        cls.KELLY_FRACTION = _env_float("KELLY_FRACTION", cls.KELLY_FRACTION)
        cls.MAX_SINGLE_MARKET = _env_float("MAX_SINGLE_MARKET", cls.MAX_SINGLE_MARKET)
        cls.MAX_TOTAL_EXPOSURE = _env_float("MAX_TOTAL_EXPOSURE", cls.MAX_TOTAL_EXPOSURE)
        cls.DAILY_LOSS_LIMIT = _env_float("DAILY_LOSS_LIMIT", cls.DAILY_LOSS_LIMIT)
        cls.DD_THROTTLE_5 = _env_float("DD_THROTTLE_5", cls.DD_THROTTLE_5)
        cls.DD_THROTTLE_10 = _env_float("DD_THROTTLE_10", cls.DD_THROTTLE_10)
        cls.DD_HALT_15 = _env_float("DD_HALT_15", cls.DD_HALT_15)
        cls.RISK_FREE_RATE = _env_float("RISK_FREE_RATE", cls.RISK_FREE_RATE)
        cls.MIN_PROFIT_THRESHOLD = _env_float("MIN_PROFIT_THRESHOLD", cls.MIN_PROFIT_THRESHOLD)

        # --- Strategy toggles --- #
        cls.STRATEGY_AMBIGUITY = _env_bool("STRATEGY_AMBIGUITY", cls.STRATEGY_AMBIGUITY)
        cls.STRATEGY_ORACLE_FEAR = _env_bool("STRATEGY_ORACLE_FEAR", cls.STRATEGY_ORACLE_FEAR)
        cls.STRATEGY_CONTRARIAN = _env_bool("STRATEGY_CONTRARIAN", cls.STRATEGY_CONTRARIAN)
        cls.STRATEGY_CORRELATED = _env_bool("STRATEGY_CORRELATED", cls.STRATEGY_CORRELATED)
        cls.STRATEGY_LIQUIDITY_VACUUM = _env_bool("STRATEGY_LIQUIDITY_VACUUM", cls.STRATEGY_LIQUIDITY_VACUUM)
        cls.STRATEGY_COMPLETE_SET = _env_bool("STRATEGY_COMPLETE_SET", cls.STRATEGY_COMPLETE_SET)

        # --- Strategy parameters --- #
        cls.AMBIGUITY_THRESHOLD = _env_float("AMBIGUITY_THRESHOLD", cls.AMBIGUITY_THRESHOLD)
        cls.AMBIGUITY_SOURCE_PENALTY = _env_float("AMBIGUITY_SOURCE_PENALTY", cls.AMBIGUITY_SOURCE_PENALTY)
        kw = _env_list("AMBIGUITY_KEYWORDS")
        if kw:
            cls.AMBIGUITY_KEYWORDS = kw
        cls.ORACLE_FEAR_DISCOUNT = _env_float("ORACLE_FEAR_DISCOUNT", cls.ORACLE_FEAR_DISCOUNT)
        ok = _env_list("ORACLE_FEAR_KEYWORDS")
        if ok:
            cls.ORACLE_FEAR_KEYWORDS = ok
        cls.CONTRARIAN_Z_THRESHOLD = _env_float("CONTRARIAN_Z_THRESHOLD", cls.CONTRARIAN_Z_THRESHOLD)
        cls.CONTRARIAN_WEEKEND_STDEV_MULT = _env_float("CONTRARIAN_WEEKEND_STDEV_MULT", cls.CONTRARIAN_WEEKEND_STDEV_MULT)
        cls.CONTRARIAN_WEEKEND_BONUS = _env_float("CONTRARIAN_WEEKEND_BONUS", cls.CONTRARIAN_WEEKEND_BONUS)
        cls.CORRELATED_CONDITIONAL_THRESHOLD = _env_float("CORRELATED_CONDITIONAL_THRESHOLD", cls.CORRELATED_CONDITIONAL_THRESHOLD)
        cls.CORRELATED_SUM_THRESHOLD = _env_float("CORRELATED_SUM_THRESHOLD", cls.CORRELATED_SUM_THRESHOLD)
        cls.LIQUIDITY_SPREAD_THRESHOLD = _env_float("LIQUIDITY_SPREAD_THRESHOLD", cls.LIQUIDITY_SPREAD_THRESHOLD)
        cls.LIQUIDITY_DEPTH_RATIO = _env_float("LIQUIDITY_DEPTH_RATIO", cls.LIQUIDITY_DEPTH_RATIO)
        cls.COMPLETE_SET_THRESHOLD = _env_float("COMPLETE_SET_THRESHOLD", cls.COMPLETE_SET_THRESHOLD)
        cls.MARKET_AGE_HOURS = _env_int("MARKET_AGE_HOURS", cls.MARKET_AGE_HOURS)
        cls.MARKET_AGE_BONUS = _env_float("MARKET_AGE_BONUS", cls.MARKET_AGE_BONUS)
        cls.CROWDING_THRESHOLD = _env_float("CROWDING_THRESHOLD", cls.CROWDING_THRESHOLD)
        cls.CROWDING_BONUS = _env_float("CROWDING_BONUS", cls.CROWDING_BONUS)
        cls.VOL_PRICE_VOLUME_SURGE = _env_float("VOL_PRICE_VOLUME_SURGE", cls.VOL_PRICE_VOLUME_SURGE)
        cls.VOL_PRICE_VOLUME_DROUGHT = _env_float("VOL_PRICE_VOLUME_DROUGHT", cls.VOL_PRICE_VOLUME_DROUGHT)
        cls.VOL_PRICE_PRICE_THRESHOLD = _env_float("VOL_PRICE_PRICE_THRESHOLD", cls.VOL_PRICE_PRICE_THRESHOLD)
        cls.VOL_PRICE_PRICE_VACUUM = _env_float("VOL_PRICE_PRICE_VACUUM", cls.VOL_PRICE_PRICE_VACUUM)

        # --- Meta Brain --- #
        cls.META_SIGNAL_WINDOW_SEC = _env_int("META_SIGNAL_WINDOW_SEC", cls.META_SIGNAL_WINDOW_SEC)
        cls.META_GOLDEN_CROSS_KELLY_MULT = _env_float("META_GOLDEN_CROSS_KELLY_MULT", cls.META_GOLDEN_CROSS_KELLY_MULT)

        # --- Strategy weights --- #
        cls.WEIGHT_AMBIGUITY = _env_float("WEIGHT_AMBIGUITY", cls.WEIGHT_AMBIGUITY)
        cls.WEIGHT_ORACLE_FEAR = _env_float("WEIGHT_ORACLE_FEAR", cls.WEIGHT_ORACLE_FEAR)
        cls.WEIGHT_CONTRARIAN = _env_float("WEIGHT_CONTRARIAN", cls.WEIGHT_CONTRARIAN)
        cls.WEIGHT_CORRELATED = _env_float("WEIGHT_CORRELATED", cls.WEIGHT_CORRELATED)
        cls.WEIGHT_LIQUIDITY_VACUUM = _env_float("WEIGHT_LIQUIDITY_VACUUM", cls.WEIGHT_LIQUIDITY_VACUUM)
        cls.WEIGHT_COMPLETE_SET = _env_float("WEIGHT_COMPLETE_SET", cls.WEIGHT_COMPLETE_SET)

        # --- Executor --- #
        cls.SLIPPAGE_TOLERANCE = _env_float("SLIPPAGE_TOLERANCE", cls.SLIPPAGE_TOLERANCE)
        cls.SNIPER_MAX_RETRY = _env_int("SNIPER_MAX_RETRY", cls.SNIPER_MAX_RETRY)
        cls.PATIENT_POST_ONLY = _env_bool("PATIENT_POST_ONLY", cls.PATIENT_POST_ONLY)

        # --- Logging --- #
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL, logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

        # Secret masking in startup log
        logger.info(
            "Config loaded  DRY_RUN=%s  FREQUENCY_MODE=%s  WALLET=%s  API_KEY=%s",
            cls.DRY_RUN,
            cls.FREQUENCY_MODE,
            _mask_secret(cls.WALLET_ADDRESS) if cls.WALLET_ADDRESS else "(unset)",
            _mask_secret(cls.POLY_API_KEY) if cls.POLY_API_KEY else "(unset)",
        )
