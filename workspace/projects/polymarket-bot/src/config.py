"""
설정 로드 모듈.
.env 파일 또는 환경 변수에서 Config dataclass를 생성합니다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict

from dotenv import load_dotenv

from src.shared.types import RiskConfig, MetaBotConfig, STRATEGY_DEFAULT_INTERVALS


@dataclass
class Config:
    """
    모든 설정을 하나의 dataclass로. .env에서 로드.
    통합 계약 11.1의 환경 변수명을 그대로 사용합니다.
    """

    # API 인증 (실거래 시 필수)
    private_key: str = ""           # POLY_PRIVATE_KEY
    api_key: str = ""               # POLY_API_KEY
    api_secret: str = ""            # POLY_API_SECRET
    api_passphrase: str = ""        # POLY_API_PASSPHRASE
    wallet_address: str = ""        # POLY_WALLET_ADDRESS

    # 실행 모드
    dry_run: bool = True            # DRY_RUN (기본값 True = 안전)
    log_level: str = "INFO"         # LOG_LEVEL

    # DB
    db_path: str = "data/polymarket_bot.db"   # DB_PATH

    # 엔진
    cycle_interval: int = 30        # CYCLE_INTERVAL (초)

    # Rate Limit
    max_requests_per_minute: int = 80

    # 리스크
    risk: RiskConfig = field(default_factory=RiskConfig)

    # 전략별 polling 간격 (초)
    strategy_intervals: Dict[str, int] = field(
        default_factory=lambda: dict(STRATEGY_DEFAULT_INTERVALS)
    )

    # 메타봇 설정
    meta_bot: MetaBotConfig = field(default_factory=MetaBotConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """
        os.environ + dotenv에서 Config 생성.
        .env 파일이 있으면 로드, 없으면 환경 변수 직접 사용.
        """
        load_dotenv(override=False)  # 이미 설정된 환경변수 우선

        def _bool(val: str, default: bool) -> bool:
            if not val:
                return default
            return val.strip().lower() in ("1", "true", "yes", "on")

        def _int(val: str, default: int) -> int:
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        dry_run = _bool(os.environ.get("DRY_RUN", ""), True)
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        db_path = os.environ.get("DB_PATH", "data/polymarket_bot.db")
        cycle_interval = _int(os.environ.get("CYCLE_INTERVAL", ""), 30)

        return cls(
            private_key=os.environ.get("POLY_PRIVATE_KEY", ""),
            api_key=os.environ.get("POLY_API_KEY", ""),
            api_secret=os.environ.get("POLY_API_SECRET", ""),
            api_passphrase=os.environ.get("POLY_API_PASSPHRASE", ""),
            wallet_address=os.environ.get("POLY_WALLET_ADDRESS", ""),
            dry_run=dry_run,
            log_level=log_level,
            db_path=db_path,
            cycle_interval=cycle_interval,
        )

    def validate_for_live_trading(self) -> None:
        """
        실거래 모드에서 필수 설정이 모두 있는지 확인.
        # @risk: 금융거래 — 설정 누락 시 인증 실패로 주문이 거부될 수 있음.
        """
        missing = []
        if not self.private_key:
            missing.append("POLY_PRIVATE_KEY")
        if not self.api_key:
            missing.append("POLY_API_KEY")
        if not self.api_secret:
            missing.append("POLY_API_SECRET")
        if not self.api_passphrase:
            missing.append("POLY_API_PASSPHRASE")
        if not self.wallet_address:
            missing.append("POLY_WALLET_ADDRESS")

        if missing:
            raise ValueError(
                f"실거래 모드에서 필수 환경 변수가 없습니다: {', '.join(missing)}\n"
                ".env.example을 참조하여 .env 파일을 설정하세요."
            )
