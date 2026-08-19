import pytest
from chatalchemy.models import EvidenceItem
from chatalchemy.reasoning.engine import ReasoningEngine
class Rx:
    async def resolve(self,drug,max_results=5): return [EvidenceItem(id='rx1',source='rxnorm',source_record_id='161',subject=drug,canonical_subject='acetaminophen',predicate='canonical_identity',value='acetaminophen',identifiers={'rxcui':'161'})],1.0
class DM:
    async def labels(self,drug,rxcui=None,max_results=20): return [EvidenceItem(id='dm1',source='dailymed',subject=drug,predicate='label_record',value='TYLENOL label')],2.0
class FDA:
    async def approvals(self,drug,max_results=20): return [EvidenceItem(id=f'fda-{drug}',source='openfda',subject=drug,predicate='fda_application_record',value='NDA1')],1.0
class CT:
    async def search(self,drug=None,condition=None,phase=None,status=None,max_results=20): return [EvidenceItem(id=f'ct-{drug}',source='clinicaltrials',subject=drug or 'x',predicate='clinical_trial',value='NCT1',context={'condition':condition,'phases':[phase] if phase else [],'status':status})],1.0
class Ch:
    async def target_drugs(self,target,max_results=20): return [EvidenceItem(id='c1',source='chembl',subject=target,predicate='target_drug',value='OSIMERTINIB'),EvidenceItem(id='c2',source='chembl',subject=target,predicate='target_drug',value='AFATINIB')],1.0
class OT:
    async def disease_targets(self,disease,max_results=20): return [EvidenceItem(id='ot1',source='opentargets',subject=disease,predicate='disease_target',value='EGFR')],1.0
    async def gene_diseases(self,gene,max_results=20): return [],1.0
class PC:
    async def compound(self,name): return [EvidenceItem(id='pc1',source='pubchem',subject=name,predicate='compound_properties',value={'canonical_smiles':'CO','iupac_name':'x'})],1.0
def eng(): return ReasoningEngine({'rxnorm':Rx(),'dailymed':DM(),'openfda':FDA(),'clinicaltrials':CT(),'chembl':Ch(),'opentargets':OT(),'pubchem':PC()})
@pytest.mark.asyncio
async def test_identity_supported():
    r=await eng().answer('What is the generic identity of Tylenol?'); assert 'acetaminophen' in r.answer and r.supported_claim_rate==1.0
@pytest.mark.asyncio
async def test_cross_source_intersection():
    r=await eng().answer('Which FDA-approved drugs targeting EGFR also have recruiting Phase 3 trials for non-small-cell lung cancer?'); assert r.plan.intent=='cross_source' and '2 candidate' in r.answer and r.supported_claim_rate==1.0
@pytest.mark.asyncio
async def test_user_evidence_is_provenance_object():
    r=await eng().answer('What is the generic identity of Tylenol?',user_evidence=[{'subject':'paper','predicate':'mentions','value':'TP53'}]); assert any(e.source=='user' for e in r.evidence)
