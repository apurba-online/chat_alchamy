import httpx
import pytest

from chatalchemy.benchmark import LiveOracle


class FakeOracle(LiveOracle):
    def __init__(self):
        self.client = None
        self.calls = []

    async def _post(self, url, query, variables):
        self.calls.append((url, query, variables))
        return {
            "data": {
                "search": {
                    "hits": [
                        {
                            "id": "EFO_0003060",
                            "entity": "disease",
                            "name": "non-small cell lung carcinoma",
                            "description": "NSCLC",
                            "score": 30.0,
                        },
                        {
                            "id": "ENSG00000146648",
                            "entity": "target",
                            "name": "EGFR",
                            "description": "epidermal growth factor receptor",
                            "score": 40.0,
                        },
                    ]
                }
            }
        }

    async def close(self):
        return None


class FailedFDAOracle(LiveOracle):
    def __init__(self):
        self.client = None

    async def _get(self, *args, **kwargs):
        raise RuntimeError("FDA unavailable")

    async def close(self):
        return None


class EmptyFDAOracle(LiveOracle):
    def __init__(self):
        self.client = None

    async def _get(self, *args, **kwargs):
        return {"results": []}

    async def close(self):
        return None


class NoMatch404FDAOracle(LiveOracle):
    def __init__(self):
        self.client = None

    async def _get(self, url, *args, **kwargs):
        request = httpx.Request("GET", url)
        response = httpx.Response(
            404,
            request=request,
            json={"error": {"code": "NOT_FOUND", "message": "No matches found!"}},
        )
        raise httpx.HTTPStatusError("not found", request=request, response=response)

    async def close(self):
        return None


class Broken404FDAOracle(LiveOracle):
    def __init__(self):
        self.client = None

    async def _get(self, url, *args, **kwargs):
        request = httpx.Request("GET", url)
        response = httpx.Response(
            404,
            request=request,
            json={"error": {"code": "NOT_FOUND", "message": "Endpoint missing"}},
        )
        raise httpx.HTTPStatusError("not found", request=request, response=response)

    async def close(self):
        return None


class FailedMechanismOracle(LiveOracle):
    def __init__(self):
        self.client = None

    async def _get(self, url, *args, **kwargs):
        if url.endswith("/target/search.json"):
            return {
                "targets": [
                    {
                        "target_chembl_id": "CHEMBL203",
                        "pref_name": "Epidermal growth factor receptor",
                        "organism": "Homo sapiens",
                        "target_type": "SINGLE PROTEIN",
                    }
                ]
            }
        if url.endswith("/mechanism.json"):
            raise RuntimeError("ChEMBL mechanism service unavailable")
        raise AssertionError(url)

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_direct_oracle_search_filters_entity_type_locally():
    oracle = FakeOracle()
    target_id = await oracle._ot_search_id("EGFR", "target")
    disease_id = await oracle._ot_search_id("non-small cell lung carcinoma", "disease")

    assert target_id == "ENSG00000146648"
    assert disease_id == "EFO_0003060"
    assert oracle.calls
    assert all("entityNames" not in query for _, query, _ in oracle.calls)


@pytest.mark.asyncio
async def test_direct_oracle_complete_fda_outage_is_unavailable_not_empty_gold():
    oracle = FailedFDAOracle()
    with pytest.raises(RuntimeError, match="FDA unavailable"):
        await oracle._approvals("pembrolizumab")


@pytest.mark.asyncio
async def test_direct_oracle_successful_empty_fda_response_remains_valid_empty_gold():
    oracle = EmptyFDAOracle()
    values, records = await oracle._approvals("definitely-not-a-drug")
    assert values == []
    assert records == []


@pytest.mark.asyncio
async def test_direct_oracle_openfda_no_match_404_is_valid_empty_gold():
    oracle = NoMatch404FDAOracle()
    values, records = await oracle._approvals("definitely-not-a-drug")
    assert values == []
    assert records == []


@pytest.mark.asyncio
async def test_direct_oracle_other_openfda_404_is_unavailable():
    oracle = Broken404FDAOracle()
    with pytest.raises(httpx.HTTPStatusError):
        await oracle._approvals("pembrolizumab")


@pytest.mark.asyncio
async def test_direct_oracle_complete_chembl_mechanism_outage_is_unavailable():
    oracle = FailedMechanismOracle()
    with pytest.raises(RuntimeError, match="ChEMBL mechanism service unavailable"):
        await oracle._target_drugs("EGFR")
