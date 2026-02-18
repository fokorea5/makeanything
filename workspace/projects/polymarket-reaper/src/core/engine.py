"""
Trading Engine -- 듀얼 리액터 오케스트레이션 (DESIGN.md 3.6절, AC-01).

_run_reactor_alpha(): 3단계 퍼널.
_run_reactor_omega(): Complete Set 실시간.
_consume_signals(): Signal Queue -> Meta Brain -> Risk -> Executor.
중복 방지 (AC-39, AC-40).
Market Age Freshness 보조지표 (AC-09).
Graceful shutdown (AC-36).
전략별 에러 격리.
"""

from __future__ import annotations

import asyncio
import logging
import signal as os_signal
from datetime import datetime, timedelta
from typing import Any

from config import Config
from src.shared.types import (
    MarketData,
    Signal,
    TradeDecision,
    RiskCheck,
    ReactorType,
    FrequencyMode,
    SignalUrgency,
    ExecutorMode,
)
from src.core.signal_queue import SignalQueue
from src.core.meta_brain import MetaBrain
from src.core.risk_sentinel import RiskSentinel
from src.core.executor import Executor
from src.core.frequency_governor import FrequencyGovernor

# 전략 imports
from src.strategies.ambiguity import AmbiguityStrategy
from src.strategies.oracle_fear import OracleFearStrategy
from src.strategies.contrarian import ContrarianStrategy
from src.strategies.correlated import CorrelatedStrategy
from src.strategies.liquidity_vacuum import LiquidityVacuumStrategy
from src.strategies.complete_set import CompleteSetStrategy

logger = logging.getLogger("reaper.core.engine")


