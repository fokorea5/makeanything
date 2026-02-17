"""
TradingEngine — 메인 루프 + 스케줄러.
DESIGN.md 섹션 8 기반.

실행 흐름:
  initialize() → while running: collect_market_data → 전략 실행 → MetaBot → RiskManager → OrderExecutor → sleep
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from src.api.data_client import DataClient
from src.api.gamma_client import GammaClient
from src.api.polymarket_client import PolymarketClient
from src.api.rate_limiter import RateLimiter
from src.config import Config
from src.db.database import Database
from src.engine.order_executor import OrderExecutor
from src.engine.risk_manager import RiskManager
from src.shared.types import (
    EnrichedMarket,
    Position,
    Signal,
    StrategyConfig,
    STRATEGY_DEFAULT_INTERVALS,
    STRATEGY_DEFAULT_PARAMS,
)
from src.strategies.base import BaseStrategy
from src.strategies.contrarian import ContrarianStrategy
from src.strategies.correlated import CorrelatedStrategy
from src.strategies.liquidity_vacuum import LiquidityVacuumStrategy
from src.strategies.meta_bot import MetaBot
from src.strategies.oracle_fear import OracleFearStrategy
from src.strategies.resolution_arb import ResolutionArbStrategy

logger = logging.getLogger(__name__)


class Scheduler:
    """
    전략별 마지막 실행 시각 추적 → 실행 주기 관리.
    DESIGN.md 섹션 8.3 기반.
    """

    def __init__(self, intervals: Dict[str, int]) -> None:
        self.intervals = intervals
        self.last_executed: Dict[str, float] = {}

    def is_due(self, strategy_name: str) -> bool:
        """주어진 전략이 실행될 시간인지 확인."""
        now = time.time()
        last = self.last_executed.get(strategy_name, 0)
        interval = self.intervals.get(strategy_name, 60)
        return (now - last) >= interval

    def mark_executed(self, strategy_name: str) -> None:
        """전략 실행 완료 기록."""
        self.last_executed[strategy_name] = time.time()


class TradingEngine:
    """
    메인 트레이딩 엔진.

    사용법:
        engine = TradingEngine(config)
        engine.start()   # run() 호출 (Ctrl+C로 종료)
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.running = False
        self._setup_logging()

        # 컴포넌트 초기화
        self.rate_limiter = RateLimiter(config.max_requests_per_minute)
        self.db = Database(config.db_path)

        self.clob_client = PolymarketClient(
            rate_limiter=self.rate_limiter,
            private_key=config.private_key,
            api_key=config.api_key,
            api_secret=config.api_secret,
            api_passphrase=config.api_passphrase,
            dry_run=config.dry_run,
        )
        self.gamma_client = GammaClient(rate_limiter=self.rate_limiter)
        self.data_client = DataClient(
            wallet_address=config.wallet_address,
            rate_limiter=self.rate_limiter,
        )

        self.risk_manager = RiskManager(
            config=config.risk,
            db=self.db,
            dry_run=config.dry_run,
        )
        self.order_executor = OrderExecutor(
            client=self.clob_client,
            db=self.db,
            dry_run=config.dry_run,
        )
        self.meta_bot = MetaBot(config=config.meta_bot)
        self.scheduler = Scheduler(intervals=config.strategy_intervals)
        self.strategies: List[BaseStrategy] = self._build_strategies()

        # 포지션 캐시 (사이클마다 업데이트)
        self._positions: List[Position] = []

    # ----------------------------------------------------------------
    # 엔진 시작/종료
    # ----------------------------------------------------------------

    def start(self) -> None:
        """엔진 시작. Ctrl+C로 종료."""
        logger.info("=" * 60)
        logger.info("Polymarket 트레이딩 봇 시작")
        logger.info("모드: %s", "드라이런 (가상)" if self.config.dry_run else "실거래")
        logger.info("사이클 간격: %d초", self.config.cycle_interval)
        logger.info("활성 전략: %s", [s.name for s in self.strategies])
        logger.info("=" * 60)

        self.initialize()
        self.run()

    def initialize(self) -> None:
        """DB 연결, 초기 데이터 확인."""
        self.db.connect()
        logger.info("DB 초기화 완료: %s", self.config.db_path)

        if not self.config.dry_run:
            # 실거래: 자격증명 확인
            self.config.validate_for_live_trading()
            logger.info("L2 자격증명 확인 완료.")

    def stop(self) -> None:
        """엔진 정지."""
        logger.info("트레이딩 엔진 정지 요청.")
        self.running = False

    def shutdown(self) -> None:
        """자원 정리."""
        self.db.close()
        logger.info("트레이딩 엔진 종료 완료.")

    # ----------------------------------------------------------------
    # 메인 루프
    # ----------------------------------------------------------------

    def run(self) -> None:
        """무한 루프. Ctrl+C로 종료."""
        self.running = True
        logger.info("메인 루프 시작.")

        try:
            while self.running:
                cycle_start = time.time()

                try:
                    self._run_cycle()
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    logger.error("사이클 오류 (계속 실행): %s", exc, exc_info=True)

                # 다음 사이클까지 대기
                elapsed = time.time() - cycle_start
                sleep_time = max(self.config.cycle_interval - elapsed, 1.0)
                logger.debug(
                    "사이클 완료 (%.2f초). 다음 사이클까지 %.2f초 대기.",
                    elapsed, sleep_time
                )
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Ctrl+C 감지. 종료합니다.")
        finally:
            self.shutdown()

    def _run_cycle(self) -> None:
        """단일 사이클 실행."""
        # 1. 시장 데이터 수집
        markets = self.collect_market_data()
        if not markets:
            logger.warning("수집된 마켓 데이터 없음. 이번 사이클 스킵.")
            return

        logger.info("사이클 시작: %d개 마켓 분석", len(markets))

        # 2. 전략별 실행
        all_signals: List[Signal] = []
        for strategy in self.strategies:
            if not strategy.is_enabled:
                continue
            if not self.scheduler.is_due(strategy.name):
                continue

            signals = strategy.safe_analyze(markets)
            if signals:
                all_signals.extend(signals)
                # 시그널 DB 기록
                try:
                    self.db.insert_signal_logs(signals)
                except Exception as exc:
                    logger.error("시그널 로그 DB 기록 실패: %s", exc)

            self.scheduler.mark_executed(strategy.name)

        if not all_signals:
            logger.info("이번 사이클: 시그널 없음.")
            return

        logger.info("총 %d개 시그널 생성.", len(all_signals))

        # 3. 메타봇 스코어링
        decisions = self.meta_bot.evaluate(all_signals)
        if not decisions:
            logger.info("MetaBot: 실행 기준 미달. 거래 없음.")
            return

        # 4. 포지션 조회
        self._refresh_positions()

        # 5. 리스크 검사 + 주문 실행
        executed = 0
        for decision in decisions:
            risk_result = self.risk_manager.check(decision, self._positions)

            if not risk_result.approved:
                logger.info(
                    "리스크 거부: %s | 이유=%s",
                    decision.market_question[:40], risk_result.reason
                )
                continue

            decision.size = risk_result.adjusted_size
            result = self.order_executor.execute(decision)

            if result.success:
                executed += 1
            else:
                logger.warning(
                    "주문 실패: %s | %s",
                    decision.market_question[:40], result.error_message
                )

        logger.info("사이클 완료: %d개 거래 실행.", executed)

    # ----------------------------------------------------------------
    # 데이터 수집
    # ----------------------------------------------------------------

    def collect_market_data(self) -> List[EnrichedMarket]:
        """
        Gamma + CLOB 데이터를 결합하여 EnrichedMarket 리스트 반환.
        각 전략이 필요한 데이터를 공통으로 수집합니다.
        """
        enriched: List[EnrichedMarket] = []

        # Gamma 마켓 목록 (활성 마켓 상위 100개)
        try:
            gamma_markets = self.gamma_client.get_markets(active=True, closed=False, limit=100)
        except Exception as exc:
            logger.error("Gamma 마켓 수집 실패: %s", exc)
            return []

        if not gamma_markets:
            return []

        for gm in gamma_markets:
            try:
                # YES 가격 (midpoint)
                yes_token_id = ""
                for token in gm.tokens:
                    if token.outcome.lower() in ("yes", "true"):
                        yes_token_id = token.token_id
                        break
                if not yes_token_id and gm.tokens:
                    yes_token_id = gm.tokens[0].token_id

                # 미드포인트 가격 조회
                if yes_token_id:
                    yes_price = self.clob_client.get_midpoint(yes_token_id)
                elif gm.outcome_prices and len(gm.outcome_prices) >= 1:
                    yes_price = gm.outcome_prices[0]
                else:
                    yes_price = 0.5

                # 클램핑
                yes_price = max(0.01, min(0.99, yes_price))
                no_price = 1.0 - yes_price

                em = EnrichedMarket(
                    gamma=gm,
                    yes_price=yes_price,
                    no_price=no_price,
                    # order_book / price_history는 전략이 필요할 때 별도 조회
                    # (사이클당 요청 수 절약)
                )
                enriched.append(em)

            except Exception as exc:
                logger.debug("마켓 %s 보강 실패: %s", gm.condition_id[:8], exc)
                continue

        # 유동성 진공 전략: 오더북 필요 → 상위 20개 마켓만 오더북 조회
        # (API 요청 절약: 사이클당 ~20 requests)
        self._enrich_with_order_books(enriched, limit=20)

        # 군중 반대 전략: 가격 히스토리 필요 → 상위 10개만
        self._enrich_with_price_history(enriched, limit=10)

        return enriched

    def _enrich_with_order_books(
        self, markets: List[EnrichedMarket], limit: int = 20
    ) -> None:
        """상위 limit개 마켓에 오더북 추가 (유동성 기준 정렬)."""
        # 유동성 높은 마켓 우선
        sorted_markets = sorted(
            markets, key=lambda m: m.gamma.liquidity, reverse=True
        )[:limit]

        for market in sorted_markets:
            yes_token_id = ""
            for token in market.gamma.tokens:
                if token.outcome.lower() in ("yes", "true"):
                    yes_token_id = token.token_id
                    break
            if not yes_token_id:
                continue

            try:
                ob = self.clob_client.get_order_book(yes_token_id)
                if ob:
                    market.order_book = ob
            except Exception as exc:
                logger.debug(
                    "오더북 조회 실패 (token=%s): %s", yes_token_id[:8], exc
                )

    def _enrich_with_price_history(
        self, markets: List[EnrichedMarket], limit: int = 10
    ) -> None:
        """상위 limit개 마켓에 가격 히스토리 추가 (볼륨 기준)."""
        sorted_markets = sorted(
            markets, key=lambda m: m.gamma.volume, reverse=True
        )[:limit]

        for market in sorted_markets:
            yes_token_id = ""
            for token in market.gamma.tokens:
                if token.outcome.lower() in ("yes", "true"):
                    yes_token_id = token.token_id
                    break
            if not yes_token_id:
                continue

            try:
                history = self.clob_client.get_price_history(
                    yes_token_id, interval="1w", fidelity=60
                )
                if history:
                    market.price_history = history
            except Exception as exc:
                logger.debug(
                    "가격 히스토리 조회 실패 (token=%s): %s", yes_token_id[:8], exc
                )

    def _refresh_positions(self) -> None:
        """현재 포지션 캐시 갱신."""
        try:
            if self.config.dry_run:
                # 드라이런: DB 가상 포지션 사용
                raw = self.db.get_open_virtual_positions()
                self._positions = [
                    Position(
                        condition_id=r["condition_id"],
                        token_id=r["token_id"],
                        market_question=r.get("market_question", ""),
                        outcome=r.get("token_side", "Yes"),
                        size=float(r.get("size", 0)),
                        avg_price=float(r.get("entry_price", 0)),
                        current_price=float(r.get("current_price") or r.get("entry_price", 0)),
                        unrealized_pnl=float(r.get("unrealized_pnl", 0)),
                        realized_pnl=float(r.get("realized_pnl", 0)),
                    )
                    for r in raw
                ]
            else:
                self._positions = self.data_client.get_positions()
        except Exception as exc:
            logger.warning("포지션 갱신 실패: %s", exc)

    # ----------------------------------------------------------------
    # 전략 빌더
    # ----------------------------------------------------------------

    def _build_strategies(self) -> List[BaseStrategy]:
        """설정 기반 전략 인스턴스 생성."""
        intervals = self.config.strategy_intervals

        def _cfg(name: str, interval: int) -> StrategyConfig:
            return StrategyConfig(
                name=name,
                interval_seconds=intervals.get(name, interval),
                params=STRATEGY_DEFAULT_PARAMS.get(name, {}).copy(),
            )

        return [
            ResolutionArbStrategy(_cfg("resolution_arb", 300)),
            OracleFearStrategy(_cfg("oracle_fear", 300)),
            ContrarianStrategy(_cfg("contrarian", 60)),
            CorrelatedStrategy(_cfg("correlated", 120)),
            LiquidityVacuumStrategy(_cfg("liquidity_vacuum", 30)),
        ]

    # ----------------------------------------------------------------
    # 로깅 설정
    # ----------------------------------------------------------------

    def _setup_logging(self) -> None:
        """로그 포맷 설정."""
        import logging
        level = getattr(logging, self.config.log_level, logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
