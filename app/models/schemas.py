from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class EvalBlock(BaseModel):
    groundedness: float = Field(..., ge=0.0, le=1.0)
    relevance: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    flagged: bool
    reasoning: str


class ChatResponse(BaseModel):
    response: str
    eval: EvalBlock
    tools_called: list[str]
    session_id: str


class MessageOut(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime
    session_id: str


class CatalogPlan(BaseModel):
    name: str
    price: str
    features: list[str]


class CatalogOut(BaseModel):
    plans: list[CatalogPlan]


class HealthOut(BaseModel):
    status: Literal["ok"]
    app: str
    environment: str


class EvalAggOut(BaseModel):
    user_id: str
    total: int
    avg_confidence: float
    avg_groundedness: float
    avg_relevance: float
    flagged_count: int
    flagged_pct: float
    last_updated_at: datetime | None
    samples: list[dict[str, Any]] = Field(default_factory=list)

