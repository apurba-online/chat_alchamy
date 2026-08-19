from __future__ import annotations
from uuid import uuid4
from .base import BaseSource
from ..models import EvidenceItem

class ClinicalTrialsSource(BaseSource):
    name='clinicaltrials'; base='https://clinicaltrials.gov/api/v2/studies'
    async def search(self, drug: str|None=None, condition: str|None=None, phase: str|None=None, status: str|None=None, max_results: int=20):
        params={'pageSize':min(max(max_results*4,20),100)}
        if drug: params['query.intr']=drug
        if condition: params['query.cond']=condition
        data,latency=await self._request_json('GET',self.base,params=params); out=[]
        for study in data.get('studies',[]) or []:
            protocol=study.get('protocolSection',{}) or {}; ident=protocol.get('identificationModule',{}) or {}; design=protocol.get('designModule',{}) or {}; stat=protocol.get('statusModule',{}) or {}; cond=protocol.get('conditionsModule',{}) or {}; arms=protocol.get('armsInterventionsModule',{}) or {}; phases=design.get('phases',[]) or []; overall=stat.get('overallStatus')
            if phase and phase not in phases: continue
            if status and status!=overall: continue
            nct=ident.get('nctId'); interventions=[i.get('name') for i in arms.get('interventions',[]) or [] if i.get('name')]
            out.append(EvidenceItem(id=f'ctg-{uuid4().hex[:12]}',source=self.name,source_record_id=nct,source_url=f'https://clinicaltrials.gov/study/{nct}' if nct else None,subject=drug or condition or 'clinical trial',predicate='clinical_trial',value=nct,context={'title':ident.get('briefTitle'),'phases':phases,'status':overall,'conditions':cond.get('conditions',[]) or [],'interventions':interventions},raw=study))
            if len(out)>=max_results: break
        return out,latency
