"""
GammaClient — Gamma Markets API 호출.
SDK 없음, requests 직접 사용.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from src.api.rate_limiter import RateLimiter
from src.shared.types import GAMMA_BASE_URL, GammaMarket, MarketToken

logger = logging.getLogger(__name__)


class GammaClient:
    """
    Gamma API (https://gamma-api.polymarket.com) 클라이언트.
    인증 불필요. rate_limiter를 통해 요청 속도를 조절합니다.
    """

    BASE_URL = GAMMA_BASE_URL

    def __init__(self, rate_limiter: RateLimiter) -> None:
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
                    logger.error("Gamma GET %s 3회 실패: %s", path, exc)
                    raise
                logger.warning("Gamma GET 실패 (시도 %d/3): %s", attempt + 1, exc)
                time.sleep(2 ** attempt)
        return []

    def _parse_market(self, raw: Dict) -> GammaMarket:
        """Gamma API 응답 dict → GammaMarket dataclass 변환."""
        # @confidence: low — Gamma API 스키마가 공식 문서에 완전히 명시되지 않음.
        outcomes: List[str] = raw.get("outcomes", ["Yes", "No"])
        if isinstance(outcomes, str):
            import json as _json
            try:
                outcomes = _json.loads(outcomes)
            except Exception:
                outcomes = ["Yes", "No"]

        outcome_prices: List[float] = []
        raw_prices = raw.get("outcomePrices", [])
        if isinstance(raw_prices, str):
            import json as _json
            try:
                raw_prices = _json.loads(raw_prices)
            except Exception:
                raw_prices = []
        for p in raw_prices:
            try:
                outcome_prices.append(float(p))
            except (TypeError, ValueError):
                outcome_prices.append(0.5)

        # 태그: [{"id": 1, "label": "Politics"}, ...] 또는 ["Politics", ...]
        raw_tags = raw.get("tags", [])
        tags: List[str] = []
        for t in raw_tags:
            if isinstance(t, dict):
                tags.append(t.get("label", t.get("name", "")))
            elif isinstance(t, str):
                tags.append(t)

        # 토큰 정보
        raw_tokens = raw.get("clobTokenIds", []) or raw.get("tokens", [])
        tokens: List[MarketToken] = []
        if isinstance(raw_tokens, list):
            for i, tok in enumerate(raw_tokens):
                if isinstance(tok, str):
                    outcome_label = outcomes[i] if i < len(outcomes) else str(i)
                    tokens.append(MarketToken(token_id=tok, outcome=outcome_label))
                elif isinstance(tok, dict):
                    tokens.append(MarketToken(
                        token_id=tok.get("token_id", tok.get("id", "")),
                        outcome=tok.get("outcome", outcomes[i] if i < len(outcomes) else str(i)),
                    ))

        return GammaMarket(
            id=int(raw.get("id", 0)),
            question=raw.get("question", ""),
            condition_id=raw.get("conditionId", raw.get("condition_id", "")),
            slug=raw.get("slug", ""),
            description=raw.get("description", ""),
            resolution_source=raw.get("resolutionSource", ""),
            end_date=raw.get("endDate", raw.get("end_date", "")),
            outcomes=outcomes,
            outcome_prices=outcome_prices,
            volume=float(raw.get("volume", 0) or 0),
            liquidity=float(raw.get("liquidity", 0) or 0),
            active=bool(raw.get("active", True)),
            closed=bool(raw.get("closed", False)),
            tags=tags,
            neg_risk=bool(raw.get("negRisk", raw.get("neg_risk", False))),
            tokens=tokens,
            event_id=str(raw.get("eventId", "")) or None,
        )

    # ----------------------------------------------------------------
    # 공개 API
    # ----------------------------------------------------------------

    def get_markets(
        self,
        active: bool = True,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0,
        tag_id: Optional[int] = None,
    ) -> List[GammaMarket]:
        """
        마켓 목록 조회.
        active=True: 진행 중인 마켓만.
        """
        params: Dict[str, Any] = {
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
        }
        if tag_id is not None:
            params["tag_id"] = tag_id

        try:
            data = self._get("/markets", params=params)
            markets_raw = data if isinstance(data, list) else data.get("data", data.get("markets", []))
            return [self._parse_market(m) for m in markets_raw if isinstance(m, dict)]
        except Exception as exc:
            logger.error("get_markets 실패: %s", exc)
            return []

    def get_market_by_id(self, market_id: int) -> Optional[GammaMarket]:
        """단일 마켓 조회 (ID)."""
        try:
            data = self._get(f"/markets/{market_id}")
            if isinstance(data, dict):
                return self._parse_market(data)
            return None
        except Exception as exc:
            logger.error("get_market_by_id(%d) 실패: %s", market_id, exc)
            return None

    def get_market_by_slug(self, slug: str) -> Optional[GammaMarket]:
        """단일 마켓 조회 (slug)."""
        try:
            data = self._get(f"/markets", params={"slug": slug})
            markets_raw = data if isinstance(data, list) else data.get("data", [data] if isinstance(data, dict) else [])
            if markets_raw:
                return self._parse_market(markets_raw[0])
            return None
        except Exception as exc:
            logger.error("get_market_by_slug(%s) 실패: %s", slug, exc)
            return None

    def get_events(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """이벤트 목록 조회."""
        try:
            data = self._get("/events", params={"limit": limit, "offset": offset})
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as exc:
            logger.error("get_events 실패: %s", exc)
            return []

    def get_tags(self) -> List[Dict]:
        """태그 목록 조회."""
        try:
            data = self._get("/tags")
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as exc:
            logger.error("get_tags 실패: %s", exc)
            return []

    def get_related_tags(self, tag_id: int) -> List[Dict]:
        """특정 태그의 관련 태그 조회."""
        try:
            data = self._get(f"/tags/{tag_id}/related-tags")
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as exc:
            logger.error("get_related_tags(%d) 실패: %s", tag_id, exc)
            return []
