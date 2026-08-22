import pytest

from chatalchemy.sources.opentargets import OpenTargetsSource


class FakeOpenTargetsDisease(OpenTargetsSource):
    def __init__(self):
        self._owns_client = False
        self.queries = []

    async def _post_json(self, url, payload, attempts=3):
        query = payload["query"]
        self.queries.append(query)
        if "query DiseaseDetails" not in query:
            raise AssertionError(query)
        return {
            "data": {
                "disease": {
                    "id": "MONDO_0007179",
                    "name": "autoimmune disease",
                    "drugAndClinicalCandidates": {
                        "rows": [
                            {
                                "id": "candidate-1",
                                "maxClinicalStage": "Phase IV",
                                "drug": {"id": "CHEMBL1201576", "name": "TOFACITINIB"},
                            },
                            {
                                "id": "candidate-duplicate",
                                "maxClinicalStage": "Phase III",
                                "drug": {"id": "CHEMBL1201576", "name": "TOFACITINIB"},
                            },
                            {
                                "id": "candidate-2",
                                "maxClinicalStage": "Phase II",
                                "drug": {"id": "CHEMBL2105717", "name": "BARICITINIB"},
                            },
                        ]
                    },
                }
            }
        }

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_disease_details_uses_current_clinical_candidate_schema():
    source = FakeOpenTargetsDisease()
    result = await source.disease_details("MONDO_0007179")

    assert result is not None
    query = " ".join(source.queries[0].split())
    assert "drugAndClinicalCandidates" in query
    assert "drug { id name }" in query
    assert "knownDrugs" not in query

    assert result["id"] == "MONDO_0007179"
    assert result["name"] == "autoimmune disease"
    assert result["source"] == "Open Targets"
    assert result["source_url"].endswith("/MONDO_0007179")
    assert result["drugs"] == [
        {
            "id": "CHEMBL1201576",
            "name": "TOFACITINIB",
            "max_clinical_stage": "Phase IV",
        },
        {
            "id": "CHEMBL2105717",
            "name": "BARICITINIB",
            "max_clinical_stage": "Phase II",
        },
    ]
