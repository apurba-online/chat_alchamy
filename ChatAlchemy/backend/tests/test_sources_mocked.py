import httpx,pytest
from chatalchemy.sources.rxnorm import RxNormSource
from chatalchemy.sources.clinicaltrials import ClinicalTrialsSource
from chatalchemy.sources.openfda import OpenFDASource
@pytest.mark.asyncio
async def test_rxnorm_brand_normalizes_to_ingredient():
    async def handler(request):
        u=str(request.url)
        if 'approximateTerm' in u: return httpx.Response(200,json={'approximateGroup':{'candidate':[{'rxcui':'202433','score':'100'}]}})
        if '/202433/properties' in u: return httpx.Response(200,json={'properties':{'name':'Tylenol','tty':'BN'}})
        return httpx.Response(200,json={'relatedGroup':{'conceptGroup':[{'tty':'IN','conceptProperties':[{'rxcui':'161','name':'acetaminophen','tty':'IN'}]}]}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client: e,_=await RxNormSource(client).resolve('Tylenol')
    assert e[0].value=='acetaminophen' and e[0].identifiers['rxcui']=='161'
@pytest.mark.asyncio
async def test_clinicaltrial_filters_phase_and_status():
    payload={'studies':[{'protocolSection':{'identificationModule':{'nctId':'NCT1','briefTitle':'x'},'designModule':{'phases':['PHASE3']},'statusModule':{'overallStatus':'RECRUITING'},'conditionsModule':{'conditions':['NSCLC']},'armsInterventionsModule':{'interventions':[{'name':'pembrolizumab'}]}}},{'protocolSection':{'identificationModule':{'nctId':'NCT2'},'designModule':{'phases':['PHASE2']},'statusModule':{'overallStatus':'COMPLETED'}}}]}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=payload))) as client: e,_=await ClinicalTrialsSource(client).search('pembrolizumab',phase='PHASE3',status='RECRUITING')
    assert [x.value for x in e]==['NCT1']
@pytest.mark.asyncio
async def test_openfda_deduplicates_application_records():
    payload={'results':[{'application_number':'NDA1','products':[{'brand_name':'X','active_ingredients':[{'name':'drug'}]}]}]}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=payload))) as client: e,_=await OpenFDASource(client).approvals('drug')
    assert len(e)==1 and e[0].value=='NDA1'
