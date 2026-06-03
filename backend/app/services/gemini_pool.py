"""Pool quản lý nhiều API key Gemini với failover tự động.

State machine của mỗi key:
    ACTIVE ──429 (phút)──► RATE_LIMITED (cooldown 60s) ──hết hạn──► ACTIVE
    ACTIVE ──quota ngày──► QUOTA_EXCEEDED (cooldown 6h) ──hết hạn──► ACTIVE
    ACTIVE ──401/403────► INVALID (chết hẳn)

Chiến lược chọn key: round-robin trong các key ACTIVE, giới hạn số request
đồng thời mỗi key bằng asyncio.Semaphore để tránh vượt RPM của Gemini free
(15 req/phút/key cho gemini-2.0-flash).
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class KeyState(str, Enum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"          # 429 transient — đợi vài chục giây
    QUOTA_EXCEEDED = "quota_exceeded"       # quota ngày hết — đợi vài giờ
    INVALID = "invalid"                     # 401/403 — key chết, không retry


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


class GeminiKeyPool:
    """Pool quản lý nhiều API key với failover và load balancing."""

    def __init__(self, keys: list[str], max_concurrent_per_key: int = 3) -> None:
        if not keys:
            raise ValueError("Cần ít nhất 1 API key Gemini.")
        self._keys: list[ApiKey] = [
            ApiKey(
                key=k,
                index=i,
                semaphore=asyncio.Semaphore(max_concurrent_per_key),
            )
            for i, k in enumerate(keys)
        ]
        self._cursor = 0
        self._lock = asyncio.Lock()
        logger.info("Khởi tạo pool với %d key, max_concurrent_per_key=%d",
                    len(self._keys), max_concurrent_per_key)

    async def acquire(self, wait_timeout: float = 300.0) -> ApiKey:
        """Lấy 1 key khả dụng, đợi tối đa wait_timeout giây nếu tất cả đều cooldown.

        Raises:
            RuntimeError: nếu hết toàn bộ key hoặc timeout đợi.
        """
        start = time.time()
        backoff = 1.0
        while True:
            now = time.time()
            async with self._lock:
                # Refresh state: chuyển key đã hết cooldown về ACTIVE
                for k in self._keys:
                    if k.state in (KeyState.RATE_LIMITED, KeyState.QUOTA_EXCEEDED):
                        if now >= k.cooldown_until:
                            logger.info("Key %s hết cooldown, set ACTIVE", k.preview)
                            k.state = KeyState.ACTIVE

                # Lọc key dùng được
                candidates = [k for k in self._keys if k.state == KeyState.ACTIVE]

                if not candidates:
                    invalid_count = sum(1 for k in self._keys if k.state == KeyState.INVALID)
                    if invalid_count == len(self._keys):
                        raise RuntimeError(
                            f"Tất cả {len(self._keys)} key Gemini đều không hợp lệ. "
                            "Kiểm tra lại GEMINI_API_KEYS."
                        )
                    next_cooldown = min(
                        (k.cooldown_until for k in self._keys
                         if k.state in (KeyState.RATE_LIMITED, KeyState.QUOTA_EXCEEDED)),
                        default=now + 60,
                    )
                    wait_for = max(1.0, min(next_cooldown - now, 10.0))
                else:
                    # Round-robin: pick key tiếp theo trong danh sách candidates
                    self._cursor = (self._cursor + 1) % len(candidates)
                    chosen = candidates[self._cursor]
                    chosen.used_count += 1
                    return chosen

            if time.time() - start > wait_timeout:
                raise RuntimeError("Timeout đợi key Gemini khả dụng.")
            logger.warning("Tất cả key đang cooldown, đợi %.1fs", wait_for)
            await asyncio.sleep(wait_for)
            backoff = min(backoff * 1.5, 10.0)

    async def report_success(self, key: ApiKey) -> None:
        async with self._lock:
            key.success_count += 1
            key.error_count = 0
            key.last_error = ""

    async def report_error(self, key: ApiKey, exc: Exception) -> None:
        msg = str(exc)
        msg_lower = msg.lower()
        async with self._lock:
            key.error_count += 1
            key.last_error = msg[:200]

            # Phân loại lỗi
            if any(s in msg_lower for s in ("permission denied", "api key not valid",
                                             "invalid api key", "401", "403")):
                key.state = KeyState.INVALID
                logger.error("Key %s INVALID: %s", key.preview, msg[:120])
            elif "quota" in msg_lower and ("exceeded" in msg_lower or "exhausted" in msg_lower):
                key.state = KeyState.QUOTA_EXCEEDED
                key.cooldown_until = time.time() + 6 * 3600
                logger.warning("Key %s QUOTA_EXCEEDED, cooldown 6h", key.preview)
            elif "429" in msg or "resource_exhausted" in msg_lower or "rate" in msg_lower:
                key.state = KeyState.RATE_LIMITED
                # Nếu Gemini trả về retry-after, có thể parse, không thì 60s
                key.cooldown_until = time.time() + 60
                logger.warning("Key %s RATE_LIMITED, cooldown 60s", key.preview)
            else:
                # Lỗi khác không phải fault của key (network, server) — không cooldown
                logger.warning("Key %s lỗi tạm thời: %s", key.preview, msg[:120])

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


_pool: Optional[GeminiKeyPool] = None


def init_pool(keys: list[str], max_concurrent_per_key: int = 3) -> GeminiKeyPool:
    global _pool
    _pool = GeminiKeyPool(keys, max_concurrent_per_key)
    return _pool


def get_pool() -> GeminiKeyPool:
    if _pool is None:
        raise RuntimeError(
            "Gemini pool chưa khởi tạo. Đảm bảo GEMINI_API_KEYS được set trong .env."
        )
    return _pool
