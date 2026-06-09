from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MemoryContext:
    facts: dict[str, str]
    recent_messages: list[dict]
    updated_at: datetime | None


class MemoryStore(ABC):
    """Abstraction layer so swapping SQLite→Postgres/Mem0 is a 1-file change."""

    @abstractmethod
    def get_context(self, user_id: str, max_messages: int = 12) -> MemoryContext:
        raise NotImplementedError

    @abstractmethod
    def append_message(self, *, user_id: str, session_id: str, role: str, content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def upsert_fact(self, *, user_id: str, key: str, value: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear_user(self, user_id: str) -> None:
        raise NotImplementedError

