"""
PolymarketClient — py-clob-client SDK 래핑.
모든 CLOB API 호출은 이 클래스를 통해 수행합니다.

# @risk: 금융거래 — place_limit_order, place_market_order, cancel_order는
#        실제 USDC를 소비/이동하는 실거래 작업입니다.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from src.api.rate_limiter import RateLimiter
from src.shared.types import (
    CLOB_HOST,
    CHAIN_ID,
    OrderBook,
    OrderBookEntry,
    OrderResult,
    OrderStatus,
    OrderType,
    Direction,
    TokenSide,
    PricePoint,
)

logger = logging.getLogger(__name__)


class PolymarketClient:
    """
    py-clob-client SDK 래핑.
    드라이런 모드: L0 (공개 조회)만 사용.
    실거래 모드: L2 (서명 + 주문) 포함.

    # @risk: 금융거래 — L2 자격증명 노출 시 자산 손실 위험.
    """

    def __init__(
        self,
        rate_limiter: RateLimiter,
        host: str = CLOB_HOST,
        chain_id: int = CHAIN_ID,
        private_key: str = "",
        api_key: str = "",
        api_secret: str = "",
        api_passphrase: str = "",
        dry_run: bool = True,
    ) -> None:
        self.rate_limiter = rate_limiter
        self.host = host
        self.chain_id = chain_id
        self.dry_run = dry_run
        self._client: Any = None

        try:
            # py-clob-client import
            from py_clob_client.client import ClobClient  # type: ignore
            from py_clob_client.clob_types import ApiCreds  # type: ignore

            if dry_run or not private_key:
                # L0 모드: 인증 불필요
                self._client = ClobClient(host=host, chain_id=chain_id)
                logger.info("PolymarketClient: L0 공개 조회 모드로 초기화 (dry_run=%s)", dry_run)
            else:
                # L2 모드: API 키 + 서명 인증
                # @risk: 금융거래 — private_key 노출 금지
                creds = ApiCreds(
                    api_key=api_key,
                    api_secret=api_secret,
                    api_passphrase=api_passphrase,
                )
                self._client = ClobClient(
                    host=host,
                    chain_id=chain_id,
                    key=private_key,
                    creds=creds,
                )
                logger.info("PolymarketClient: L2 거래 모드로 초기화")

        except ImportError:
            logger.warning(
                "py-clob-client 미설치. REST fallback 모드로 동작합니다. "
                "'pip install py-clob-client'를 실행하세요."
            )
            self._client = None

    # ----------------------------------------------------------------
    # 내부 헬퍼
    # ----------------------------------------------------------------

    def _call_with_retry(self, fn, *args, **kwargs) -> Any:
        """
        SDK 호출 + 429 재시도 래핑.
        """
        for attempt in range(3):
            self.rate_limiter.wait_if_needed()
            try:
                result = fn(*args, **kwargs)
                self.rate_limiter.record_request()
                return result
            except Exception as exc:
                msg = str(exc)
                if "429" in msg or "Too Many Requests" in msg:
                    self.rate_limiter.handle_429(attempt)
                else:
                    raise
        raise RuntimeError("SDK 호출 3회 재시도 후 실패.")

    def _rest_get(self, path: str, params: Optional[Dict] = None) -> Any:
        """직접 REST GET 호출 (SDK에 없는 엔드포인트용)."""
        url = f"{self.host}{path}"
        for attempt in range(3):
            self.rate_limiter.wait_if_needed()
            try:
                resp = requests.get(url, params=params, timeout=15)
                self.rate_limiter.record_request()
                if resp.status_code == 429:
                    self.rate_limiter.handle_429(attempt)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                if attempt == 2:
                    raise
                logger.warning("REST GET 실패 (시도 %d/3): %s", attempt + 1, exc)
                time.sleep(1)
        raise RuntimeError(f"REST GET {path} 3회 실패.")

    # ----------------------------------------------------------------
    # 공개 데이터 (L0)
    # ----------------------------------------------------------------

    def get_markets(self) -> List[Dict]:
        """
        공개 마켓 목록 조회.
        SDK get_simplified_markets() 또는 REST fallback.
        """
        if self._client is not None:
            try:
                result = self._call_with_retry(self._client.get_simplified_markets)
                if isinstance(result, list):
                    return result
                # 일부 버전: {"data": [...], "next_cursor": "..."}
                if isinstance(result, dict) and "data" in result:
                    return result["data"]
                return []
            except Exception as exc:
                logger.error("get_markets SDK 실패: %s", exc)
                return []
        # fallback
        try:
            data = self._rest_get("/markets")
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as exc:
            logger.error("get_markets REST 실패: %s", exc)
            return []

    def get_order_book(self, token_id: str) -> Optional[OrderBook]:
        """
        오더북 조회. SDK 호출 후 OrderBook 타입으로 변환.
        """
        if self._client is not None:
            try:
                raw = self._call_with_retry(self._client.get_order_book, token_id)
                return self._parse_order_book(token_id, raw)
            except Exception as exc:
                logger.error("get_order_book 실패 (token=%s): %s", token_id[:8], exc)
                return None
        return None

    def _parse_order_book(self, token_id: str, raw: Any) -> OrderBook:
        """SDK 오더북 응답 → OrderBook dataclass 변환."""
        # @confidence: low — SDK 응답 형식이 버전별로 다를 수 있음.
        bids: List[OrderBookEntry] = []
        asks: List[OrderBookEntry] = []

        if raw is None:
            return OrderBook(token_id=token_id, bids=[], asks=[])

        # SDK OrderSummary 객체 또는 dict 처리
        raw_bids = getattr(raw, "bids", None) or (raw.get("bids", []) if isinstance(raw, dict) else [])
        raw_asks = getattr(raw, "asks", None) or (raw.get("asks", []) if isinstance(raw, dict) else [])

        for b in raw_bids:
            try:
                p = float(getattr(b, "price", b.get("price", 0)))
                s = float(getattr(b, "size", b.get("size", 0)))
                bids.append(OrderBookEntry(price=p, size=s))
            except (TypeError, ValueError, AttributeError):
                continue

        for a in raw_asks:
            try:
                p = float(getattr(a, "price", a.get("price", 0)))
                s = float(getattr(a, "size", a.get("size", 0)))
                asks.append(OrderBookEntry(price=p, size=s))
            except (TypeError, ValueError, AttributeError):
                continue

        # bids 내림차순, asks 오름차순 정렬
        bids.sort(key=lambda x: x.price, reverse=True)
        asks.sort(key=lambda x: x.price)

        return OrderBook(token_id=token_id, bids=bids, asks=asks)

    def get_midpoint(self, token_id: str) -> float:
        """
        미드포인트 가격 조회. 실패 시 0.5 반환.
        """
        if self._client is not None:
            try:
                result = self._call_with_retry(self._client.get_midpoint, token_id)
                # 응답 형식: {"mid": "0.55"} 또는 float
                if isinstance(result, dict):
                    return float(result.get("mid", 0.5))
                return float(result)
            except Exception as exc:
                logger.debug("get_midpoint 실패 (token=%s): %s", token_id[:8], exc)

        # fallback: 오더북에서 직접 계산
        ob = self.get_order_book(token_id)
        if ob and ob.bids and ob.asks:
            return (ob.best_bid + ob.best_ask) / 2.0
        return 0.5

    def get_spread(self, token_id: str) -> float:
        """
        스프레드 조회. SDK 실패 시 오더북에서 직접 계산.
        """
        if self._client is not None:
            try:
                result = self._call_with_retry(self._client.get_spread, token_id)
                if isinstance(result, dict):
                    return float(result.get("spread", 0.0))
                return float(result)
            except Exception:
                pass

        ob = self.get_order_book(token_id)
        if ob:
            return ob.spread
        return 0.0

    def get_last_trade_price(self, token_id: str) -> float:
        """
        최근 체결가 조회.
        """
        if self._client is not None:
            try:
                result = self._call_with_retry(self._client.get_last_trade_price, token_id)
                if isinstance(result, dict):
                    return float(result.get("price", 0.5))
                return float(result)
            except Exception as exc:
                logger.debug("get_last_trade_price 실패 (token=%s): %s", token_id[:8], exc)
        return self.get_midpoint(token_id)

    def get_price_history(
        self, token_id: str, interval: str = "1w", fidelity: int = 60
    ) -> List[PricePoint]:
        """
        가격 히스토리 조회. CLOB REST /prices-history 직접 호출.
        interval: "1d", "1w", "1m" 등.
        fidelity: 분 단위 해상도 (기본 60분).
        """
        try:
            data = self._rest_get(
                "/prices-history",
                params={"market": token_id, "interval": interval, "fidelity": fidelity},
            )
            points: List[PricePoint] = []
            history = data if isinstance(data, list) else data.get("history", [])
            for item in history:
                if isinstance(item, dict):
                    ts = int(item.get("t", 0))
                    p = float(item.get("p", 0.0))
                    points.append(PricePoint(timestamp=ts, price=p))
            return points
        except Exception as exc:
            logger.error("get_price_history 실패 (token=%s): %s", token_id[:8], exc)
            return []

    # ----------------------------------------------------------------
    # 거래 (L2) — @risk: 금융거래
    # ----------------------------------------------------------------

    def place_limit_order(
        self,
        token_id: str,
        side: Direction,
        price: float,
        size: float,
        order_type: OrderType = OrderType.GTC,
    ) -> OrderResult:
        """
        리밋 오더 실행.
        # @risk: 금융거래 — 실제 USDC 소비.
        """
        if self._client is None:
            return self._failed_result(token_id, side, price, size, "SDK 미초기화")

        try:
            from py_clob_client.clob_types import OrderArgs, OrderType as SDKOrderType  # type: ignore

            # 주문 방향: BUY=0, SELL=1 (SDK 규칙)
            sdk_side = 0 if side == Direction.BUY else 1

            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=sdk_side,
            )
            signed_order = self._call_with_retry(
                self._client.create_order, order_args
            )
            resp = self._call_with_retry(
                self._client.post_order, signed_order, SDKOrderType.GTC
            )

            order_id = resp.get("orderID", "") if isinstance(resp, dict) else str(resp)
            status_str = resp.get("status", "PENDING") if isinstance(resp, dict) else "PENDING"
            status = OrderStatus.PENDING

            return OrderResult(
                success=True,
                order_id=order_id,
                condition_id="",
                token_id=token_id,
                direction=side,
                token_side=TokenSide.YES,
                price=price,
                size=size,
                order_type=order_type,
                status=status,
                composite_score=0.0,
                contributing_strategies=[],
                dry_run=False,
            )

        except Exception as exc:
            logger.error("place_limit_order 실패: %s", exc)
            return self._failed_result(token_id, side, price, size, str(exc))

    def place_market_order(self, token_id: str, amount: float) -> OrderResult:
        """
        시장가 주문 (FOK).
        # @risk: 금융거래 — 즉시 체결. 슬리피지 가능.
        """
        if self._client is None:
            return self._failed_result(token_id, Direction.BUY, 0.0, amount, "SDK 미초기화")

        try:
            from py_clob_client.clob_types import MarketOrderArgs, OrderType as SDKOrderType  # type: ignore

            order_args = MarketOrderArgs(token_id=token_id, amount=amount)
            signed_order = self._call_with_retry(self._client.create_market_order, order_args)
            resp = self._call_with_retry(
                self._client.post_order, signed_order, SDKOrderType.FOK
            )

            order_id = resp.get("orderID", "") if isinstance(resp, dict) else str(resp)

            return OrderResult(
                success=True,
                order_id=order_id,
                condition_id="",
                token_id=token_id,
                direction=Direction.BUY,
                token_side=TokenSide.YES,
                price=0.0,
                size=amount,
                order_type=OrderType.FOK,
                status=OrderStatus.PENDING,
                composite_score=0.0,
                contributing_strategies=[],
                dry_run=False,
            )

        except Exception as exc:
            logger.error("place_market_order 실패: %s", exc)
            return self._failed_result(token_id, Direction.BUY, 0.0, amount, str(exc))

    def cancel_order(self, order_id: str) -> bool:
        """
        단일 주문 취소.
        # @risk: 금융거래 — 주문 취소 실패 시 오픈 포지션 유지.
        """
        if self._client is None:
            return False
        try:
            self._call_with_retry(self._client.cancel, order_id)
            logger.info("주문 취소 성공: %s", order_id)
            return True
        except Exception as exc:
            logger.error("cancel_order 실패 (order=%s): %s", order_id, exc)
            return False

    def cancel_all_orders(self) -> bool:
        """
        모든 오픈 주문 취소.
        # @risk: 금융거래 — 의도치 않은 전체 취소 위험.
        """
        if self._client is None:
            return False
        try:
            self._call_with_retry(self._client.cancel_all)
            logger.info("모든 주문 취소 완료.")
            return True
        except Exception as exc:
            logger.error("cancel_all_orders 실패: %s", exc)
            return False

    def get_open_orders(self, market: Optional[str] = None) -> List[Dict]:
        """
        오픈 주문 목록 조회.
        """
        if self._client is None:
            return []
        try:
            if market:
                result = self._call_with_retry(self._client.get_orders, market=market)
            else:
                result = self._call_with_retry(self._client.get_orders)
            if isinstance(result, list):
                return result
            return result.get("data", []) if isinstance(result, dict) else []
        except Exception as exc:
            logger.error("get_open_orders 실패: %s", exc)
            return []

    # ----------------------------------------------------------------
    # 헬퍼
    # ----------------------------------------------------------------

    def _failed_result(
        self, token_id: str, side: Direction, price: float, size: float, msg: str
    ) -> OrderResult:
        return OrderResult(
            success=False,
            order_id="",
            condition_id="",
            token_id=token_id,
            direction=side,
            token_side=TokenSide.YES,
            price=price,
            size=size,
            order_type=OrderType.GTC,
            status=OrderStatus.FAILED,
            composite_score=0.0,
            contributing_strategies=[],
            dry_run=self.dry_run,
            error_message=msg,
        )
