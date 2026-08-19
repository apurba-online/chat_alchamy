import pytest

from chatalchemy.reasoning import ChatAlchemyEngine
from chatalchemy.sources.base import LiveSource


class FailingFDA(LiveSource):
    name = "Drugs@FDA/openFDA"

    async def approval_records(self, drug: str, max_results: int = 20):
        raise RuntimeError("simulated 503")


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
