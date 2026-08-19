import time

import pytest

from chatalchemy.evaluation import FaultInjectedSource
from chatalchemy.models import SourceTrace


class DummySource:
    name = "Dummy"

    async def close(self):
        return None

    async def fetch(self):
        return ["ok"]

    async def traced(self, operation, coro):
        started = time.perf_counter()
        try:
            result = await coro
            return result, SourceTrace(source=self.name, operation=operation, ok=True, latency_ms=(time.perf_counter() - started) * 1000, result_count=len(result))
        except Exception as exc:
            return [], SourceTrace(source=self.name, operation=operation, ok=False, latency_ms=(time.perf_counter() - started) * 1000, result_count=0, error=str(exc))


@pytest.mark.asyncio
async def test_exception_fault_is_visible_in_source_trace():
    proxy = FaultInjectedSource(DummySource(), fail_methods={"fetch"}, mode="exception")
    result, trace = await proxy.traced("fetch", proxy.fetch())
    assert result == []
    assert not trace.ok
    assert "injected failure" in (trace.error or "")


@pytest.mark.asyncio
async def test_empty_fault_returns_empty_result_without_touching_upstream():
    proxy = FaultInjectedSource(DummySource(), fail_methods={"fetch"}, mode="empty")
    result, trace = await proxy.traced("fetch", proxy.fetch())
    assert result == []
    assert trace.ok
    assert trace.result_count == 0
