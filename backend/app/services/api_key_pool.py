"""Pool quản lý nhiều API key với failover, persistence và hot-reload."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class KeyState(str, Enum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID = "invalid"


@dataclass
class ApiKey:
    key: str
    index: int
    state: KeyState = KeyState.ACTIVE
    cooldown_until: float = 0.0
    used_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_error: str = ""
    semaphore: Optional[asyncio.Semaphore] = field(default=None, repr=False)

    @property
    def preview(self) -> str:
        if len(self.key) <= 12:
            return self.key
        return f"{self.key[:6]}...{self.key[-4:]}"

    @property
    def cooldown_remaining(self) -> float:
        return max(0.0, self.cooldown_until - time.time())


class ApiKeyPool:
    """Pool API key dùng chung cho các provider HTTP."""

    def __init__(
        self,
        keys: list[str],
        max_concurrent_per_key: int = 3,
        persist_path: Optional[Path] = None,
    ) -> None:
        self._max_concurrent = max_concurrent_per_key
        self._persist_path = persist_path
        self._cursor = 0
        self._lock = asyncio.Lock()
        self._keys: list[ApiKey] = []
        self._build_keys(keys)
        logger.info("Pool khởi tạo với %d key (max_concurrent_per_key=%d)",
                    len(self._keys), max_concurrent_per_key)

    def _build_keys(self, keys: list[str]) -> None:
        self._keys = [
            ApiKey(key=k.strip(), index=i, semaphore=asyncio.Semaphore(self._max_concurrent))
            for i, k in enumerate(keys) if k.strip()
        ]

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps({"keys": [k.key for k in self._keys]}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Không lưu được keys vào %s", self._persist_path)

    @classmethod
    def load_keys_from_file(cls, path: Path) -> list[str]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [k for k in data.get("keys", []) if isinstance(k, str) and k.strip()]
        except Exception:
            logger.exception("Không đọc được %s", path)
            return []

    async def acquire(self, wait_timeout: float = 300.0) -> ApiKey:
        if not self._keys:
            raise RuntimeError("Pool chưa có API key nào. Vào trang Admin để thêm.")

        start = time.time()
        while True:
            now = time.time()
            async with self._lock:
                for k in self._keys:
                    if k.state in (KeyState.RATE_LIMITED, KeyState.QUOTA_EXCEEDED) and now >= k.cooldown_until:
                        k.state = KeyState.ACTIVE
                candidates = [k for k in self._keys if k.state == KeyState.ACTIVE]
                if candidates:
                    self._cursor = (self._cursor + 1) % len(candidates)
                    chosen = candidates[self._cursor]
                    chosen.used_count += 1
                    return chosen
                invalid_count = sum(1 for k in self._keys if k.state == KeyState.INVALID)
                if invalid_count == len(self._keys):
                    raise RuntimeError("Tất cả key đều không hợp lệ. Cập nhật trong trang Admin.")
                next_cd = min(
                    (k.cooldown_until for k in self._keys
                     if k.state in (KeyState.RATE_LIMITED, KeyState.QUOTA_EXCEEDED)),
                    default=now + 30,
                )
                wait_for = max(1.0, min(next_cd - now, 10.0))

            if time.time() - start > wait_timeout:
                raise RuntimeError("Timeout đợi key khả dụng.")
            logger.warning("Tất cả key đang cooldown, đợi %.1fs", wait_for)
            await asyncio.sleep(wait_for)

    async def report_success(self, key: ApiKey) -> None:
        async with self._lock:
            key.success_count += 1
            key.error_count = 0
            key.last_error = ""

    async def report_error(self, key: ApiKey, exc: Exception) -> None:
        msg = str(exc)
        m = msg.lower()
        async with self._lock:
            key.error_count += 1
            key.last_error = msg[:200]
            if any(s in m for s in ("permission denied", "api key not valid", "invalid api key", "401", "403")):
                key.state = KeyState.INVALID
                logger.error("Key %s INVALID: %s", key.preview, msg[:100])
            elif "quota" in m and ("exceeded" in m or "exhausted" in m):
                key.state = KeyState.QUOTA_EXCEEDED
                key.cooldown_until = time.time() + 6 * 3600
                logger.warning("Key %s QUOTA_EXCEEDED 6h", key.preview)
            elif "429" in msg or "resource_exhausted" in m or "rate" in m:
                key.state = KeyState.RATE_LIMITED
                key.cooldown_until = time.time() + 60
                logger.warning("Key %s RATE_LIMITED 60s", key.preview)

    # ============ CRUD ============

    async def replace_all(self, keys: list[str]) -> int:
        """Thay toàn bộ danh sách key (giữ semaphore mặc định)."""
        clean = [k.strip() for k in keys if k.strip()]
        async with self._lock:
            self._build_keys(clean)
            self._cursor = 0
            self._persist()
        logger.info("Pool replace_all → %d key", len(clean))
        return len(clean)

    async def add_key(self, key: str) -> int:
        key = key.strip()
        if not key:
            raise ValueError("Key rỗng.")
        async with self._lock:
            if any(k.key == key for k in self._keys):
                raise ValueError("Key đã tồn tại trong pool.")
            self._keys.append(ApiKey(
                key=key, index=len(self._keys),
                semaphore=asyncio.Semaphore(self._max_concurrent),
            ))
            self._persist()
        return len(self._keys)

    async def remove_key(self, index: int) -> int:
        async with self._lock:
            if not (0 <= index < len(self._keys)):
                raise ValueError(f"Index {index} không hợp lệ.")
            removed = self._keys.pop(index)
            for i, k in enumerate(self._keys):
                k.index = i
            self._persist()
        logger.info("Đã xoá key %s", removed.preview)
        return len(self._keys)

    async def reset_key(self, index: int) -> None:
        """Reset state về ACTIVE (dùng khi muốn thử lại key bị cooldown ngay)."""
        async with self._lock:
            if not (0 <= index < len(self._keys)):
                raise ValueError(f"Index {index} không hợp lệ.")
            k = self._keys[index]
            k.state = KeyState.ACTIVE
            k.cooldown_until = 0
            k.error_count = 0
            k.last_error = ""

    def stats(self) -> dict:
        return {
            "total": len(self._keys),
            "active": sum(1 for k in self._keys if k.state == KeyState.ACTIVE),
            "rate_limited": sum(1 for k in self._keys if k.state == KeyState.RATE_LIMITED),
            "quota_exceeded": sum(1 for k in self._keys if k.state == KeyState.QUOTA_EXCEEDED),
            "invalid": sum(1 for k in self._keys if k.state == KeyState.INVALID),
            "keys": [
                {
                    "index": k.index,
                    "preview": k.preview,
                    "state": k.state.value,
                    "used": k.used_count,
                    "success": k.success_count,
                    "errors": k.error_count,
                    "last_error": k.last_error,
                    "cooldown_remaining": round(k.cooldown_remaining, 1),
                }
                for k in self._keys
            ],
        }


_pool: Optional[ApiKeyPool] = None


def init_pool(keys: list[str], max_concurrent_per_key: int = 3,
              persist_path: Optional[Path] = None) -> ApiKeyPool:
    global _pool
    _pool = ApiKeyPool(keys, max_concurrent_per_key, persist_path)
    return _pool


def get_pool() -> ApiKeyPool:
    if _pool is None:
        raise RuntimeError("Pool chưa init.")
    return _pool
