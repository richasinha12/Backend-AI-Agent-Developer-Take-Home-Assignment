from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import settings


class EvalService:
    def __init__(self, *, openai_client: OpenAI | None):
        self.client = openai_client

    def _heuristic_eval(self, *, response: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        # Groundedness: high if response mentions plan names found in evidence.
        evidence_text = json.dumps(evidence).lower()
        r = response.lower()
        hits = sum(1 for name in ["starter", "growth", "enterprise"] if name in r and name in evidence_text)
        groundedness = min(0.6 + 0.15 * hits, 0.95)
        relevance = 0.85 if evidence else 0.6
        confidence = (groundedness * 0.6) + (relevance * 0.4)

        flagged = confidence < settings.confidence_flag_threshold
        reasoning = (
            "Heuristic eval: response compared against catalog search evidence; "
            f"hits={hits}, evidence_items={len(evidence)}."
        )
        return {
            "groundedness": float(round(groundedness, 2)),
            "relevance": float(round(relevance, 2)),
            "confidence": float(round(confidence, 2)),
            "flagged": bool(flagged),
            "reasoning": reasoning,
        }

    def score(
        self,
        *,
        user_message: str,
        response: str,
        evidence: list[dict[str, Any]],
        user_memory: dict[str, Any],
        tools_called: list[str],
    ) -> dict[str, Any]:
        if not self.client:
            return self._heuristic_eval(response=response, evidence=evidence)

        prompt = {
            "task": "Score the assistant response for groundedness, relevance, and confidence (0..1).",
            "user_message": user_message,
            "assistant_response": response,
            "catalog_evidence": evidence,
            "user_memory_used": user_memory,
            "tools_called": tools_called,
            "output_format": {
                "groundedness": 0.0,
                "relevance": 0.0,
                "confidence": 0.0,
                "flagged": False,
                "reasoning": "short reasoning",
            },
            "rules": [
                "Scores must be floats between 0 and 1.",
                "Flagged should be true if confidence < 0.55 or if answer contains claims not supported by evidence.",
                "Reasoning must mention whether the response is directly supported by catalog_evidence.",
                "Return ONLY valid JSON (no markdown).",
            ],
        }

        res = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a strict JSON generator for evaluation."},
                {"role": "user", "content": json.dumps(prompt)},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = res.choices[0].message.content or "{}"
        try:
            out = json.loads(raw)
        except Exception:
            return self._heuristic_eval(response=response, evidence=evidence)

        # Clamp / normalize
        def clamp(x: Any) -> float:
            try:
                v = float(x)
            except Exception:
                v = 0.0
            return max(0.0, min(1.0, v))

        out = {
            "groundedness": clamp(out.get("groundedness")),
            "relevance": clamp(out.get("relevance")),
            "confidence": clamp(out.get("confidence")),
            "flagged": bool(out.get("flagged")),
            "reasoning": str(out.get("reasoning", ""))[:1000],
        }
        # enforce threshold-based flag (so it's consistent)
        if out["confidence"] < settings.confidence_flag_threshold:
            out["flagged"] = True
        return out

