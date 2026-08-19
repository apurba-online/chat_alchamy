import pytest

from chatalchemy.reasoning import ChatAlchemyEngine

pytestmark = pytest.mark.live


def require_source(response, source: str):
    trace = next((t for t in response.traces if t.source == source), None)
    assert trace is not None, f"No trace was recorded for {source}"
    if not trace.ok:
        pytest.skip(f"External source unavailable from CI runner: {source}: {trace.error}")
    return trace


@pytest.mark.asyncio
async def test_live_rxnorm_identity():
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("What is the generic identity of Tylenol?")
        require_source(response, "RxNorm")
        assert any(e.source == "RxNorm" for e in response.evidence)
        assert "acetaminophen" in response.answer.lower()
        assert response.supported_claim_rate == 1.0
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_live_openfda_approval():
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("What FDA approval information is available for pembrolizumab?")
        require_source(response, "Drugs@FDA/openFDA")
        assert any(e.predicate == "fda_application_record" for e in response.evidence)
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_live_clinicaltrials_query():
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("List Phase 3 trials involving pembrolizumab for non-small-cell lung cancer.")
        require_source(response, "ClinicalTrials.gov")
        assert response.plan.intent == "trials"
        assert any(e.predicate == "clinical_trial" for e in response.evidence)
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_live_chembl_target_query():
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("Which drugs target EGFR?")
        require_source(response, "ChEMBL")
        assert any(e.source == "ChEMBL" for e in response.evidence)
        assert response.plan.intent == "target_drugs"
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_live_dailymed_label_query():
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("What DailyMed label records are available for pembrolizumab?")
        require_source(response, "DailyMed")
        assert response.plan.intent == "label"
        assert any(e.predicate == "dailymed_label_record" for e in response.evidence)
    finally:
        await engine.close()
