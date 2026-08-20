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


@pytest.mark.asyncio
async def test_live_opentargets_disease_gene_query():
    """Release gate for the exact natural-language failure found in preview."""
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("What genes are associated with non-small-cell lung cancer?")
        trace = next((t for t in response.traces if t.source == "Open Targets"), None)
        assert trace is not None, "No Open Targets trace was recorded"
        assert trace.ok, trace.error
        assert response.plan.intent == "disease"
        assert trace.result_count > 0
        assert any(e.predicate == "disease_gene_association" for e in response.evidence)
        assert any(str(e.value).upper() == "EGFR" for e in response.evidence)
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_live_opentargets_egfr_gene_details_query():
    """Strict gate for current ClinicalTargetFromTarget GraphQL fields."""
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("What diseases are associated with gene EGFR in Open Targets?")
        trace = next((t for t in response.traces if t.source == "Open Targets"), None)
        assert trace is not None, "No Open Targets trace was recorded"
        assert trace.ok, trace.error
        assert response.plan.intent == "gene"
        assert trace.result_count > 0
        assert any(e.predicate == "gene_identity" for e in response.evidence)
        assert any(e.predicate == "gene_disease_association" for e in response.evidence)
        assert any(e.predicate == "known_drug" for e in response.evidence)
    finally:
        await engine.close()


@pytest.mark.asyncio
async def test_live_pubchem_compound_query():
    engine = ChatAlchemyEngine()
    try:
        response = await engine.answer("Give the PubChem CID, canonical SMILES, and IUPAC name for aspirin.")
        require_source(response, "PubChem")
        assert response.plan.intent == "compound"
        assert any(e.predicate == "compound_properties" for e in response.evidence)
    finally:
        await engine.close()
