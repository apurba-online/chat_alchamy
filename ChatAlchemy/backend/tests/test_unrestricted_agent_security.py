import httpx
import pytest

from chatalchemy.evaluation import UnrestrictedToolAgent


class FakeLLM:
    def __init__(self):
        self.calls = 0
        self.last_usage = {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}

    async def json(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return {
                "done": False,
                "tool": "openfda",
                "drug": "aspirin",
                "target": None,
                "condition": None,
                "phase": None,
                "status": None,
                "gene": None,
                "compound": None,
                "reason": "check FDA records",
            }
        return {
            "done": True,
            "tool": "none",
            "drug": None,
            "target": None,
            "condition": None,
            "phase": None,
            "status": None,
            "gene": None,
            "compound": None,
            "reason": "done",
        }


class SecretFailingFDA:
    async def approval_records(self, drug: str, max_results: int = 20):
        request = httpx.Request("GET", "https://api.fda.gov/drug/drugsfda.json?api_key=secret-value")
        response = httpx.Response(503, request=request)
        raise httpx.HTTPStatusError(
            "failure at https://api.fda.gov/drug/drugsfda.json?api_key=secret-value",
            request=request,
            response=response,
        )


@pytest.mark.asyncio
async def test_unrestricted_agent_error_trace_does_not_store_api_key():
    agent = UnrestrictedToolAgent(FakeLLM(), {"openfda": SecretFailingFDA()}, max_steps=2)
    result = await agent.retrieve("Does aspirin have FDA records?")

    assert result["trace"][0]["ok"] is False
    error = result["trace"][0]["error"]
    assert error == "HTTPStatusError: upstream returned HTTP 503"
    assert "secret-value" not in error
    assert "api_key=" not in error
