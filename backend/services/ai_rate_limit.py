"""Small per-process Bedrock concurrency/cooldown guard for the MVP."""
from __future__ import annotations

import asyncio
import time


class BedrockRateLimiter:
    def __init__(self, cooldown_seconds: float = 2.0) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._lock = asyncio.Lock()
        self._active: set[int] = set()
        self._last_done: dict[int, float] = {}

    async def acquire(self, user_id: int) -> tuple[bool, int]:
        async with self._lock:
            now = time.monotonic()
            if user_id in self._active:
                return False, 1
            remaining = self.cooldown_seconds - (now - self._last_done.get(user_id, -1e9))
            if remaining > 0:
                return False, max(1, int(remaining + 0.999))
            self._active.add(user_id)
            return True, 0

    async def release(self, user_id: int) -> None:
        async with self._lock:
            self._active.discard(user_id)
            self._last_done[user_id] = time.monotonic()

    async def reset(self) -> None:
        async with self._lock:
            self._active.clear()
            self._last_done.clear()


bedrock_rate_limiter = BedrockRateLimiter()
