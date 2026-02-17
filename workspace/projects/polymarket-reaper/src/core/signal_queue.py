"""
Priority Signal Queue (DESIGN.md 3.7절, AC-40).

asyncio.PriorityQueue 기반.
purge_market()으로 특정 마켓 시그널 소거 (AC-40).
drain_expired()로 만료 시그널 30초 주기 제거.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from src.shared.types import Signal

logger = logging.getLogger("reaper.core.signal_queue")


class SignalQueue:
    """Priority Signal Queue.

    시그널의 urgency(낮을수록 높은 우선순위)에 따라 정렬된다.
    Signal dataclass의 sort_key = (urgency, timestamp)이 비교 기준이다.
    """

    def __init__(self, maxsize: int = 0) -> None:
        self._queue: asyncio.PriorityQueue[Signal] = asyncio.PriorityQueue(
            maxsize=maxsize
        )
        # AC-40: Omega 실행 후 소거된 마켓 ID 집합
        # get() 시 이 집합에 속하는 시그널은 스킵한다.
        self._purged_markets: set[str] = set()

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    async def put(self, signal: Signal) -> None:
        """시그널을 큐에 투입한다.

        이미 소거된 마켓의 시그널은 즉시 폐기한다.
        """
        if signal.condition_id in self._purged_markets:
            logger.debug(
                "Signal %s dropped: market %s is purged",
                signal.id, signal.condition_id,
            )
            return
        await self._queue.put(signal)
        logger.debug(
            "Signal enqueued: id=%s strategy=%s market=%s urgency=%s",
            signal.id, signal.strategy.value, signal.condition_id, signal.urgency.name,
        )

    async def get(self) -> Signal:
        """가장 높은 우선순위의 시그널을 꺼낸다.

        소거된 마켓의 시그널이나 만료된 시그널은 자동으로 건너뛴다.
        """
        while True:
            signal = await self._queue.get()
            # 소거된 마켓 필터링
            if signal.condition_id in self._purged_markets:
                logger.debug(
                    "Signal %s skipped on get: market %s purged",
                    signal.id, signal.condition_id,
                )
                self._queue.task_done()
                continue
            # 만료된 시그널 필터링
            if signal.is_expired:
                logger.debug("Signal %s skipped on get: expired", signal.id)
                self._queue.task_done()
                continue
            return signal

    def qsize(self) -> int:
        """대기 중인 시그널 수를 반환한다."""
        return self._queue.qsize()

    def purge_market(self, condition_id: str) -> int:
        """AC-40: 특정 마켓의 시그널을 모두 소거 표시한다.

        asyncio.PriorityQueue는 중간 삭제가 불편하므로,
        _purged_markets에 추가하고 get() 시 필터링한다.

        Returns:
            소거된 마켓의 등록 여부 (1이면 새로 등록, 0이면 이미 등록됨).
        """
        if condition_id in self._purged_markets:
            return 0
        self._purged_markets.add(condition_id)
        logger.info("Market %s added to purge list", condition_id)
        return 1

    async def drain_expired(self) -> int:
        """만료된 시그널을 제거한다. 30초 주기로 호출된다.

        Returns:
            제거된 시그널 수.
        """
        drained = 0
        remaining: list[Signal] = []

        # 현재 큐의 모든 시그널을 꺼내서 필터링
        while not self._queue.empty():
            try:
                signal = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            if signal.is_expired or signal.condition_id in self._purged_markets:
                drained += 1
                self._queue.task_done()
            else:
                remaining.append(signal)
                self._queue.task_done()

        # 유효한 시그널을 다시 투입
        for signal in remaining:
            await self._queue.put(signal)

        if drained > 0:
            logger.info("Drained %d expired/purged signals", drained)

        # 오래된 purge 목록 정리 (큐가 비어있으면 purge 목록도 클리어)
        if self._queue.empty():
            self._purged_markets.clear()

        return drained

    def clear_purge(self, condition_id: str) -> None:
        """특정 마켓의 소거 표시를 해제한다."""
        self._purged_markets.discard(condition_id)
