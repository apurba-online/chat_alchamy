import httpx
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


class NoMatchFDA(OpenFDASource):
    """openFDA encodes a legitimate zero-match search as a 404 error payload."""

    def __init__(self):
        self._owns_client = False

    async def _get(self, url, *, params=None, attempts=3):
        request = httpx.Request("GET", url, params=params)
        response = httpx.Response(
            404,
            request=request,
            json={"error": {"code": "NOT_FOUND", "message": "No matches found!"}},
        )
        raise httpx.HTTPStatusError("not found", request=request, response=response)

    async def close(self):
        return None


class Broken404FDA(OpenFDASource):
    """A different 404 shape is a real failure, not evidence of no records."""

    def __init__(self):
        self._owns_client = False

    async def _get(self, url, *, params=None, attempts=3):
        request = httpx.Request("GET", url, params=params)
        response = httpx.Response(
            404,
            request=request,
            json={"error": {"code": "NOT_FOUND", "message": "Endpoint does not exist"}},
        )
        raise httpx.HTTPStatusError("not found", request=request, response=response)

    async def close(self):
        return None


class SecretURLSource(LiveSource):
    name = "SecretTest"

    async def records(self):
        request = httpx.Request("GET", "https://example.invalid/data?api_key=super-secret-value&q=test")
        response = httpx.Response(503, request=request)
        raise httpx.HTTPStatusError(
            "service unavailable for https://example.invalid/data?api_key=super-secret-value&q=test",
            request=request,
            response=response,
        )


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
async def test_openfda_no_matches_404_is_a_valid_empty_result():
    engine = ChatAlchemyEngine(sources={"openfda": NoMatchFDA()})
    try:
        response = await engine.answer("What FDA approval information is available for madeupdrugxyz?")
    finally:
        await engine.close()

    assert response.traces and response.traces[0].ok is True
    assert response.traces[0].result_count == 0
    assert "No Drugs@FDA/openFDA application records" in response.answer
    assert not response.warnings
    assert not response.claims


@pytest.mark.asyncio
async def test_non_no_match_openfda_404_remains_a_source_failure():
    engine = ChatAlchemyEngine(sources={"openfda": Broken404FDA()})
    try:
        response = await engine.answer("What FDA approval information is available for pembrolizumab?")
    finally:
        await engine.close()

    assert response.traces and response.traces[0].ok is False
    assert "HTTPStatusError" in (response.traces[0].error or "")
    assert "no conclusion about the absence" in response.answer.lower()
    assert "no drugs@fda/openfda application records" not in response.answer.lower()


@pytest.mark.asyncio
async def test_source_trace_http_error_does_not_expose_request_api_key():
    source = SecretURLSource()
    try:
        rows, trace = await source.traced("records", source.records())
    finally:
        await source.close()

    assert rows == []
    assert trace.ok is False
    assert trace.error == "HTTPStatusError: upstream returned HTTP 503"
    assert "super-secret-value" not in trace.error
    assert "api_key=" not in trace.error


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
