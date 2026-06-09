from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.sales_agent import PersistentSalesAssistantAgent
from app.db.models import EvalRecord


class ChatService:
    def __init__(self, *, db: Session, agent: PersistentSalesAssistantAgent):
        self.db = db
        self.agent = agent

    def chat(self, *, user_id: str, message: str) -> dict:
        result = self.agent.run(user_id=user_id, message=message)

        ev = result["eval"]
        rec = EvalRecord(
            session_id=result["session_id"],
            user_id=user_id,
            groundedness=ev["groundedness"],
            relevance=ev["relevance"],
            confidence=ev["confidence"],
            flagged=ev["flagged"],
            reasoning=ev["reasoning"],
            tools_called={"tools_called": result.get("tools_called", [])},
        )
        self.db.add(rec)
        self.db.commit()

        return result

