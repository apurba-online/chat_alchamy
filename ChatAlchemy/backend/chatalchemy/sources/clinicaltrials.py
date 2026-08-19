from __future__ import annotations
from ..models import EvidenceItem
from .base import LiveSource
class ClinicalTrialsSource(LiveSource):
    name="ClinicalTrials.gov";base_url="https://clinicaltrials.gov/api/v2/studies"
    async def search_trials(self,drug:str|None=None,condition:str|None=None,phase:str|None=None,status:str|None=None,max_results:int=20)->list[EvidenceItem]:
        params={"pageSize":min(max_results*3,100),"format":"json"}
        if drug:params["query.intr"]=drug
        if condition:params["query.cond"]=condition
        out=[]
        for study in (await self._get(self.base_url,params=params)).get("studies") or []:
            p=study.get("protocolSection") or {};ident=p.get("identificationModule") or {};design=p.get("designModule") or {};status_mod=p.get("statusModule") or {};cond_mod=p.get("conditionsModule") or {};arms=p.get("armsInterventionsModule") or {};nct=ident.get("nctId");phases=design.get("phases") or [];overall=status_mod.get("overallStatus")
            if phase and phase not in phases:continue
            if status and overall!=status:continue
            interventions=[i.get("name") for i in arms.get("interventions") or [] if i.get("name")]
            out.append(EvidenceItem.build(subject=drug or condition or nct or "trial",predicate="clinical_trial",value=nct,qualifiers={"title":ident.get("briefTitle"),"phases":phases,"status":overall,"conditions":cond_mod.get("conditions") or [],"interventions":interventions},source=self.name,source_record_id=nct,source_url=f"https://clinicaltrials.gov/study/{nct}" if nct else None))
            if len(out)>=max_results:break
        return out
