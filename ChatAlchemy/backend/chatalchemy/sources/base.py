from __future__ import annotations

import asyncio
import time
from typing import Any
import httpx


class SourceError(RuntimeError):
    pass


class BaseSource:
    name = "base"

    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 20.0):
        self._external_client = client
        self.timeout = timeout

    async def _request_json(self, method: str, url: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None, retries: int = 2) -> tuple[Any, float]:
        headers = {"Accept": "application/json", "Cache-Control": "no-cache", "Pragma": "no-cache"}
        client = self._external_client or httpx.AsyncClient(timeout=self.timeout, headers=headers)
        close = self._external_client is None
        try:
            last: Exception | None = None
            for attempt in range(retries + 1):
                started = time.perf_counter()
                try:
                    response = await client.request(method, url, params=params, json=json, headers=headers)
                    latency = (time.perf_counter() - started) * 1000
                    if response.status_code == 429 or response.status_code >= 500:
                        raise SourceError(f"HTTP {response.status_code} from {self.name}")
                    response.raise_for_status()
                    return response.json(), latency
                except Exception as exc:
                    last = exc
                    if attempt < retries:
                        await asyncio.sleep(0.25 * (2 ** attempt))
            raise SourceError(str(last) if last else f"Unknown {self.name} error")
        finally:
            if close:
                await client.aclose()
