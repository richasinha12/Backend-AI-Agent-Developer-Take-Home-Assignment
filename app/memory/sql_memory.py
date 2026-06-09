from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatSession, UserMemoryKV
from app.memory.base import MemoryContext, MemoryStore


class SqlMemoryStore(MemoryStore):
    def __init__(self, db: Session):
        self.db = db

    def get_context(self, user_id: str, max_messages: int = 12) -> MemoryContext:
        facts_rows = self.db.execute(
            select(UserMemoryKV).where(UserMemoryKV.user_id == user_id)
        ).scalars().all()
        facts = {r.key: r.value for r in facts_rows}
        updated_at = max((r.updated_at for r in facts_rows), default=None)

        msg_rows = (
            self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id)
                .order_by(desc(ChatMessage.created_at))
                .limit(max_messages)
            )
            .scalars()
            .all()
        )
        # return in chronological order
        msg_rows = list(reversed(msg_rows))
        recent_messages = [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
                "session_id": m.session_id,
            }
            for m in msg_rows
        ]

        return MemoryContext(facts=facts, recent_messages=recent_messages, updated_at=updated_at)

    def append_message(self, *, user_id: str, session_id: str, role: str, content: str) -> None:
        # Ensure session exists (idempotent)
        existing = self.db.get(ChatSession, session_id)
        if existing is None:
            self.db.add(ChatSession(session_id=session_id, user_id=user_id))
            self.db.flush()

        self.db.add(ChatMessage(user_id=user_id, session_id=session_id, role=role, content=content))
        self.db.commit()

    def upsert_fact(self, *, user_id: str, key: str, value: str) -> None:
        row = (
            self.db.execute(
                select(UserMemoryKV).where(UserMemoryKV.user_id == user_id, UserMemoryKV.key == key)
            )
            .scalars()
            .first()
        )
        if row is None:
            row = UserMemoryKV(user_id=user_id, key=key, value=value, updated_at=datetime.utcnow())
            self.db.add(row)
        else:
            row.value = value
            row.updated_at = datetime.utcnow()
        self.db.commit()

    def clear_user(self, user_id: str) -> None:
        self.db.execute(delete(UserMemoryKV).where(UserMemoryKV.user_id == user_id))
        self.db.execute(delete(ChatMessage).where(ChatMessage.user_id == user_id))
        self.db.execute(delete(ChatSession).where(ChatSession.user_id == user_id))
        self.db.commit()

