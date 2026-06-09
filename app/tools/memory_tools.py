from __future__ import annotations

from typing import Any

from app.memory.base import MemoryStore


def get_user_memory(user_id: str, *, memory: MemoryStore, max_messages: int = 12) -> dict[str, Any]:
    ctx = memory.get_context(user_id=user_id, max_messages=max_messages)
    return {
        "facts": ctx.facts,
        "recent_messages": [
            {"role": m["role"], "content": m["content"], "session_id": m["session_id"]}
            for m in ctx.recent_messages
        ],
        "updated_at": ctx.updated_at.isoformat() if ctx.updated_at else None,
    }


def flag_for_human(user_id: str, reason: str) -> dict[str, Any]:
    # Bonus tool: for take-home we just return a structured payload that could be sent to a queue.
    return {"user_id": user_id, "flagged": True, "reason": reason}

