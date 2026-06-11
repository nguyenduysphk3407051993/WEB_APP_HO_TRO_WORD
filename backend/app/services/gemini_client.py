"""HTTP client cho Google Gemini Vision API."""
from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from app.config import settings

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

GEMINI_MODELS = [
    {"id": "gemini-3.5-flash", "name": "Gemini 3.5 Flash"},
    {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash Lite"},
    {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
    {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
]
GEMINI_MODEL_IDS = {item["id"] for item in GEMINI_MODELS}


def _extract_text(payload: dict[str, Any]) -> str:
    try:
        return payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini trả về dữ liệu không có nội dung.") from exc


async def create_vision_completion(
    *,
    api_key: str,
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    model: str,
) -> str:
    image_data = base64.b64encode(image_bytes).decode("ascii")
    url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={api_key.strip()}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": image_data}},
                ]
            }
        ],
        "generationConfig": {"maxOutputTokens": settings.GEMINI_MAX_TOKENS},
    }

    async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
        response = await client.post(url, json=payload)

    if response.is_error:
        detail = response.text[:500]
        raise RuntimeError(f"Gemini HTTP {response.status_code}: {detail}")
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        preview = response.text[:500].strip()
        raise RuntimeError(
            f"Không thể giải mã JSON từ Gemini (HTTP {response.status_code}). "
            f"Phản hồi: {preview or '<rỗng>'}"
        ) from exc
    return _extract_text(data).strip()


async def test_single_key(key: str, model: str | None = None) -> dict:
    model = model or "gemini-3.5-flash"
    url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={key.strip()}"
    payload = {
        "contents": [{"parts": [{"text": "Reply with only the word: OK"}]}],
        "generationConfig": {"maxOutputTokens": 16},
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
        if response.is_error:
            return {"ok": False, "message": f"HTTP {response.status_code}: {response.text[:160]}"}
        try:
            data = response.json()
        except json.JSONDecodeError:
            return {"ok": False, "message": f"Không thể giải mã JSON (HTTP {response.status_code})"}
        text = _extract_text(data).strip()
        return {"ok": True, "message": f"Gemini phản hồi: {text[:50]}"}
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        return {"ok": False, "message": str(exc)[:200]}
