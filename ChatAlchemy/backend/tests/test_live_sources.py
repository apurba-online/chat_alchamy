import os,pytest
from chatalchemy.sources.rxnorm import RxNormSource
from chatalchemy.sources.clinicaltrials import ClinicalTrialsSource
from chatalchemy.sources.opentargets import OpenTargetsSource
from chatalchemy.sources.pubchem import PubChemSource
pytestmark=pytest.mark.live
@pytest.mark.skipif(os.getenv('RUN_LIVE_TESTS')!='1',reason='set RUN_LIVE_TESTS=1')
@pytest.mark.asyncio
async def test_live_contracts():
    rx,_=await RxNormSource().resolve('Tylenol'); assert rx; ct,_=await ClinicalTrialsSource().search('pembrolizumab',max_results=1); assert isinstance(ct,list); ot,_=await OpenTargetsSource().disease_targets('lung cancer',max_results=1); assert isinstance(ot,list); pc,_=await PubChemSource().compound('osimertinib'); assert pc
