"""Tiện ích upload và lưu file."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings


def validate_extension(filename: str, allowed: set[str]) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng {ext} không được hỗ trợ. Cho phép: {sorted(allowed)}",
        )
    return ext


async def save_upload(file: UploadFile, allowed: set[str]) -> Path:
    ext = validate_extension(file.filename or "", allowed)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File vượt quá kích thước tối đa.")
    target = settings.UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    target.write_bytes(content)
    return target


def new_output_path(suffix: str) -> Path:
    return settings.OUTPUT_DIR / f"{uuid.uuid4().hex}{suffix}"
