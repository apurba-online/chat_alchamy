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


class FailingOpenTargets(LiveSource):
    name = "Open Targets"

    async def disease_genes(self, disease: str, max_results: int = 20):
        raise RuntimeError("simulated GraphQL execution error")


@pytest.mark.asyncio
async def test_source_failure_is_exposed_not_hallucinated():
    engine = ChatAlchemyEngine(sources={"openfda": FailingFDA()})
    try:
        response = await engine.answer("What FDA approval information is available for pembrolizumab?")
    finally:
        await engine.close()

    assert any(not trace.ok for trace in response.traces)
    assert any("failed during" in warning.lower() for warning in response.warnings)
    assert any("must not be interpreted as evidence of absence" in warning.lower() for warning in response.warnings)
    assert "could not complete the live biomedical query" in response.answer.lower()
    assert "no conclusion about the absence" in response.answer.lower()
    assert "no drugs@fda/openfda application records" not in response.answer.lower()
    assert not response.claims
    assert response.supported_claim_rate == 0.0


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
    assert "no conclusion about the absence" in response.answer.lower()
    assert "no drugs@fda/openfda application records" not in response.answer.lower()
    assert not response.claims
    assert response.supported_claim_rate == 0.0


@pytest.mark.asyncio
async def test_failed_disease_gene_query_is_not_reported_as_zero_associations():
    engine = ChatAlchemyEngine(sources={"opentargets": FailingOpenTargets()})
    try:
        response = await engine.answer("What genes are associated with non-small-cell lung cancer?")
    finally:
        await engine.close()

    assert response.plan.intent == "disease"
    assert response.traces and response.traces[0].ok is False
    assert "simulated GraphQL execution error" in (response.traces[0].error or "")
    assert "0 associated target gene" not in response.answer.lower()
    assert "no conclusion about the absence" in response.answer.lower()
    assert not response.claims
    assert response.supported_claim_rate == 0.0
