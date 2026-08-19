from __future__ import annotations
from ..models import EvidenceItem
from .base import LiveSource
class RxNormSource(LiveSource):
    name="RxNorm";base_url="https://rxnav.nlm.nih.gov/REST"
    async def resolve(self,drug:str)->list[EvidenceItem]:
        if not drug:return[]
        data=await self._get(f"{self.base_url}/approximateTerm.json",params={"term":drug,"maxEntries":8});candidates=data.get("approximateGroup",{}).get("candidate",[]) or []
        ranked=[]
        for c in candidates[:8]:
            rxcui=c.get("rxcui")
            if not rxcui:continue
            p=(await self._get(f"{self.base_url}/rxcui/{rxcui}/properties.json")).get("properties") or {};ranked.append(({"IN":0,"PIN":1,"MIN":2}.get(p.get("tty",""),9),p or {"rxcui":rxcui,"name":c.get("name",drug)}))
        if not ranked:return[]
        ranked.sort(key=lambda x:x[0]);best=ranked[0][1]
        if ranked[0][0]>=9 and best.get("rxcui"):
            related=await self._get(f"{self.base_url}/rxcui/{best['rxcui']}/related.json",params={"tty":"IN+PIN+MIN"});rel=[]
            for g in related.get("relatedGroup",{}).get("conceptGroup",[]) or []:
                for cp in g.get("conceptProperties") or []:rel.append(({"IN":0,"PIN":1,"MIN":2}.get(cp.get("tty",""),9),cp))
            if rel:rel.sort(key=lambda x:x[0]);best=rel[0][1]
        name=best.get("name") or drug;rxcui=str(best.get("rxcui") or "")
        return [EvidenceItem.build(subject=drug,predicate="canonical_drug_identity",value=name,qualifiers={"rxcui":rxcui,"tty":best.get("tty")},source=self.name,source_record_id=rxcui or None,source_url=f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json" if rxcui else None)]
