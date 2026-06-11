"""HTTP client cho 9router qua API tương thích OpenAI Chat Completions."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.services.gemini_client import GEMINI_MODELS, GEMINI_MODEL_IDS

NINEROUTER_MODELS = [
    {"id": "cx/gpt-5.5", "name": "GPT-5.5"},
    {"id": "cx/gpt-5.4", "name": "GPT-5.4"},
    {"id": "cx/gpt-5.3-codex", "name": "GPT-5.3 Codex"},
    {"id": "cx/gpt-5.3-codex-high", "name": "GPT-5.3 Codex High"},
    {"id": "cx/gpt-5.3-codex-xhigh", "name": "GPT-5.3 Codex Xhigh"},
    {"id": "openclaw-edutechnd-org", "name": "OpenClaw EduTechND Org"},
]
NINEROUTER_MODEL_IDS = {item["id"] for item in NINEROUTER_MODELS}

ALL_PROVIDERS = [
    {
        "id": "9router",
        "name": "9router (OpenAI compatible)",
        "models": NINEROUTER_MODELS,
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "models": GEMINI_MODELS,
    },
]
_ALL_MODEL_IDS: dict[str, set[str]] = {
    "9router": NINEROUTER_MODEL_IDS,
    "gemini": GEMINI_MODEL_IDS,
}


class ProviderConfig:
    def __init__(self, path: Path, default_provider: str, default_model: str) -> None:
        self.path = path
        self.provider = default_provider
        self.model = default_model
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            provider = str(data.get("provider", "")).strip()
            model = str(data.get("model", "")).strip()
            if provider in _ALL_MODEL_IDS and model in _ALL_MODEL_IDS[provider]:
                self.provider = provider
                self.model = model
            elif model and model in NINEROUTER_MODEL_IDS:
                # backward compat: file cũ không có trường provider
                self.provider = "9router"
                self.model = model
        except (OSError, ValueError, TypeError):
            return

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"provider": self.provider, "model": self.model},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def set_provider(self, provider: str, model: str) -> None:
        provider = provider.strip()
        model = model.strip()
        if provider not in _ALL_MODEL_IDS:
            raise ValueError(f"Provider '{provider}' không được hỗ trợ.")
        if model not in _ALL_MODEL_IDS[provider]:
            raise ValueError(f"Model '{model}' không thuộc provider '{provider}'.")
        self.provider = provider
        self.model = model
        self._save()

    def set_model(self, model: str) -> str:
        """Backward-compat: chỉ đổi model trong 9router."""
        model = model.strip()
        if model not in NINEROUTER_MODEL_IDS:
            raise ValueError("Model 9router không được hỗ trợ.")
        self.provider = "9router"
        self.model = model
        self._save()
        return model

    def public_config(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "base_url": settings.NINEROUTER_BASE_URL,
            "model": self.model,
            "models": NINEROUTER_MODELS,
            "providers": ALL_PROVIDERS,
        }


provider_config = ProviderConfig(
    settings.PROVIDER_CONFIG_FILE,
    "9router",
    settings.NINEROUTER_MODEL,
)


def _chat_completions_url() -> str:
    return f"{settings.NINEROUTER_BASE_URL.rstrip('/')}/chat/completions"


def _extract_text(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("9router trả về dữ liệu không có nội dung.") from exc

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
        )
    raise RuntimeError("9router trả về content không đúng định dạng.")


async def create_vision_completion(
    *,
    api_key: str,
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
) -> str:
    image_data = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": provider_config.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}",
                        },
                    },
                ],
            }
        ],
        "max_tokens": settings.NINEROUTER_MAX_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=settings.NINEROUTER_TIMEOUT_SECONDS) as client:
        response = await client.post(
            _chat_completions_url(),
            headers=headers,
            json=payload,
        )
    if response.is_error:
        detail = response.text[:500]
        raise RuntimeError(f"9router HTTP {response.status_code}: {detail}")
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        preview = response.text[:500].strip()
        raise RuntimeError(
            f"Không thể giải mã JSON từ 9router (HTTP {response.status_code}). "
            f"Phản hồi: {preview or '<rỗng>'}"
        ) from exc
    return _extract_text(data).strip()


async def test_single_key(key: str, model: str | None = None) -> dict:
    payload = {
        "model": model or provider_config.model,
        "messages": [
            {"role": "user", "content": "Reply with only the word: OK"}
        ],
        "max_tokens": 16,
    }
    headers = {
        "Authorization": f"Bearer {key.strip()}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _chat_completions_url(),
                headers=headers,
                json=payload,
            )
        if response.is_error:
            return {
                "ok": False,
                "message": f"HTTP {response.status_code}: {response.text[:160]}",
            }
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            preview = response.text[:160].strip()
            return {
                "ok": False,
                "message": f"Không thể giải mã JSON từ 9router (HTTP {response.status_code}). Phản hồi: {preview or '<rỗng>'}",
            }
        text = _extract_text(data).strip()
        return {"ok": True, "message": f"9router phản hồi: {text[:50]}"}
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        return {"ok": False, "message": str(exc)[:200]}
