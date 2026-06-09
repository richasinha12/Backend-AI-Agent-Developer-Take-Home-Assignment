from __future__ import annotations

from typing import Any

from app.services.catalog_service import CatalogService


def search_catalog(query: str, *, catalog_service: CatalogService, limit: int = 3) -> list[dict[str, Any]]:
    """Keyword-ish search over plan name/price/features (no hallucination)."""
    return catalog_service.search(query=query, limit=limit)

