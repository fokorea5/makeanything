"""
Frequency Governor (DESIGN.md 3.11절, 7절, AC-28, AC-29, AC-30).

4모드: TURBO / NORMAL / STEALTH / AUTO.
AUTO: DD 기반 자동 전환.
SIGHUP / DB 런타임 모드 변경.
Stage 주기 + Kelly 배수 제공.
"""

from __future__ import annotations

import signal as os_signal
import logging
from datetime import datetime
from typing import Any

from config import Config
from src.shared.types import FrequencyMode, FrequencyState

logger = logging.getLogger("reaper.core.frequency_governor")

# 모드별 파라미터 테이블 (AC-28)
_MODE_PARAMS: dict[str, dict[str, float]] = {
    "TURBO": {
        "stage1_interval": 180.0,   # 3분
        "stage2_interval": 30.0,    # 30초
        "kelly_multiplier": 1.0,
    },
    "NORMAL": {
        "stage1_interval": 300.0,   # 5분
        "stage2_interval": 60.0,    # 60초
        "kelly_multiplier": 0.7,
    },
    "STEALTH": {
        "stage1_interval": 600.0,   # 10분
        "stage2_interval": 120.0,   # 120초
        "kelly_multiplier": 0.4,
    },
}


class FrequencyGovernor:
    """Frequency Governor: 거래 빈도를 DD 상황에 따라 동적으로 조절한다.

    Governor와 Risk Sentinel은 DD를 독립적으로 참조하며,
    두 효과는 곱셈으로 중첩된다.
    """

    def __init__(self, config: Config, db_manager: Any = None) -> None:
        self.config = config
        self.db_manager = db_manager

        # 초기 모드 설정
        mode_str = getattr(config, "FREQUENCY_MODE", "AUTO")
        try:
            self._mode = FrequencyMode(mode_str)
        except ValueError:
            logger.warning("Invalid FREQUENCY_MODE '%s', defaulting to AUTO", mode_str)
            self._mode = FrequencyMode.AUTO

        # AUTO DD 임계값 (AC-29)
        self._auto_dd_turbo: float = getattr(config, "AUTO_DD_TURBO", 0.03)
        self._auto_dd_normal: float = getattr(config, "AUTO_DD_NORMAL", 0.06)

        # AUTO 모드일 때의 현재 실질 모드
        self._auto_effective_mode: str = "NORMAL"

        # 상태 기록
        self._last_transition = datetime.utcnow()
        self._transition_reason = "init"

        # SIGHUP 핸들러 등록 (AC-30)
        self._register_sighup()

        logger.info("Frequency Governor initialized: mode=%s", self._mode.value)

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def get_current_mode(self) -> FrequencyMode:
        """현재 모드를 반환한다."""
        return self._mode

    def get_effective_mode_name(self) -> str:
        """실질적으로 적용되는 모드명을 반환한다.

        AUTO일 때는 DD에 따라 결정된 실질 모드를 반환한다.
        """
        if self._mode == FrequencyMode.AUTO:
            return self._auto_effective_mode
        return self._mode.value

    def get_stage1_interval(self) -> float:
        """Stage 1 스캔 주기(초)를 반환한다."""
        effective = self.get_effective_mode_name()
        return _MODE_PARAMS.get(effective, _MODE_PARAMS["NORMAL"])["stage1_interval"]

    def get_stage2_interval(self) -> float:
        """Stage 2 스캔 주기(초)를 반환한다."""
        effective = self.get_effective_mode_name()
        return _MODE_PARAMS.get(effective, _MODE_PARAMS["NORMAL"])["stage2_interval"]

    def get_kelly_multiplier(self) -> float:
        """Kelly 배수(0.4~1.0)를 반환한다."""
        effective = self.get_effective_mode_name()
        return _MODE_PARAMS.get(effective, _MODE_PARAMS["NORMAL"])["kelly_multiplier"]

    def get_state(self) -> FrequencyState:
        """현재 Governor 상태를 FrequencyState로 반환한다."""
        return FrequencyState(
            current_mode=self._mode,
            stage1_interval=self.get_stage1_interval(),
            stage2_interval=self.get_stage2_interval(),
            kelly_multiplier=self.get_kelly_multiplier(),
            auto_active=(self._mode == FrequencyMode.AUTO),
            last_transition=self._last_transition,
            transition_reason=self._transition_reason,
        )

    async def check_auto_transition(self, current_dd: float) -> FrequencyMode | None:
        """AUTO 모드에서 DD에 따른 모드 전환을 체크한다 (AC-29).

        Args:
            current_dd: 현재 drawdown 비율 (0.0~1.0).

        Returns:
            모드가 전환되면 새 모드를, 변경 없으면 None을 반환한다.
        """
        if self._mode != FrequencyMode.AUTO:
            return None

        # DD 기반 모드 결정
        if current_dd < self._auto_dd_turbo:
            new_effective = "TURBO"
        elif current_dd < self._auto_dd_normal:
            new_effective = "NORMAL"
        else:
            new_effective = "STEALTH"

        if new_effective != self._auto_effective_mode:
            old = self._auto_effective_mode
            self._auto_effective_mode = new_effective
            self._last_transition = datetime.utcnow()
            self._transition_reason = f"auto_dd: {current_dd:.2%} → {new_effective}"
            logger.info(
                "AUTO transition: %s → %s (DD=%.2f%%)",
                old, new_effective, current_dd * 100,
            )
            return FrequencyMode(new_effective)

        return None

    def set_mode(self, mode: FrequencyMode) -> None:
        """런타임 모드 변경 (AC-30).

        AUTO 모드에서 수동 전환 시 AUTO 해제.
        """
        old = self._mode
        self._mode = mode
        self._last_transition = datetime.utcnow()
        self._transition_reason = "manual"

        if mode != FrequencyMode.AUTO:
            # 수동 모드 설정 시 effective도 동기화
            self._auto_effective_mode = mode.value

        logger.info("Mode changed: %s → %s (manual)", old.value, mode.value)

    async def check_db_mode(self) -> FrequencyMode | None:
        """DB 플래그에서 모드 변경을 감지한다 (AC-30).

        Returns:
            변경된 모드 또는 None.
        """
        if self.db_manager is None:
            return None

        try:
            db_mode_str = await self.db_manager.get_frequency_mode()
            if db_mode_str is None:
                return None

            try:
                db_mode = FrequencyMode(db_mode_str)
            except ValueError:
                return None

            if db_mode != self._mode:
                old = self._mode
                self._mode = db_mode
                self._last_transition = datetime.utcnow()
                self._transition_reason = "db_flag"

                if db_mode != FrequencyMode.AUTO:
                    self._auto_effective_mode = db_mode.value

                logger.info(
                    "Mode changed via DB: %s → %s", old.value, db_mode.value,
                )
                return db_mode
        except Exception as e:
            logger.warning("DB mode check failed: %s", e)

        return None

    # ------------------------------------------------------------------
    # SIGHUP 핸들러 (AC-30)
    # ------------------------------------------------------------------

    def _register_sighup(self) -> None:
        """SIGHUP 시그널 핸들러를 등록한다.

        SIGHUP 수신 시 DB에서 모드를 읽어 전환한다.
        Windows에서는 SIGHUP이 없으므로 무시한다.
        """
        try:
            os_signal.signal(os_signal.SIGHUP, self._on_sighup)
            logger.debug("SIGHUP handler registered")
        except (AttributeError, OSError):
            # Windows에서는 SIGHUP 미지원
            logger.debug("SIGHUP not available on this platform")

    def _on_sighup(self, signum: int, frame: Any) -> None:
        """SIGHUP 수신 시 호출된다.

        비동기 DB 조회는 여기서 할 수 없으므로 플래그만 설정한다.
        다음 check_db_mode() 호출에서 실제 전환이 일어난다.
        """
        logger.info("SIGHUP received: will check DB for mode change")
        self._transition_reason = "sighup_pending"
