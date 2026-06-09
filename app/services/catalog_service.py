from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz


class CatalogService:
    def __init__(self, catalog_path: str):
        self.catalog_path = catalog_path

    def load(self) -> dict[str, Any]:
        p = Path(self.catalog_path)
        return json.loads(p.read_text(encoding="utf-8"))

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        data = self.load()
        plans = data.get("plans", [])
        q = (query or "").strip().lower()
        if not q:
            return plans[:limit]

        scored = []
        for plan in plans:
            hay = " ".join(
                [plan.get("name", ""), plan.get("price", ""), " ".join(plan.get("features", []))]
            ).lower()
            scored.append((fuzz.token_set_ratio(q, hay), plan))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

