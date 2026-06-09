from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session

from app.agents.sales_agent import PersistentSalesAssistantAgent
from app.config import settings
from app.db.models import ChatMessage, EvalRecord
from app.db.session import get_db
from app.memory.sql_memory import SqlMemoryStore
from app.models.schemas import (
    CatalogOut,
    ChatRequest,
    ChatResponse,
    EvalAggOut,
    HealthOut,
    MessageOut,
)
from app.services.catalog_service import CatalogService
from app.services.chat_service import ChatService
from app.services.eval_service import EvalService


router = APIRouter()


def _openai_client():
    if not settings.openai_api_key:
        return None
    # Import here so the app still boots if OpenAI is not configured.
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok", app=settings.app_name, environment=settings.environment)


@router.get("/catalog", response_model=CatalogOut)
def get_catalog() -> CatalogOut:
    data = json.loads(Path(settings.catalog_path).read_text(encoding="utf-8"))
    return CatalogOut.model_validate(data)


@router.post("/chat/{user_id}", response_model=ChatResponse)
def chat(user_id: str, payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    memory = SqlMemoryStore(db)
    catalog = CatalogService(settings.catalog_path)
    client = _openai_client()
    eval_service = EvalService(openai_client=client)
    agent = PersistentSalesAssistantAgent(memory=memory, catalog=catalog, eval_service=eval_service, openai_client=client)
    chat_service = ChatService(db=db, agent=agent)

    result = chat_service.chat(user_id=user_id, message=payload.message)
    return ChatResponse(
        response=result["response"],
        eval=result["eval"],
        tools_called=result["tools_called"],
        session_id=result["session_id"],
    )


@router.get("/chat/{user_id}/history", response_model=list[MessageOut])
def history(user_id: str, db: Session = Depends(get_db)) -> list[MessageOut]:
    rows = (
        db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        .scalars()
        .all()
    )
    return [
        MessageOut(role=r.role, content=r.content, created_at=r.created_at, session_id=r.session_id) for r in rows
    ]


@router.delete("/chat/{user_id}/memory")
def clear_memory(user_id: str, db: Session = Depends(get_db)) -> Response:
    memory = SqlMemoryStore(db)
    memory.clear_user(user_id)
    db.execute(delete(EvalRecord).where(EvalRecord.user_id == user_id))
    db.commit()
    return Response(status_code=204)


@router.get("/chat/{user_id}/evals", response_model=EvalAggOut)
def evals(user_id: str, db: Session = Depends(get_db)) -> EvalAggOut:
    total = db.execute(select(func.count(EvalRecord.id)).where(EvalRecord.user_id == user_id)).scalar_one()
    if total == 0:
        return EvalAggOut(
            user_id=user_id,
            total=0,
            avg_confidence=0.0,
            avg_groundedness=0.0,
            avg_relevance=0.0,
            flagged_count=0,
            flagged_pct=0.0,
            last_updated_at=None,
            samples=[],
        )

    agg = db.execute(
        select(
            func.avg(EvalRecord.confidence),
            func.avg(EvalRecord.groundedness),
            func.avg(EvalRecord.relevance),
            func.sum(case((EvalRecord.flagged == True, 1), else_=0)),
            func.max(EvalRecord.created_at),
        ).where(EvalRecord.user_id == user_id)
    ).one()

    avg_conf, avg_ground, avg_rel, flagged_count, last_ts = agg
    flagged_count = int(flagged_count or 0)

    samples_rows = (
        db.execute(
            select(EvalRecord)
            .where(EvalRecord.user_id == user_id)
            .order_by(EvalRecord.created_at.desc())
            .limit(5)
        )
        .scalars()
        .all()
    )
    samples = [
        {
            "created_at": r.created_at.isoformat(),
            "confidence": r.confidence,
            "groundedness": r.groundedness,
            "relevance": r.relevance,
            "flagged": r.flagged,
            "reasoning": r.reasoning,
            "session_id": r.session_id,
        }
        for r in samples_rows
    ]

    return EvalAggOut(
        user_id=user_id,
        total=int(total),
        avg_confidence=float(avg_conf or 0.0),
        avg_groundedness=float(avg_ground or 0.0),
        avg_relevance=float(avg_rel or 0.0),
        flagged_count=flagged_count,
        flagged_pct=float(flagged_count / total),
        last_updated_at=last_ts,
        samples=samples,
    )


@router.get("/")
def index() -> Response:
    # Tiny built-in UI for quick demo video (no frontend build step required).
    html = f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Persistent Sales Assistant</title>
    <style>
      body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; max-width: 900px; margin: 40px auto; padding: 0 16px; }}
      .row {{ display: flex; gap: 10px; }}
      input, textarea, button {{ font-size: 14px; }}
      textarea {{ width: 100%; height: 90px; }}
      pre {{ background: #0b1020; color: #e9eefc; padding: 12px; overflow: auto; border-radius: 8px; }}
      .muted {{ color: #666; }}
    </style>
  </head>
  <body>
    <h2>Persistent Sales Assistant (API Demo)</h2>
    <p class="muted">This UI calls <code>POST /chat/{{user_id}}</code> and shows the structured eval block + tools called.</p>
    <div class="row">
      <div style="flex: 1">
        <label>User ID</label><br/>
        <input id="userId" value="demo-user" style="width: 100%; padding: 8px;" />
      </div>
      <div style="width: 180px">
        <label>&nbsp;</label><br/>
        <button id="wipe" style="width: 100%; padding: 10px;">Wipe memory</button>
      </div>
    </div>
    <div style="margin-top: 14px;">
      <label>Message</label><br/>
      <textarea id="msg">What's your enterprise pricing?</textarea>
    </div>
    <button id="send" style="margin-top: 10px; padding: 10px 14px;">Send</button>
    <h3>Response</h3>
    <pre id="out"></pre>
    <script>
      const out = document.getElementById('out');
      const userIdEl = document.getElementById('userId');
      const msgEl = document.getElementById('msg');
      document.getElementById('send').onclick = async () => {{
        out.textContent = "Loading...";
        const userId = userIdEl.value.trim();
        const res = await fetch(`/chat/${{encodeURIComponent(userId)}}`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ message: msgEl.value }})
        }});
        out.textContent = JSON.stringify(await res.json(), null, 2);
      }};
      document.getElementById('wipe').onclick = async () => {{
        const userId = userIdEl.value.trim();
        await fetch(`/chat/${{encodeURIComponent(userId)}}/memory`, {{ method: "DELETE" }});
        out.textContent = "Memory wiped (204).";
      }};
    </script>
  </body>
</html>
"""
    return Response(content=html, media_type="text/html")
