import pytest

from chatalchemy.sources.opentargets import OpenTargetsSource


class FakeOpenTargets(OpenTargetsSource):
    def __init__(self):
        self.queries = []
        self._owns = False

    async def _post_json(self, url, payload, attempts=3):
        self.queries.append(payload)
        query = payload["query"]
        if "query Search" in query:
            assert "entityNames" not in query
            assert "entities" not in payload["variables"]
            return {
                "data": {
                    "search": {
                        "hits": [
                            {
                                "id": "ENSG00000146648",
                                "entity": "target",
                                "name": "EGFR",
                                "description": "epidermal growth factor receptor",
                                "score": 12.0,
                            },
                            {
                                "id": "EFO_0003060",
                                "entity": "disease",
                                "name": "non-small cell lung carcinoma",
                                "description": "NSCLC",
                                "score": 20.0,
                            },
                        ]
                    }
                }
            }
        assert "associatedTargets(" in query
        assert 'orderByScore: "score desc"' in query
        assert "enableIndirect: true" in query
        assert payload["variables"]["id"] == "EFO_0003060"
        return {
            "data": {
                "disease": {
                    "id": "EFO_0003060",
                    "name": "non-small cell lung carcinoma",
                    "associatedTargets": {
                        "rows": [
                            {
                                "target": {
                                    "id": "ENSG00000146648",
                                    "approvedSymbol": "EGFR",
                                    "approvedName": "epidermal growth factor receptor",
                                },
                                "score": 0.91,
                            }
                        ]
                    },
                }
            }
        }

    async def close(self):
        return None


class GraphQLErrorOpenTargets(OpenTargetsSource):
    def __init__(self):
        self._owns = False

    async def _post_json(self, url, payload, attempts=3):
        return {
            "data": {"disease": None},
            "errors": [{"message": "Invalid association ordering"}],
        }

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_disease_genes_uses_current_association_query():
    source = FakeOpenTargets()
    rows = await source.disease_genes("non-small-cell lung cancer", max_results=20)
    assert len(rows) == 1
    assert rows[0].predicate == "disease_gene_association"
    assert rows[0].value == "EGFR"
    assert rows[0].qualifiers["efo_id"] == "EFO_0003060"
    assert rows[0].qualifiers["include_indirect"] is True
    assert rows[0].source_record_id == "ENSG00000146648"
    assert len(source.queries) >= 2


@pytest.mark.asyncio
async def test_graphql_200_with_errors_is_not_reported_as_valid_empty_result():
    source = GraphQLErrorOpenTargets()
    with pytest.raises(RuntimeError, match="Open Targets GraphQL error"):
        await source.disease_genes("non-small-cell lung cancer", max_results=20)
