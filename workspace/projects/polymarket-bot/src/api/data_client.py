"""
DataClient — Polymarket Data API 호출.
포지션, 포트폴리오, 거래 내역 조회.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from src.api.rate_limiter import RateLimiter
from src.shared.types import DATA_BASE_URL, Position

logger = logging.getLogger(__name__)


class DataClient:
    """
    Data API (https://data-api.polymarket.com) 클라이언트.
    인증 불필요 (지갑 주소만 파라미터로 사용).

    # @risk: 개인정보 — wallet_address는 공개 주소이지만 포지션 정보가 노출됩니다.
    """

    BASE_URL = DATA_BASE_URL

    def __init__(self, wallet_address: str, rate_limiter: RateLimiter) -> None:
        self.wallet_address = wallet_address
        self.rate_limiter = rate_limiter
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    # ----------------------------------------------------------------
    # 내부 헬퍼
    # ----------------------------------------------------------------

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        """GET 요청 + 429 재시도."""
        url = f"{self.BASE_URL}{path}"
        for attempt in range(3):
            self.rate_limiter.wait_if_needed()
            try:
                resp = self._session.get(url, params=params, timeout=15)
                self.rate_limiter.record_request()
                if resp.status_code == 429:
                    self.rate_limiter.handle_429(attempt)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                if attempt == 2:
                    logger.error("Data GET %s 3회 실패: %s", path, exc)
                    raise
                logger.warning("Data GET 실패 (시도 %d/3): %s", attempt + 1, exc)
                time.sleep(2 ** attempt)
        return {}

    def _parse_position(self, raw: Dict) -> Optional[Position]:
        """Data API 포지션 응답 → Position dataclass 변환."""
        # @confidence: low — Data API 스키마 검증 필요.
        try:
            size = float(raw.get("size", raw.get("currentValue", 0)) or 0)
            avg_price = float(raw.get("avgPrice", raw.get("averagePrice", 0)) or 0)
            current_price = float(raw.get("curPrice", raw.get("currentPrice", avg_price)) or avg_price)
            unrealized = float(raw.get("unrealizedPnl", 0) or 0)
            realized = float(raw.get("realizedPnl", 0) or 0)

            return Position(
                condition_id=raw.get("conditionId", raw.get("condition_id", "")),
                token_id=raw.get("tokenId", raw.get("token_id", raw.get("asset", ""))),
                market_question=raw.get("title", raw.get("question", raw.get("market", ""))),
                outcome=raw.get("outcome", "Yes"),
                size=size,
                avg_price=avg_price,
                current_price=current_price,
                unrealized_pnl=unrealized,
                realized_pnl=realized,
            )
        except Exception as exc:
            logger.warning("포지션 파싱 실패: %s | raw=%s", exc, raw)
            return None

    # ----------------------------------------------------------------
    # 공개 API
    # ----------------------------------------------------------------

    def get_positions(self) -> List[Position]:
        """
        현재 보유 포지션 조회.
        wallet_address가 비어 있으면 빈 리스트 반환.
        """
        if not self.wallet_address:
            logger.warning("wallet_address 미설정. 포지션 조회 불가.")
            return []

        try:
            data = self._get("/positions", params={"user": self.wallet_address})
            positions_raw = data if isinstance(data, list) else data.get("data", data.get("positions", []))
            result = []
            for p in positions_raw:
                if isinstance(p, dict):
                    pos = self._parse_position(p)
                    if pos:
                        result.append(pos)
            return result
        except Exception as exc:
            logger.error("get_positions 실패: %s", exc)
            return []

    def get_portfolio_value(self) -> float:
        """
        포트폴리오 총 가치 (USDC) 조회.
        wallet_address가 없으면 0.0 반환.
        """
        if not self.wallet_address:
            return 0.0

        try:
            data = self._get("/value", params={"user": self.wallet_address})
            if isinstance(data, dict):
                return float(data.get("value", data.get("total", 0)) or 0)
            return float(data) if data else 0.0
        except Exception as exc:
            logger.error("get_portfolio_value 실패: %s", exc)
            return 0.0

    def get_activity(self, limit: int = 100) -> List[Dict]:
        """최근 활동 내역 (베팅, 리딤 등) 조회."""
        if not self.wallet_address:
            return []
        try:
            data = self._get(
                "/activity",
                params={"user": self.wallet_address, "limit": limit}
            )
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as exc:
            logger.error("get_activity 실패: %s", exc)
            return []

    def get_trades(self, limit: int = 100) -> List[Dict]:
        """최근 체결 거래 내역 조회."""
        if not self.wallet_address:
            return []
        try:
            data = self._get(
                "/trades",
                params={"user": self.wallet_address, "limit": limit}
            )
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as exc:
            logger.error("get_trades 실패: %s", exc)
            return []
