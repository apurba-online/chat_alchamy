import httpx,pytest
from chatalchemy.sources import RxNormSource,ClinicalTrialsSource,PubChemSource
@pytest.mark.asyncio
async def test_rxnorm_resolve_mocked():
    def handler(req):
        if "approximateTerm" in str(req.url):return httpx.Response(200,json={"approximateGroup":{"candidate":[{"rxcui":"161","name":"acetaminophen"}]}})
        if "/rxcui/161/properties" in str(req.url):return httpx.Response(200,json={"properties":{"rxcui":"161","name":"acetaminophen","tty":"IN"}})
        return httpx.Response(404)
    client=httpx.AsyncClient(transport=httpx.MockTransport(handler));rows=await RxNormSource(client=client).resolve("Tylenol");assert rows[0].value=="acetaminophen";await client.aclose()
@pytest.mark.asyncio
async def test_trials_filter_mocked():
    payload={"studies":[{"protocolSection":{"identificationModule":{"nctId":"NCT1","briefTitle":"Test"},"designModule":{"phases":["PHASE3"]},"statusModule":{"overallStatus":"RECRUITING"},"conditionsModule":{"conditions":["NSCLC"]},"armsInterventionsModule":{"interventions":[{"name":"pembrolizumab"}]}}}]};client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=payload)));rows=await ClinicalTrialsSource(client=client).search_trials("pembrolizumab","NSCLC","PHASE3","RECRUITING",20);assert len(rows)==1 and rows[0].value=="NCT1";await client.aclose()
@pytest.mark.asyncio
async def test_pubchem_mocked():
    payload={"PropertyTable":{"Properties":[{"CID":123,"ConnectivitySMILES":"CCO","IUPACName":"ethanol"}]}};client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=payload)));rows=await PubChemSource(client=client).compound("ethanol");assert rows[0].value["cid"]=="123";await client.aclose()
