from __future__ import annotations

import asyncio
import re
import time
from typing import Awaitable, TypeVar

import httpx

from ..models import SourceTrace

T = TypeVar("T")

_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key=)[^&\s]+"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+"),
)


def _safe_error(exc: Exception) -> str:
    """Return a useful trace error without exposing request URLs or secrets."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTPStatusError: upstream returned HTTP {exc.response.status_code}"
    if isinstance(exc, httpx.RequestError):
        return f"{type(exc).__name__}: upstream request failed"

    text = str(exc).replace("\n", " ").strip()
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(r"\1[REDACTED]", text)
    if len(text) > 500:
        text = text[:497] + "..."
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


class LiveSource:
    name = "source"

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(18.0),
            follow_redirects=True,
            headers={"User-Agent": "ChatAlchemy-Live/1.0", "Accept": "application/json"},
        )

    async def close(self):
        if self._owns_client:
            await self.client.aclose()

    async def _get(self, url: str, params: dict | None = None, attempts: int = 3):
        last: Exception | None = None
        for attempt in range(attempts):
            try:
                response = await self.client.get(url, params=params)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < attempts - 1:
                    await asyncio.sleep(0.35 * (2**attempt))
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last = exc
                if attempt < attempts - 1:
                    await asyncio.sleep(0.2 * (2**attempt))
        assert last is not None
        raise last

    async def _post_json(self, url: str, payload: dict, attempts: int = 3):
        last: Exception | None = None
        for attempt in range(attempts):
            try:
                response = await self.client.post(url, json=payload)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < attempts - 1:
                    await asyncio.sleep(0.35 * (2**attempt))
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last = exc
                if attempt < attempts - 1:
                    await asyncio.sleep(0.2 * (2**attempt))
        assert last is not None
        raise last

    async def traced(self, operation: str, awaitable: Awaitable[list[T]]) -> tuple[list[T], SourceTrace]:
        start = time.perf_counter()
        try:
            rows = await awaitable
            return rows, SourceTrace(
                source=self.name,
                operation=operation,
                ok=True,
                latency_ms=(time.perf_counter() - start) * 1000,
                result_count=len(rows),
            )
        except Exception as exc:
            return [], SourceTrace(
                source=self.name,
                operation=operation,
                ok=False,
                latency_ms=(time.perf_counter() - start) * 1000,
                result_count=0,
                error=_safe_error(exc),
            )
