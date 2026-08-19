import pytest

from chatalchemy.reasoning import ChatAlchemyEngine

pytestmark = pytest.mark.live

@pytest.mark.asyncio
async def test_live_rxnorm_identity():
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("What is the generic identity of Tylenol?")
        assert any(t.source == "RxNorm" and t.ok for t in response.traces)
        assert any(e.source == "RxNorm" for e in response.evidence)
        assert response.supported_claim_rate == 1.0
    finally: await engine.close()

@pytest.mark.asyncio
async def test_live_openfda_approval():
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("What FDA approval information is available for pembrolizumab?")
        assert any(t.source == "Drugs@FDA/openFDA" and t.ok for t in response.traces)
        assert any(e.predicate == "fda_approval_record" for e in response.evidence)
    finally: await engine.close()

@pytest.mark.asyncio
async def test_live_clinicaltrials_query():
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("List Phase 3 trials involving pembrolizumab for non-small-cell lung cancer.")
        assert any(t.source == "ClinicalTrials.gov" and t.ok for t in response.traces)
        assert response.plan.intent == "trials"
    finally: await engine.close()

@pytest.mark.asyncio
async def test_live_chembl_target_query():
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("Which drugs target EGFR?")
        assert any(t.source == "ChEMBL" and t.ok for t in response.traces)
        assert response.plan.intent == "target_drugs"
    finally: await engine.close()

@pytest.mark.asyncio
async def test_live_dailymed_label_query():
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("What DailyMed label records are available for pembrolizumab?")
        assert any(t.source == "DailyMed" and t.ok for t in response.traces)
        assert response.plan.intent == "label"
    finally: await engine.close()