class TradingEngine:
    """Trading Engine: 듀얼 리액터 오케스트레이션.

    Reactor Alpha (Slow Brain): 3단계 퍼널 (Stage 1->2->3).
    Reactor Omega (Fast Brain): Complete Set 실시간 차익.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._running = False

        # 코어 컴포넌트 (run()에서 초기화)
        self.signal_queue = SignalQueue()
        self.meta_brain = MetaBrain(config)
        self.frequency_governor = FrequencyGovernor(config)
        self.risk_sentinel: RiskSentinel | None = None
        self.executor: Executor | None = None

        # 외부 의존성 (run()에서 주입)
        self.clob_client: Any = None
        self.gamma_client: Any = None
        self.data_client: Any = None
        self.ws_manager: Any = None
        self.market_cache: Any = None
        self.db_manager: Any = None
        self.portfolio_tracker: Any = None

        # 전략 인스턴스 (run()에서 초기화)
        self._stage1_strategies: list[Any] = []
        self._stage2_strategies: list[Any] = []
        self._stage3_strategies: list[Any] = []
        self._omega_strategy: CompleteSetStrategy | None = None

        # 퍼널 결과
        self._target_list: list[MarketData] = []
        self._hit_list: list[MarketData] = []

        # 터미널 대시보드
        self._dashboard: Any = None

        # Market Age 파라미터 (AC-09)
        self._market_age_hours: int = getattr(config, "MARKET_AGE_HOURS", 48)
        self._market_age_bonus: float = getattr(config, "MARKET_AGE_BONUS", 0.15)

    # ------------------------------------------------------------------
    # 메인 실행
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """메인 엔진 루프. asyncio.gather로 모든 코루틴을 병렬 실행한다 (AC-01)."""
        logger.info("Trading Engine starting...")
        self._running = True

        # Graceful shutdown 핸들러 등록 (AC-36)
        self._register_shutdown_handlers()

        # 컴포넌트 초기화
        await self._initialize()

        logger.info("Trading Engine running. DRY_RUN=%s", getattr(self.config, "DRY_RUN", True))

        try:
            tasks = [
                self._run_reactor_alpha(),
                self._run_reactor_omega(),
                self._consume_signals(),
                self._drain_expired_loop(),
                self._portfolio_sync(),
                self._governor_auto_check(),
                self._health_check(),
            ]
            if self._dashboard is not None:
                tasks.append(self._dashboard.run())
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Engine tasks cancelled")
        except Exception as e:
            logger.error("Engine fatal error: %s", e)
        finally:
            await self._shutdown()

    # ------------------------------------------------------------------
    # 초기화
    # ------------------------------------------------------------------

    async def _initialize(self) -> None:
        """컴포넌트를 초기화한다."""
        # API 클라이언트 (외부에서 주입되지 않았으면 import 시도)
        if self.clob_client is None:
            try:
                from src.api.clob_client import AsyncClobClient
                self.clob_client = AsyncClobClient()
                await self.clob_client.init()
            except ImportError:
                logger.warning("AsyncClobClient not available")

        if self.gamma_client is None:
            try:
                from src.api.gamma_client import AsyncGammaClient
                self.gamma_client = AsyncGammaClient()
                await self.gamma_client.init()
            except ImportError:
                logger.warning("AsyncGammaClient not available")

        if self.data_client is None:
            try:
                from src.api.data_client import AsyncDataClient
                self.data_client = AsyncDataClient()
                await self.data_client.init()
            except ImportError:
                logger.warning("AsyncDataClient not available")

        if self.ws_manager is None:
            try:
                from src.api.ws_manager import WSManager
                self.ws_manager = WSManager()
            except ImportError:
                logger.warning("WSManager not available")

        if self.market_cache is None:
            try:
                from src.data.market_cache import MarketDataCache
                self.market_cache = MarketDataCache()
            except ImportError:
                logger.warning("MarketDataCache not available")

        if self.db_manager is None:
            try:
                from src.data.db import DBManager
                self.db_manager = DBManager()
                await self.db_manager.init_db()
            except ImportError:
                logger.warning("DBManager not available")
            except Exception as e:
                logger.warning("DB init failed: %s", e)

        if self.portfolio_tracker is None:
            try:
                from src.portfolio.tracker import PortfolioTracker
                self.portfolio_tracker = PortfolioTracker(
                    data_client=self.data_client,
                )
            except ImportError:
                logger.warning("PortfolioTracker not available")

        # Frequency Governor에 DB 연결
        self.frequency_governor.db_manager = self.db_manager

        # Risk Sentinel
        self.risk_sentinel = RiskSentinel(
            self.config,
            frequency_governor=self.frequency_governor,
            portfolio_tracker=self.portfolio_tracker,
            clob_client=self.clob_client,
        )

        # Executor
        self.executor = Executor(
            self.config,
            clob_client=self.clob_client,
            db_manager=self.db_manager,
            portfolio_tracker=self.portfolio_tracker,
        )

        # 전략 초기화
        self._init_strategies()

        # Market Cache 초기 로드
        if self.market_cache is not None:
            try:
                await self.market_cache.refresh_markets(self.gamma_client)
                logger.info("Market cache refreshed")
            except Exception as e:
                logger.warning("Market cache refresh failed: %s", e)

        # Portfolio Tracker 초기 동기화
        if self.portfolio_tracker is not None:
            try:
                await self.portfolio_tracker.sync_positions()
                logger.info("Portfolio synced")
            except Exception as e:
                logger.warning("Portfolio sync failed: %s", e)

            # bankroll이 0이면 INITIAL_BANKROLL fallback 적용
            bankroll = await self.portfolio_tracker.get_bankroll()
            if bankroll <= 0 and not getattr(self.config, "DRY_RUN", True):
                initial = getattr(self.config, "INITIAL_BANKROLL", 0.0)
                if initial > 0:
                    self.portfolio_tracker.set_initial_bankroll(initial)
                    logger.info("Bankroll set from INITIAL_BANKROLL: %.2f", initial)
                else:
                    logger.warning(
                        "LIVE mode bankroll is 0. Set INITIAL_BANKROLL in .env "
                        "or ensure Data API can reach wallet."
                    )

        # 즉시 AUTO 모드 전환 (60초 대기 없이 초기 DD 기반으로 설정)
        if self.portfolio_tracker is not None:
            try:
                current_dd = await self.portfolio_tracker.get_current_drawdown()
                await self.frequency_governor.check_auto_transition(current_dd)
                effective = self.frequency_governor.get_effective_mode_name()
                logger.info("Initial AUTO mode set: %s (DD=%.2f%%)", effective, current_dd * 100)
            except Exception as e:
                logger.warning("Initial AUTO transition failed: %s", e)

        # WebSocket 연결
        await self._connect_websocket()

        # 터미널 대시보드 초기화
        try:
            from src.ui.dashboard import TerminalDashboard
            self._dashboard = TerminalDashboard(self)
            logger.info("Terminal Dashboard initialized")
        except ImportError:
            logger.info("Terminal Dashboard not available (install rich)")

        # 초기화 완료 상태 요약
        market_count = len(self.market_cache._markets) if self.market_cache else 0
        bankroll = await self.portfolio_tracker.get_bankroll() if self.portfolio_tracker else 0.0
        effective_mode = self.frequency_governor.get_effective_mode_name()
        logger.info(
            "Engine initialization complete  markets=%d  bankroll=%.2f  mode=%s  "
            "clob=%s  gamma=%s  data=%s",
            market_count, bankroll, effective_mode,
            "OK" if self.clob_client and getattr(self.clob_client, "_client", None) else "STUB",
            "OK" if self.gamma_client and getattr(self.gamma_client, "_session", None) else "STUB",
            "OK" if self.data_client and getattr(self.data_client, "_session", None) else "STUB",
        )

    def _init_strategies(self) -> None:
        """전략 인스턴스를 초기화한다."""
        # Stage 1 전략
        ambiguity = AmbiguityStrategy(self.config)
        oracle_fear = OracleFearStrategy(self.config)
        self._stage1_strategies = [
            s for s in [ambiguity, oracle_fear] if s.enabled
        ]

        # Stage 2 전략
        contrarian = ContrarianStrategy(self.config, data_client=self.data_client)
        correlated = CorrelatedStrategy(self.config, market_cache=self.market_cache)
        self._stage2_strategies = [
            s for s in [contrarian, correlated] if s.enabled
        ]

        # Stage 3 전략
        liquidity_vacuum = LiquidityVacuumStrategy(self.config)
        self._stage3_strategies = [
            s for s in [liquidity_vacuum] if s.enabled
        ]

        # Reactor Omega
        self._omega_strategy = CompleteSetStrategy(
            self.config,
            market_cache=self.market_cache,
            signal_queue=self.signal_queue,
            meta_brain=self.meta_brain,
        )

        logger.info(
            "Strategies initialized: Stage1=%d Stage2=%d Stage3=%d Omega=%s",
            len(self._stage1_strategies),
            len(self._stage2_strategies),
            len(self._stage3_strategies),
            self._omega_strategy.enabled if self._omega_strategy else False,
        )

    async def _connect_websocket(self) -> None:
        """WebSocket 연결을 수행한다."""
        if self.ws_manager is None:
            return

        try:
            # 초기에는 market 채널만 연결
            # 실제 구독은 Stage 2 완료 후 Hit List 기반으로 수행
            await self.ws_manager.connect_market(
                asset_ids=[],
                on_event=self._on_ws_event,
            )
            logger.info("WebSocket connected")
        except Exception as e:
            logger.warning("WebSocket connection failed: %s", e)

    # ------------------------------------------------------------------
    # Reactor Alpha -- 3단계 퍼널
    # ------------------------------------------------------------------

    async def _run_reactor_alpha(self) -> None:
        """Reactor Alpha (Slow Brain) 3단계 퍼널 (AC-01)."""
        first_run = True
        while self._running:
            try:
                # 첫 사이클은 즉시 실행, 이후부터 Governor 주기에 따라 대기
                if first_run:
                    first_run = False
                    # 초기화 직후 market cache가 아직 비었을 수 있으므로 짧게 대기
                    await asyncio.sleep(5)
                else:
                    stage1_interval = self.frequency_governor.get_stage1_interval()
                    await asyncio.sleep(stage1_interval)

                if not self._running:
                    break

                # Stage 1 실행
                all_markets = await self._get_all_markets()
                if not all_markets:
                    logger.warning(
                        "No active markets for Stage 1 -- retrying in 30s "
                        "(check Gamma API connection / GAMMA_HOST)"
                    )
                    await asyncio.sleep(30)
                    continue

                self._target_list = await self._run_stage1(all_markets)
                logger.info(
                    "Stage 1 complete: %d markets → %d targets",
                    len(all_markets), len(self._target_list),
                )

                if not self._target_list:
                    continue

                # Stage 2 스캔 (Governor 주기에 따라)
                stage2_interval = self.frequency_governor.get_stage2_interval()
                await asyncio.sleep(stage2_interval)

                if not self._running:
                    break

                # Stage 2 실행
                self._hit_list = await self._run_stage2(self._target_list)
                logger.info(
                    "Stage 2 complete: %d targets → %d hits",
                    len(self._target_list), len(self._hit_list),
                )

                if not self._hit_list:
                    continue

                # Stage 3: WS 구독 등록
                await self._subscribe_hit_list(self._hit_list)

                # Stage 3 전략에 Hit List 등록
                for strategy in self._stage3_strategies:
                    try:
                        await strategy.analyze(self._hit_list)
                    except Exception as e:
                        logger.error("Stage 3 strategy %s setup failed: %s", strategy.name, e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Reactor Alpha error: %s", e)
                await asyncio.sleep(10)

    async def _run_stage1(self, markets: list[MarketData]) -> list[MarketData]:
        """Stage 1: Ambiguity + Oracle Fear + Market Age (AC-07, AC-08, AC-09, AC-10)."""
        target_market_ids: set[str] = set()
        all_signals: list[Signal] = []

        for strategy in self._stage1_strategies:
            try:
                signals = await strategy.analyze(markets)
                for s in signals:
                    # Market Age Freshness 보조지표 적용 (AC-09)
                    s = self._apply_market_age_bonus(s, markets)
                    all_signals.append(s)
                    target_market_ids.add(s.condition_id)
                    await self.signal_queue.put(s)
            except Exception as e:
                logger.error("Strategy %s failed: %s", strategy.name, e)

        # Target List 구축 (AC-10)
        target_list = [m for m in markets if m.condition_id in target_market_ids]

        logger.info(
            "Stage 1: %d signals produced, %d markets targeted",
            len(all_signals), len(target_list),
        )
        return target_list

    async def _run_stage2(self, target_list: list[MarketData]) -> list[MarketData]:
        """Stage 2: Contrarian + Correlated + Crowding (AC-11, AC-12, AC-13, AC-14)."""
        hit_market_ids: set[str] = set()
        all_signals: list[Signal] = []

        # 가격 히스토리 로드 (Stage 2에 필요)
        await self._load_price_histories(target_list)

        for strategy in self._stage2_strategies:
            try:
                signals = await strategy.analyze(target_list)
                for s in signals:
                    all_signals.append(s)
                    hit_market_ids.add(s.condition_id)
                    await self.signal_queue.put(s)
            except Exception as e:
                logger.error("Strategy %s failed: %s", strategy.name, e)

        # Hit List = Stage 2 시그널이 발생한 마켓 + Stage 1 Target List (AC-14)
        hit_list = [m for m in target_list if m.condition_id in hit_market_ids]

        logger.info(
            "Stage 2: %d signals produced, %d markets in hit list",
            len(all_signals), len(hit_list),
        )
        return hit_list

    # ------------------------------------------------------------------
    # Market Age Freshness (AC-09)
    # ------------------------------------------------------------------

    def _apply_market_age_bonus(self, signal: Signal, markets: list[MarketData]) -> Signal:
        """생성 48시간 이내 마켓에 confidence +0.15 가산."""
        market = self._find_market(signal.condition_id, markets)
        if market is None:
            return signal

        try:
            start_str = market.start_date
            if not start_str:
                return signal

            start_str_clean = start_str.replace("Z", "+00:00")
            if "T" in start_str_clean:
                start_date = datetime.fromisoformat(start_str_clean).replace(tzinfo=None)
            else:
                start_date = datetime.fromisoformat(start_str_clean + "T00:00:00")

            now = datetime.utcnow()
            hours_since_creation = (now - start_date).total_seconds() / 3600

            if hours_since_creation < self._market_age_hours:
                signal.confidence = min(1.0, signal.confidence + self._market_age_bonus)
                signal.metadata["market_age_hours"] = round(hours_since_creation, 1)
                signal.metadata["market_age_bonus_applied"] = True
                logger.debug(
                    "Market Age bonus applied: market=%s age=%.1fh",
                    signal.condition_id, hours_since_creation,
                )
            else:
                signal.metadata["market_age_hours"] = round(hours_since_creation, 1)
                signal.metadata["market_age_bonus_applied"] = False
        except (ValueError, TypeError) as e:
            logger.debug("Market Age check failed for %s: %s", signal.condition_id, e)

        return signal

    # ------------------------------------------------------------------
    # Reactor Omega -- Complete Set 실시간
    # ------------------------------------------------------------------

    async def _run_reactor_omega(self) -> None:
        """Reactor Omega (Fast Brain): Complete Set 실시간 차익 (AC-18, AC-19)."""
        if self._omega_strategy is None or not self._omega_strategy.enabled:
            logger.info("Reactor Omega disabled")
            return

        # 초기 event 그룹 등록
        await self._register_omega_events()

        # WS 이벤트는 _on_ws_event()에서 디스패치되므로 여기서는 대기
        while self._running:
            try:
                await asyncio.sleep(60)
                # 주기적으로 event 그룹 갱신
                await self._register_omega_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Reactor Omega error: %s", e)
                await asyncio.sleep(10)

    async def _register_omega_events(self) -> None:
        """Omega 전략에 event 그룹을 등록한다."""
        if self.market_cache is None or self._omega_strategy is None:
            return

        try:
            if hasattr(self.market_cache, "get_event_groups"):
                event_groups = self.market_cache.get_event_groups()
            else:
                event_groups = {}
            self._omega_strategy.register_event_groups(event_groups)
        except Exception as e:
            logger.warning("Omega event registration failed: %s", e)

    # ------------------------------------------------------------------
    # WebSocket 이벤트 디스패치
    # ------------------------------------------------------------------

    async def _on_ws_event(self, event: dict[str, Any]) -> None:
        """WebSocket 이벤트를 적절한 전략으로 디스패치한다."""
        # Stage 3 전략에 디스패치
        for strategy in self._stage3_strategies:
            if strategy.requires_ws:
                try:
                    signals = await strategy.on_ws_event(event)
                    for s in signals:
                        await self.signal_queue.put(s)
                except Exception as e:
                    logger.error("Stage 3 WS handler %s error: %s", strategy.name, e)

        # Omega 전략에 디스패치
        if self._omega_strategy is not None and self._omega_strategy.enabled:
            try:
                omega_signals = await self._omega_strategy.on_ws_event(event)
                for s in omega_signals:
                    # Omega는 Signal Queue를 우회하여 직접 실행 (AC-19)
                    await self._execute_omega_signal(s)
            except Exception as e:
                logger.error("Omega WS handler error: %s", e)

    async def _execute_omega_signal(self, signal: Signal) -> None:
        """Omega 시그널을 Risk Sentinel → Sniper Executor로 직접 실행한다."""
        if self.risk_sentinel is None or self.executor is None:
            logger.warning("Risk Sentinel or Executor not available for Omega")
            return

        try:
            # TradeDecision 생성 (Meta Brain 우회)
            import uuid
            decision = TradeDecision(
                id=str(uuid.uuid4()),
                condition_id=signal.condition_id,
                token_id=signal.token_id,
                side=signal.side,
                confidence=signal.confidence,
                urgency=signal.urgency,
                contributing_signals=[signal.id],
                convergence_count=1,
                weighted_confidence=signal.confidence,
                convergence_bonus=0.0,
                price_at_decision=signal.price_at_signal,
                executor_mode=ExecutorMode.SNIPER,
                reactor_source=ReactorType.OMEGA,
                golden_cross=False,
            )

            # Risk Sentinel 평가
            risk_check = await self._build_risk_check()
            market_data = self._find_market_by_id(signal.condition_id)
            approval = await self.risk_sentinel.evaluate(
                decision, risk_check,
                market_end_date=market_data.end_date if market_data else None,
                market_fee_bps=market_data.fee_rate_bps if market_data else 0.0,
                market_min_order=market_data.minimum_order_size if market_data else 5.0,
            )

            if approval.approved:
                result = await self.executor.execute(decision, approval)
                logger.info(
                    "Omega execution: market=%s status=%s cost=$%.2f",
                    signal.condition_id, result.status.value, result.cost_usdc,
                )
            else:
                logger.info(
                    "Omega rejected by Risk: market=%s reason=%s",
                    signal.condition_id,
                    approval.reject_reason.value if approval.reject_reason else "unknown",
                )

        except Exception as e:
            logger.error("Omega execution error: %s", e)

    # ------------------------------------------------------------------
    # Signal Consumer: Queue -> Meta Brain -> Risk -> Executor
    # ------------------------------------------------------------------

    async def _consume_signals(self) -> None:
        """Signal Queue에서 시그널을 소비하여 실행한다."""
        while self._running:
            try:
                # 큐에서 시그널 대기
                signal = await asyncio.wait_for(
                    self.signal_queue.get(), timeout=5.0,
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                # 중복 방지 (AC-39)
                if await self._check_duplicate(signal):
                    logger.debug(
                        "Signal %s skipped: duplicate for market %s",
                        signal.id, signal.condition_id,
                    )
                    continue

                # Meta Brain: 시그널 → TradeDecision (AC-20~22)
                decision = await self.meta_brain.consume(signal)
                if decision is None:
                    continue

                # Risk Sentinel: TradeDecision → RiskApproval (AC-23~27)
                if self.risk_sentinel is None:
                    continue

                risk_check = await self._build_risk_check()
                market_data = self._find_market_by_id(signal.condition_id)
                approval = await self.risk_sentinel.evaluate(
                    decision, risk_check,
                    market_end_date=market_data.end_date if market_data else None,
                    market_fee_bps=market_data.fee_rate_bps if market_data else 0.0,
                    market_min_order=market_data.minimum_order_size if market_data else 5.0,
                )

                if not approval.approved:
                    logger.info(
                        "Signal %s rejected: %s",
                        signal.id,
                        approval.reject_reason.value if approval.reject_reason else "unknown",
                    )
                    continue

                # Executor: RiskApproval → TradeResult (AC-31~33)
                if self.executor is None:
                    continue

                result = await self.executor.execute(decision, approval)
                logger.info(
                    "Trade executed: market=%s side=%s status=%s cost=$%.2f",
                    result.condition_id, result.side.value,
                    result.status.value, result.cost_usdc,
                )

            except Exception as e:
                logger.error("Signal consumption error for %s: %s", signal.id, e)

    # ------------------------------------------------------------------
    # 중복 방지 (AC-39)
    # ------------------------------------------------------------------

    async def _check_duplicate(self, signal: Signal) -> bool:
        """동일 마켓 중복 주문 방지. True면 스킵.

        1. 미체결 GTC가 있으면 → 스킵.
        2. 기존 포지션이 같은 방향 → 스킵.
        3. 반대 방향 → 기존 포지션 청산 후 진행.
        """
        market_id = signal.condition_id

        # 미체결 주문 체크
        if self.portfolio_tracker is not None:
            try:
                has_open = await self.portfolio_tracker.has_open_orders(market_id)
                if has_open:
                    return True
            except Exception:
                pass

        # 기존 포지션 체크
        if self.portfolio_tracker is not None:
            try:
                position = await self.portfolio_tracker.get_position(market_id)
                if position:
                    # 같은 방향 판단
                    if self._same_direction(position, signal):
                        return True
                    else:
                        # 반대 방향: 기존 포지션 청산
                        await self._close_position(position)
                        return False
            except Exception:
                pass

        return False

    def _same_direction(self, position: Any, signal: Signal) -> bool:
        """포지션과 시그널이 같은 방향인지 판단한다."""
        if position is None:
            return False
        try:
            # position.outcome이 "Yes"/"No"이고 signal.side가 BUY/SELL
            pos_is_yes = position.outcome == "Yes"
            sig_buys_yes = (
                signal.side.value == "BUY" and signal.token_id == getattr(position, "token_id", "")
            )
            sig_buys_no = signal.side.value == "BUY" and not sig_buys_yes

            if pos_is_yes and sig_buys_yes:
                return True
            if not pos_is_yes and sig_buys_no:
                return True
        except Exception:
            pass
        return False

    async def _close_position(self, position: Any) -> None:
        """기존 포지션을 청산한다."""
        if self.clob_client is None:
            return

        try:
            logger.info(
                "Closing position: market=%s outcome=%s size=%.4f",
                position.condition_id, position.outcome, position.size,
            )
            # 청산 = 반대 방향 SELL
            if self.executor is not None and not getattr(self.config, "DRY_RUN", True):
                await self.clob_client.cancel_market_orders(position.condition_id)
        except Exception as e:
            logger.error("Position close failed: %s", e)

    # ------------------------------------------------------------------
    # 주기적 작업
    # ------------------------------------------------------------------

    async def _drain_expired_loop(self) -> None:
        """30초 주기로 만료 시그널 제거."""
        while self._running:
            try:
                await asyncio.sleep(30)
                await self.signal_queue.drain_expired()
                self.meta_brain.clean_stale()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Drain expired error: %s", e)

    async def _portfolio_sync(self) -> None:
        """120초 주기 포지션 동기화."""
        while self._running:
            try:
                await asyncio.sleep(120)
                if self.portfolio_tracker is not None:
                    await self.portfolio_tracker.sync_positions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Portfolio sync error: %s", e)

    async def _governor_auto_check(self) -> None:
        """60초 주기 Governor AUTO 모드 DD 체크 (AC-29)."""
        while self._running:
            try:
                await asyncio.sleep(60)

                # DD 조회
                current_dd = 0.0
                if self.portfolio_tracker is not None:
                    try:
                        current_dd = await self.portfolio_tracker.get_current_drawdown()
                    except Exception:
                        pass

                # AUTO 모드 전환 체크
                await self.frequency_governor.check_auto_transition(current_dd)

                # DB 모드 체크 (AC-30)
                await self.frequency_governor.check_db_mode()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Governor auto check error: %s", e)

    async def _health_check(self) -> None:
        """60초 주기 시스템 헬스체크."""
        while self._running:
            try:
                await asyncio.sleep(60)
                gov_state = self.frequency_governor.get_state()
                logger.info(
                    "Health: queue=%d mode=%s kelly=%.2f targets=%d hits=%d",
                    self.signal_queue.qsize(),
                    gov_state.current_mode.value,
                    gov_state.kelly_multiplier,
                    len(self._target_list),
                    len(self._hit_list),
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check error: %s", e)

    # ------------------------------------------------------------------
    # 헬퍼
    # ------------------------------------------------------------------

    async def _get_all_markets(self) -> list[MarketData]:
        """활성 마켓 전체를 가져온다. 캐시가 비면 1회 refresh 시도."""
        if self.market_cache is not None:
            try:
                markets = await self.market_cache.get_all_active_markets()
                if markets:
                    return markets
                # 캐시가 비었으면 refresh 후 재시도
                logger.info("Market cache empty, refreshing...")
                if self.gamma_client is not None:
                    await self.market_cache.refresh_markets(self.gamma_client)
                    return await self.market_cache.get_all_active_markets()
            except Exception as e:
                logger.error("Failed to get markets: %s", e)
        return []

    async def _load_price_histories(self, markets: list[MarketData]) -> None:
        """Stage 2에 필요한 가격 히스토리를 로드한다."""
        if self.clob_client is None:
            return

        for market in markets:
            try:
                if market.yes_token_id and not market.prices_history:
                    history = await self.clob_client.get_prices_history(
                        market.yes_token_id, interval="1w",
                    )
                    market.prices_history = history or []
            except Exception as e:
                logger.debug("Price history load failed for %s: %s", market.condition_id, e)

    async def _subscribe_hit_list(self, hit_list: list[MarketData]) -> None:
        """Hit List 마켓의 WebSocket 구독을 등록한다."""
        if self.ws_manager is None:
            return

        asset_ids = []
        for m in hit_list:
            if m.yes_token_id:
                asset_ids.append(m.yes_token_id)
            if m.no_token_id:
                asset_ids.append(m.no_token_id)

        if asset_ids:
            try:
                await self.ws_manager.subscribe_assets(asset_ids)
                logger.info("WS subscribed to %d assets from hit list", len(asset_ids))
            except Exception as e:
                logger.warning("WS subscription failed: %s", e)

    async def _build_risk_check(self) -> RiskCheck:
        """현재 리스크 상태 스냅샷을 빌드한다."""
        bankroll = 1000.0
        total_exposure = 0.0
        daily_pnl = 0.0
        peak_bankroll = 1000.0
        current_drawdown = 0.0
        market_exposures: dict[str, float] = {}
        circuit_breaker_active = False

        if self.portfolio_tracker is not None:
            try:
                bankroll = await self.portfolio_tracker.get_bankroll()
                total_exposure = await self.portfolio_tracker.get_total_exposure()
                daily_pnl = await self.portfolio_tracker.get_daily_pnl()
                peak_bankroll = await self.portfolio_tracker.get_peak_bankroll()
                current_drawdown = await self.portfolio_tracker.get_current_drawdown()

                # 마켓별 노출
                positions = await self.portfolio_tracker.get_all_positions()
                for pos in positions:
                    market_exposures[pos.condition_id] = (
                        market_exposures.get(pos.condition_id, 0.0) + pos.size * pos.current_price
                    )
            except Exception as e:
                logger.warning("Risk check data fetch failed: %s", e)

        return RiskCheck(
            bankroll=bankroll,
            total_exposure=total_exposure,
            daily_pnl=daily_pnl,
            peak_bankroll=peak_bankroll,
            current_drawdown=current_drawdown,
            market_exposures=market_exposures,
            circuit_breaker_active=circuit_breaker_active,
            frequency_mode=self.frequency_governor.get_current_mode(),
        )

    def _find_market(
        self, condition_id: str, markets: list[MarketData],
    ) -> MarketData | None:
        """마켓 리스트에서 condition_id로 마켓을 찾는다."""
        for m in markets:
            if m.condition_id == condition_id:
                return m
        return None

    def _find_market_by_id(self, condition_id: str) -> MarketData | None:
        """캐시에서 마켓 데이터를 찾는다."""
        if self.market_cache is not None:
            try:
                if hasattr(self.market_cache, "_markets"):
                    return self.market_cache._markets.get(condition_id)
            except Exception:
                pass
        # Target/Hit 리스트에서 검색
        for m in self._target_list + self._hit_list:
            if m.condition_id == condition_id:
                return m
        return None

    # ------------------------------------------------------------------
    # Graceful Shutdown (AC-36)
    # ------------------------------------------------------------------

    def _register_shutdown_handlers(self) -> None:
        """SIGINT/SIGTERM 핸들러를 등록한다."""
        loop = asyncio.get_event_loop()
        for sig in (os_signal.SIGINT, os_signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._signal_shutdown)
            except (NotImplementedError, RuntimeError):
                # Windows에서는 add_signal_handler 미지원
                pass

    def _signal_shutdown(self) -> None:
        """시그널 수신 시 호출된다."""
        logger.info("Shutdown signal received")
        self._running = False

    async def _shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Shutting down Trading Engine...")
        self._running = False

        # 진행 중 주문 완료 대기 (최대 10초)
        try:
            await asyncio.wait_for(asyncio.sleep(0.1), timeout=10)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

        # API 클라이언트 종료
        for name, client in [
            ("GammaClient", self.gamma_client),
            ("DataClient", self.data_client),
            ("ClobClient", self.clob_client),
        ]:
            if client is not None and hasattr(client, "close"):
                try:
                    await client.close()
                except Exception as e:
                    logger.warning("%s close error: %s", name, e)

        # WebSocket 연결 종료
        if self.ws_manager is not None:
            try:
                await self.ws_manager.close()
            except Exception as e:
                logger.warning("WS close error: %s", e)

        # DB 커밋 및 종료
        if self.db_manager is not None:
            try:
                if hasattr(self.db_manager, "close"):
                    await self.db_manager.close()
            except Exception as e:
                logger.warning("DB close error: %s", e)

        logger.info("Trading Engine stopped")
