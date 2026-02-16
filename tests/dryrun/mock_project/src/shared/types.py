"""공유 타입 정의 — 설계자만 수정."""

from dataclasses import dataclass


@dataclass
class Todo:
    id: int
    title: str
    done: bool = False
