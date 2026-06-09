from __future__ import annotations

import json
import re
import uuid
from typing import Any

from openai import OpenAI

from app.config import settings
from app.memory.base import MemoryStore
from app.services.catalog_service import CatalogService
from app.services.eval_service import EvalService
from app.tools.catalog_tools import search_catalog
from app.tools.memory_tools import get_user_memory


class PersistentSalesAssistantAgent:
    def __init__(
        self,
        *,
        memory: MemoryStore,
        catalog: CatalogService,
        eval_service: EvalService,
        openai_client: OpenAI | None,
    ):
        self.memory = memory
        self.catalog = catalog
        self.eval_service = eval_service
        self.client = openai_client

    def _extract_plan_interest(self, text: str) -> str | None:
        t = text.lower()
        for name in ["starter", "growth", "enterprise"]:
            if re.search(rf"\b{name}\b", t):
                return name.capitalize()
        return None

    def _update_memory(self, *, user_id: str, user_message: str, assistant_response: str) -> None:
        plan = self._extract_plan_interest(user_message) or self._extract_plan_interest(assistant_response)
        if plan:
            self.memory.upsert_fact(user_id=user_id, key="last_plan_discussed", value=plan)

        # Very small “interest” extractor (e.g., SSO, audit logs, SLA)
        keywords = ["sso", "audit logs", "sla", "webhooks", "api access", "priority support", "email support"]
        interests = [k for k in keywords if k in (user_message.lower() + " " + assistant_response.lower())]
        if interests:
            self.memory.upsert_fact(user_id=user_id, key="interests", value=", ".join(sorted(set(interests))))

    def _fallback_response(self, *, user_id: str, message: str) -> tuple[str, list[str], list[dict], dict]:
        tools_called: list[str] = []

        mem = get_user_memory(user_id, memory=self.memory)
        tools_called.append("get_user_memory")

        # If the user writes a follow-up ("does that include..."), bias search using remembered plan.
        last_plan = mem.get("facts", {}).get("last_plan_discussed")
        is_followup = bool(re.search(r"\b(that|it|this)\b", message.lower())) or ("include" in message.lower())
        query = f"{last_plan} {message}" if (last_plan and is_followup) else message

        hits = search_catalog(query, catalog_service=self.catalog, limit=3)
        tools_called.append("search_catalog")

        # If follow-up + we have a remembered plan, prefer the exact plan entry.
        if last_plan and is_followup:
            exact = next((p for p in self.catalog.load().get("plans", []) if p.get("name") == last_plan), None)
            if exact:
                hits = [exact] + [h for h in hits if h.get("name") != last_plan]

        if hits:
            top = hits[0]
            response = f"{top['name']} pricing is {top['price']}. Key features: {', '.join(top['features'])}."

            # If the user is asking about a specific feature, answer that explicitly.
            asked = message.lower()
            asked_feature = None
            for f in ["sso", "audit logs", "sla", "webhooks", "api access", "priority support", "email support"]:
                if f in asked:
                    asked_feature = f
                    break
            if asked_feature:
                has = any(asked_feature.lower() == feat.lower() for feat in top.get("features", []))
                response = f"Yes — {top['name']} includes {asked_feature}." if has else f"No — {top['name']} does not include {asked_feature}."
                response += f" ({top['name']} is {top['price']}; features: {', '.join(top['features'])}.)"

            if last_plan and last_plan != top["name"]:
                response += f" (Earlier we discussed {last_plan}.)"
        else:
            response = (
                "I couldn't find that in the catalog. Ask about Starter ($49/mo), Growth ($199/mo), "
                "or Enterprise ($499/mo), and I’ll answer using the catalog."
            )

        return response, tools_called, hits, mem

    def _llm_response(self, *, user_id: str, message: str) -> tuple[str, list[str], list[dict], dict]:
        # Always call real tools (per assignment). LLM may request more, but we ensure at least these two.
        tools_called: list[str] = []
        mem = get_user_memory(user_id, memory=self.memory)
        tools_called.append("get_user_memory")

        hits = search_catalog(message, catalog_service=self.catalog, limit=3)
        tools_called.append("search_catalog")

        sys = (
            "You are a B2B SaaS sales assistant. You must answer ONLY using the provided catalog evidence "
            "and the user memory. If something is not in evidence, say you don't know. Be concise."
        )
        user_payload = {
            "user_message": message,
            "user_memory": mem,
            "catalog_evidence": hits,
            "instructions": [
                "Answer grounded in catalog_evidence.",
                "If user asks follow-up like 'does that include SSO?', use last_plan_discussed from memory.",
            ],
        }

        res = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
            temperature=0.2,
        )
        response = (res.choices[0].message.content or "").strip()
        if not response:
            # Safety net
            response = f"From the catalog: {hits[0]['name']} is {hits[0]['price']}." if hits else "I don't know."
        return response, tools_called, hits, mem

    def run(self, *, user_id: str, message: str, session_id: str | None = None) -> dict[str, Any]:
        session_id = session_id or str(uuid.uuid4())

        # Persist user message (cross-session memory)
        self.memory.append_message(user_id=user_id, session_id=session_id, role="user", content=message)

        if self.client:
            response, tools_called, hits, mem = self._llm_response(user_id=user_id, message=message)
        else:
            response, tools_called, hits, mem = self._fallback_response(user_id=user_id, message=message)

        # Persist assistant message
        self.memory.append_message(user_id=user_id, session_id=session_id, role="assistant", content=response)

        # Update memory facts (plan discussed / interests)
        self._update_memory(user_id=user_id, user_message=message, assistant_response=response)

        eval_block = self.eval_service.score(
            user_message=message,
            response=response,
            evidence=hits,
            user_memory=mem,
            tools_called=tools_called,
        )

        return {
            "response": response,
            "eval": eval_block,
            "tools_called": tools_called,
            "session_id": session_id,
            "evidence": hits,
            "memory_used": mem,
        }
