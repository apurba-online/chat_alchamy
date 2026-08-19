from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx


class SourceError(RuntimeError):
    pass


class LiveSource:
    name = "source"

    def __init__(self, client: httpx.AsyncClient, *, min_interval: float = 0.0, retries: int = 2):
        self.client = client
        self.min_interval = min_interval
        self.retries = retries
        self._last_call = 0.0
        self._lock = asyncio.Lock()

    async def _throttle(self) -> None:
        if self.min_interval <= 0:
            return
        async with self._lock:
            elapsed = time.monotonic() - self._last_call
            wait = self.min_interval - elapsed
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()

    async def get_json(self, url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            await self._throttle()
            try:
                response = await self.client.get(url, params=params, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
                if response.status_code == 404:
                    return {}
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.retries:
                        await asyncio.sleep(0.5 * (2**attempt))
                        continue
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self.retries:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
        raise SourceError(f"{self.name} request failed: {last_error}")
