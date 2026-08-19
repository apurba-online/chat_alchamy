import pytest

from chatalchemy.models import Entity, EvidenceItem
from chatalchemy.reasoning import ChatAlchemyEngine

class FakeRxNorm:
    async def resolve(self, name):
        entity = Entity(text=name, type="drug", canonical_name="pembrolizumab", ids={"rxcui": "1547545"})
        ev = EvidenceItem.build(subject="pembrolizumab", predicate="drug_identity", value="pembrolizumab", source="RxNorm", source_record_id="1547545")
        return entity, [ev]
class FakeFDA:
    async def approval_records(self, names, limit=20):
        return [EvidenceItem.build(subject="pembrolizumab", predicate="fda_approval_record", value="BLA125514", source="Drugs@FDA/openFDA", source_record_id="BLA125514")]
class FakeTrials:
    async def search_trials(self, **kwargs):
        return [EvidenceItem.build(subject="pembrolizumab", predicate="clinical_trial", value="NCT123", source="ClinicalTrials.gov", source_record_id="NCT123", qualifiers={"phase": ["PHASE3"], "status": "RECRUITING"})]
class FakeChEMBL:
    async def target_drugs(self, target_query, limit=20):
        return [EvidenceItem.build(subject="pembrolizumab", predicate="molecular_target", value=target_query, source="ChEMBL", source_record_id="CHEMBL:X")]
class FakeDailyMed:
    async def label_records(self, **kwargs):
        return []

@pytest.mark.asyncio
async def test_approval_end_to_end_with_fake_live_sources():
    engine = ChatAlchemyEngine(rxnorm=FakeRxNorm(), openfda=FakeFDA(), clinicaltrials=FakeTrials(), chembl=FakeChEMBL(), dailymed=FakeDailyMed())
    response = await engine.answer("What FDA approval information is available for pembrolizumab?")
    await engine.close()
    assert "BLA125514" in response.answer
    assert response.supported_claim_rate == 1.0
    assert all(claim.supported for claim in response.claims)
    assert {e.source for e in response.evidence} >= {"RxNorm", "Drugs@FDA/openFDA"}

@pytest.mark.asyncio
async def test_trial_end_to_end_with_fake_live_sources():
    engine = ChatAlchemyEngine(rxnorm=FakeRxNorm(), openfda=FakeFDA(), clinicaltrials=FakeTrials(), chembl=FakeChEMBL(), dailymed=FakeDailyMed())
    response = await engine.answer("How many recruiting Phase 3 trials involve pembrolizumab for NSCLC?")
    await engine.close()
    assert "1 matching trial" in response.answer
    assert response.plan.filters["phase"] == "PHASE3"
    assert response.supported_claim_rate == 1.0
