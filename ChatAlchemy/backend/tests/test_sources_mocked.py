import httpx
import pytest

from chatalchemy.sources import ClinicalTrialsSource, OpenFDASource, RxNormSource


@pytest.mark.asyncio
async def test_rxnorm_parsing():
    async def handler(request: httpx.Request):
        if "approximateTerm" in str(request.url):
            return httpx.Response(200, json={"approximateGroup": {"candidate": [{"rxcui": "161", "score": "100"}]}})
        return httpx.Response(200, json={"properties": {"name": "acetaminophen", "tty": "IN"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        entity, evidence = await RxNormSource(client).resolve("Tylenol")
    assert entity is not None
    assert entity.ids["rxcui"] == "161"
    assert entity.canonical_name == "acetaminophen"
    assert evidence[0].predicate == "drug_identity"


@pytest.mark.asyncio
async def test_openfda_parsing():
    async def handler(request: httpx.Request):
        return httpx.Response(200, json={"results": [{"application_number": "BLA125514", "sponsor_name": "Example", "openfda": {"generic_name": ["PEMBROLIZUMAB"]}, "products": [{"brand_name": "KEYTRUDA", "marketing_status": "Prescription"}]}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        evidence = await OpenFDASource(client).approval_records(["pembrolizumab"])
    assert len(evidence) == 1
    assert evidence[0].value == "BLA125514"


@pytest.mark.asyncio
async def test_clinicaltrials_filters_phase_and_status():
    async def handler(request: httpx.Request):
        return httpx.Response(200, json={"studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT0001", "briefTitle": "Trial"}, "statusModule": {"overallStatus": "RECRUITING"}, "designModule": {"phases": ["PHASE3"]}, "conditionsModule": {"conditions": ["NSCLC"]}, "armsInterventionsModule": {"interventions": [{"name": "Pembrolizumab"}]}}}, {"protocolSection": {"identificationModule": {"nctId": "NCT0002"}, "statusModule": {"overallStatus": "COMPLETED"}, "designModule": {"phases": ["PHASE3"]}}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        evidence = await ClinicalTrialsSource(client).search_trials(intervention="pembrolizumab", condition="NSCLC", phase="PHASE3", status="RECRUITING")
    assert [e.value for e in evidence] == ["NCT0001"]


@pytest.mark.asyncio
async def test_chembl_target_and_mechanism_parsing():
    from chatalchemy.sources import ChEMBLSource
    async def handler(request: httpx.Request):
        url = str(request.url)
        if "/target/search.json" in url:
            return httpx.Response(200, json={"targets": [{"target_chembl_id": "CHEMBL203", "pref_name": "Epidermal growth factor receptor erbB1", "organism": "Homo sapiens"}]})
        if "/mechanism.json" in url:
            return httpx.Response(200, json={"mechanisms": [{"molecule_chembl_id": "CHEMBL1201742", "mechanism_of_action": "EGFR inhibitor", "action_type": "INHIBITOR"}]})
        if "/molecule/CHEMBL1201742.json" in url:
            return httpx.Response(200, json={"molecule_chembl_id": "CHEMBL1201742", "pref_name": "GEFITINIB"})
        return httpx.Response(404)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        evidence = await ChEMBLSource(client).target_drugs("EGFR")
    assert evidence
    assert evidence[0].subject == "GEFITINIB"
    assert evidence[0].predicate == "molecular_target"


@pytest.mark.asyncio
async def test_dailymed_spl_parsing():
    from chatalchemy.sources import DailyMedSource
    async def handler(request: httpx.Request):
        return httpx.Response(200, json={"metadata": {"total_elements": "1"}, "data": [{"setid": "abc-123", "title": "KEYTRUDA- pembrolizumab injection", "spl_version": "10", "published_date": "Aug 01, 2026"}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        evidence = await DailyMedSource(client).label_records(drug_name="pembrolizumab", rxcui="1547545")
    assert len(evidence) == 1
    assert evidence[0].value == "abc-123"
    assert evidence[0].predicate == "dailymed_label_record"
