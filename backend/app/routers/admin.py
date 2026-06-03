"""Endpoint giám sát pool Gemini keys."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.gemini_pool import get_pool

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/keys/stats")
def keys_stats() -> dict:
    """Trạng thái từng key trong pool."""
    try:
        return get_pool().stats()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
