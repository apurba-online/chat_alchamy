from __future__ import annotations

from typing import Any


class FaultInjectedSource:
    """Proxy a live source while deterministically perturbing selected operations.

    This is evaluation-only. It never modifies an upstream API or cached source data.
    """

    def __init__(self, source: Any, *, fail_methods: set[str], mode: str = "exception"):
        if mode not in {"exception", "empty"}:
            raise ValueError("mode must be 'exception' or 'empty'")
        self._source = source
        self.fail_methods = set(fail_methods)
        self.mode = mode
        self.name = getattr(source, "name", source.__class__.__name__)

    async def close(self):
        return await self._source.close()

    async def traced(self, operation: str, coro):
        return await self._source.traced(operation, coro)

    def __getattr__(self, name: str):
        attr = getattr(self._source, name)
        if not callable(attr) or name in {"close", "traced"}:
            return attr

        async def wrapped(*args, **kwargs):
            if name in self.fail_methods:
                if self.mode == "empty":
                    return []
                raise RuntimeError(f"injected failure for {self.name}.{name}")
            return await attr(*args, **kwargs)

        return wrapped
