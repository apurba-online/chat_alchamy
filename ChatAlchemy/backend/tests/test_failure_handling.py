import pytest

from chatalchemy.models import Entity, EvidenceItem
from chatalchemy.reasoning import ChatAlchemyEngine

class GoodRxNorm:
    async def resolve(self, name):
        return Entity(text=name, type="drug", canonical_name=name, ids={"rxcui": "1"}), [EvidenceItem.build(subject=name, predicate="drug_identity", value=name, source="RxNorm", source_record_id="1")]
class FailingFDA:
    async def approval_records(self, names, limit=20):
        raise RuntimeError("simulated 503")
class EmptyTrials:
    async def search_trials(self, **kwargs): return []
class EmptyChEMBL:
    async def target_drugs(self, target_query, limit=20): return []
class EmptyDailyMed:
    async def label_records(self, **kwargs): return []

@pytest.mark.asyncio
async def test_source_failure_is_exposed_not_hallucinated():
    engine = ChatAlchemyEngine(rxnorm=GoodRxNorm(), openfda=FailingFDA(), clinicaltrials=EmptyTrials(), chembl=EmptyChEMBL(), dailymed=EmptyDailyMed())
    response = await engine.answer("What FDA approval information is available for pembrolizumab?")
    await engine.close()
    assert any(not t.ok for t in response.traces)
    assert any("live sources failed" in w.lower() for w in response.warnings)
    assert "No matching Drugs@FDA" in response.answer
    assert not response.claims
