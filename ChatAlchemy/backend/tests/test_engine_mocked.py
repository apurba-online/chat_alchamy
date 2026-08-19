import httpx,pytest
from chatalchemy.llm import LLMClient
from chatalchemy.reasoning import ChatAlchemyEngine
from chatalchemy.sources import RxNormSource,DailyMedSource,OpenFDASource,ClinicalTrialsSource,ChEMBLSource,OpenTargetsSource,PubChemSource
@pytest.mark.asyncio
async def test_engine_identity_end_to_end_mocked():
    def handler(req):
        u=str(req.url)
        if "approximateTerm" in u:return httpx.Response(200,json={"approximateGroup":{"candidate":[{"rxcui":"161","name":"acetaminophen"}]}})
        if "/rxcui/161/properties" in u:return httpx.Response(200,json={"properties":{"rxcui":"161","name":"acetaminophen","tty":"IN"}})
        return httpx.Response(200,json={})
    client=httpx.AsyncClient(transport=httpx.MockTransport(handler));sources={"rxnorm":RxNormSource(client=client),"dailymed":DailyMedSource(client=client),"openfda":OpenFDASource(client=client),"clinicaltrials":ClinicalTrialsSource(client=client),"chembl":ChEMBLSource(client=client),"opentargets":OpenTargetsSource(client=client),"pubchem":PubChemSource(client=client)};llm=LLMClient(client=client);llm.api_key=None;engine=ChatAlchemyEngine(llm=llm,sources=sources);result=await engine.answer("What is the generic identity of Tylenol?");assert result.plan.intent=="identity";assert result.supported_claim_rate==1.0;assert result.evidence[0].value=="acetaminophen";await client.aclose()
