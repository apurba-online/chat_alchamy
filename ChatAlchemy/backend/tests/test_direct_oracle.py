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


@pytest.mark.asyncio
async def test_direct_oracle_search_filters_entity_type_locally():
    oracle = FakeOracle()
    target_id = await oracle._ot_search_id("EGFR", "target")
    disease_id = await oracle._ot_search_id("non-small cell lung carcinoma", "disease")

    assert target_id == "ENSG00000146648"
    assert disease_id == "EFO_0003060"
    assert oracle.calls
    assert all("entityNames" not in query for _, query, _ in oracle.calls)
