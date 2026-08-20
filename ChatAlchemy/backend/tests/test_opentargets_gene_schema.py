import pytest

from chatalchemy.benchmark import LiveOracle
from chatalchemy.sources.opentargets import OpenTargetsSource


class FakeOpenTargets(OpenTargetsSource):
    def __init__(self):
        self._owns_client = False
        self.queries = []

    async def _post_json(self, url, payload, attempts=3):
        query = payload["query"]
        self.queries.append(query)
        if "query Search" in query:
            return {
                "data": {
                    "search": {
                        "hits": [
                            {
                                "id": "ENSG00000146648",
                                "entity": "target",
                                "name": "EGFR",
                                "description": "epidermal growth factor receptor",
                                "score": 100.0,
                            }
                        ]
                    }
                }
            }
        if "query Target" in query:
            return {
                "data": {
                    "target": {
                        "id": "ENSG00000146648",
                        "approvedSymbol": "EGFR",
                        "approvedName": "epidermal growth factor receptor",
                        "associatedDiseases": {
                            "rows": [
                                {
                                    "disease": {"id": "EFO_0003060", "name": "non-small cell lung carcinoma"},
                                    "score": 0.91,
                                }
                            ]
                        },
                        "drugAndClinicalCandidates": {
                            "rows": [
                                {
                                    "id": "candidate-hash",
                                    "drug": {"id": "CHEMBL3353410", "name": "OSIMERTINIB"},
                                    "maxClinicalStage": "Phase IV",
                                    "diseases": [
                                        {
                                            "diseaseId": "EFO_0003060",
                                            "diseaseFromSource": "non-small cell lung cancer",
                                        }
                                    ],
                                }
                            ]
                        },
                    }
                }
            }
        raise AssertionError(query)

    async def close(self):
        return None


class FakeDirectOracle(LiveOracle):
    def __init__(self):
        self.client = None
        self.queries = []

    async def _ot_search_id(self, query_text: str, entity: str):
        assert query_text == "EGFR"
        assert entity == "target"
        return "ENSG00000146648"

    async def _post(self, url, query, variables):
        self.queries.append(query)
        return {
            "data": {
                "target": {
                    "id": "ENSG00000146648",
                    "approvedSymbol": "EGFR",
                    "associatedDiseases": {
                        "rows": [
                            {
                                "disease": {"id": "EFO_0003060", "name": "non-small cell lung carcinoma"},
                                "score": 0.91,
                            }
                        ]
                    },
                    "drugAndClinicalCandidates": {
                        "rows": [
                            {
                                "id": "candidate-hash",
                                "drug": {"id": "CHEMBL3353410", "name": "OSIMERTINIB"},
                                "maxClinicalStage": "Phase IV",
                                "diseases": [],
                            }
                        ]
                    },
                }
            }
        }

    async def close(self):
        return None


def _candidate_query(queries):
    return next(query for query in queries if "drugAndClinicalCandidates" in query)


@pytest.mark.asyncio
async def test_product_gene_query_uses_current_graphql_drug_object():
    source = FakeOpenTargets()
    rows = await source.gene_details("EGFR", max_results=10)

    query = _candidate_query(source.queries)
    assert "drug { id name }" in " ".join(query.split())
    assert "drugId" not in query
    assert "targetId" not in query

    assert any(row.predicate == "gene_disease_association" for row in rows)
    drug = next(row for row in rows if row.predicate == "known_drug")
    assert drug.value == "OSIMERTINIB"
    assert drug.source_record_id == "CHEMBL3353410"
    assert drug.qualifiers["chembl_id"] == "CHEMBL3353410"


@pytest.mark.asyncio
async def test_direct_oracle_gene_query_uses_same_public_schema_independently():
    oracle = FakeDirectOracle()
    values, records = await oracle._gene("EGFR", limit=10)

    query = _candidate_query(oracle.queries)
    assert "drug { id name }" in " ".join(query.split())
    assert "drugId" not in query
    assert "targetId" not in query
    assert "gene_disease_association:non-small cell lung carcinoma" in values
    assert "known_drug:osimertinib" in values
    assert any(record["record"] == "CHEMBL3353410" for record in records)
