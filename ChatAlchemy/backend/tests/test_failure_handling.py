import pytest

from chatalchemy.reasoning import ChatAlchemyEngine
from chatalchemy.sources.base import LiveSource
from chatalchemy.sources.openfda import OpenFDASource


class FailingFDA(LiveSource):
    name = "Drugs@FDA/openFDA"

    async def approval_records(self, drug: str, max_results: int = 20):
        raise RuntimeError("simulated 503")


class FailingSearchFDA(OpenFDASource):
    """Exercise the real adapter's fallback loop when every upstream call fails."""

    def __init__(self):
        self._owns_client = False

    async def _get(self, *args, **kwargs):
        raise RuntimeError("simulated upstream outage")

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_source_failure_is_exposed_not_hallucinated():
    engine = ChatAlchemyEngine(sources={"openfda": FailingFDA()})
    try:
        response = await engine.answer("What FDA approval information is available for pembrolizumab?")
    finally:
        await engine.close()

    assert any(not t.ok for t in response.traces)
    assert any("failed during" in w.lower() for w in response.warnings)
    assert "No Drugs@FDA/openFDA application records" in response.answer
    assert not response.claims


@pytest.mark.asyncio
async def test_adapter_does_not_convert_total_upstream_failure_into_zero_records():
    engine = ChatAlchemyEngine(sources={"openfda": FailingSearchFDA()})
    try:
        response = await engine.answer("What FDA approval information is available for pembrolizumab?")
    finally:
        await engine.close()

    assert response.traces
    assert response.traces[0].ok is False
    assert response.traces[0].result_count == 0
    assert "simulated upstream outage" in (response.traces[0].error or "")
    assert any("failed during approval_records" in warning for warning in response.warnings)
    assert not response.claims
