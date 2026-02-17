"""
Rate Limiter — 토큰 버킷 방식 (슬라이딩 윈도우).
모든 API 호출 전 wait_if_needed()를 호출하세요.
"""

import logging
import time
from collections import deque
from typing import Deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    슬라이딩 윈도우 방식 Rate Limiter.
    최근 60초 간의 요청 수를 추적하여 max_requests_per_minute 초과 시 대기.

    통합 계약: 80 req/분 (100 제한에 20% 마진).
    """

    def __init__(self, max_requests_per_minute: int = 80) -> None:
        self.max_rpm = max_requests_per_minute
        self._window_secs: float = 60.0
        self._timestamps: Deque[float] = deque()

    def _cleanup_old(self, now: float) -> None:
        """60초 이전 타임스탬프 제거."""
        cutoff = now - self._window_secs
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def wait_if_needed(self) -> None:
        """
        요청 전 호출. 한도 초과 시 슬립 후 반환.
        """
        now = time.time()
        self._cleanup_old(now)

        if len(self._timestamps) >= self.max_rpm:
            # 가장 오래된 요청이 윈도우에서 빠질 때까지 대기
            oldest = self._timestamps[0]
            sleep_time = (oldest + self._window_secs) - now + 0.05  # 50ms 마진
            if sleep_time > 0:
                logger.debug(
                    "Rate limit 도달 (%d/%d). %.2f초 대기...",
                    len(self._timestamps), self.max_rpm, sleep_time
                )
                time.sleep(sleep_time)
                self._cleanup_old(time.time())

    def record_request(self) -> None:
        """요청 발생 후 호출. 타임스탬프 기록."""
        self._timestamps.append(time.time())

    def handle_429(self, retry_count: int) -> float:
        """
        HTTP 429 수신 시 지수 백오프 대기 시간(초) 반환.
        최대 3회 재시도: 2^0=1초, 2^1=2초, 2^2=4초.
        retry_count가 3 이상이면 ValueError 발생.
        """
        if retry_count >= 3:
            raise RuntimeError(
                f"429 Too Many Requests — {retry_count}회 재시도 후 포기합니다."
            )
        wait = float(2 ** retry_count)
        logger.warning("429 Too Many Requests. %.0f초 백오프 대기 (재시도 %d/3).", wait, retry_count + 1)
        time.sleep(wait)
        return wait

    @property
    def current_count(self) -> int:
        """현재 윈도우 내 요청 수."""
        self._cleanup_old(time.time())
        return len(self._timestamps)
