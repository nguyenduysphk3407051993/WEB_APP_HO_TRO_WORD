"""Admin: quản lý API keys Gemini (có mật khẩu bảo vệ)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.services.gemini_pool import get_pool, test_single_key

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def require_admin(x_admin_password: str = Header(default="")) -> None:
    if not settings.ADMIN_PASSWORD:
        raise HTTPException(
            503,
            "ADMIN_PASSWORD chưa được thiết lập trong .env — không thể quản lý keys qua web.",
        )
    if x_admin_password != settings.ADMIN_PASSWORD:
        raise HTTPException(401, "Sai mật khẩu admin.")


class KeysPayload(BaseModel):
    keys: list[str] = Field(..., description="Danh sách API key (mỗi key 1 phần tử)")


class SingleKeyPayload(BaseModel):
    key: str


class TestKeysPayload(BaseModel):
    keys: list[str]


@router.get("/auth-check")
def auth_check(_: None = Depends(require_admin)) -> dict:
    """Kiểm tra mật khẩu — frontend dùng để verify trước khi vào trang admin."""
    return {"ok": True}


@router.get("/keys/stats")
def keys_stats(_: None = Depends(require_admin)) -> dict:
    try:
        return get_pool().stats()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/keys")
async def replace_keys(
    payload: KeysPayload, _: None = Depends(require_admin)
) -> dict:
    """Thay toàn bộ danh sách key bằng payload mới (paste 10 key cùng lúc)."""
    count = await get_pool().replace_all(payload.keys)
    return {"total": count}


@router.post("/keys/add")
async def add_key(
    payload: SingleKeyPayload, _: None = Depends(require_admin)
) -> dict:
    try:
        count = await get_pool().add_key(payload.key)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"total": count}


@router.delete("/keys/{index}")
async def remove_key(index: int, _: None = Depends(require_admin)) -> dict:
    try:
        count = await get_pool().remove_key(index)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"total": count}


@router.post("/keys/{index}/reset")
async def reset_key(index: int, _: None = Depends(require_admin)) -> dict:
    try:
        await get_pool().reset_key(index)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True}


@router.post("/keys/test")
async def test_keys(
    payload: TestKeysPayload, _: None = Depends(require_admin)
) -> dict:
    """Test song song nhiều key — không lưu, chỉ kiểm tra."""
    keys = [k.strip() for k in payload.keys if k.strip()]
    if not keys:
        raise HTTPException(400, "Không có key để test.")
    results = await asyncio.gather(
        *[test_single_key(k, settings.GEMINI_MODEL) for k in keys]
    )
    masked = [
        {"preview": f"{k[:6]}...{k[-4:]}" if len(k) > 12 else k, **r}
        for k, r in zip(keys, results)
    ]
    return {"results": masked, "ok": sum(1 for r in results if r["ok"]), "total": len(results)}
