from __future__ import annotations
import asyncio
from ..models import EvidenceItem
from .base import LiveSource
class ChEMBLSource(LiveSource):
    name="ChEMBL";base_url="https://www.ebi.ac.uk/chembl/api/data"
    async def target_drugs(self,target:str,max_results:int=20)->list[EvidenceItem]:
        if not target:return[]
        targets=(await self._get(f"{self.base_url}/target/search.json",params={"q":target,"limit":10})).get("targets") or []
        def score(t):
            text=" ".join(str(t.get(k,"")) for k in ["pref_name","target_chembl_id","organism","target_type"]).upper();s=10 if target.upper() in text else 0;s+=5 if t.get("organism")=="Homo sapiens" else 0;s+=3 if t.get("target_type")=="SINGLE PROTEIN" else 0;return s
        mech_rows=[]
        for t in sorted(targets,key=score,reverse=True)[:6]:
            tid=t.get("target_chembl_id")
            if not tid:continue
            try:mech_rows.extend((tid,m) for m in (await self._get(f"{self.base_url}/mechanism.json",params={"target_chembl_id":tid,"limit":50},attempts=1)).get("mechanisms") or [])
            except Exception:continue
        mol_ids=[]
        for _,m in mech_rows:
            mid=m.get("molecule_chembl_id")
            if mid and mid not in mol_ids:mol_ids.append(mid)
        async def molecule(mid):
            try:return mid,await self._get(f"{self.base_url}/molecule/{mid}.json",attempts=1)
            except Exception:return mid,{}
        molecules=dict(await asyncio.gather(*(molecule(mid) for mid in mol_ids[:max_results])));out=[];seen=set()
        for tid,m in mech_rows:
            mid=m.get("molecule_chembl_id")
            if not mid or mid in seen:continue
            seen.add(mid);mol=molecules.get(mid) or {};name=mol.get("pref_name") or mid;out.append(EvidenceItem.build(subject=target.upper(),predicate="targeting_drug",value=name,qualifiers={"molecule_chembl_id":mid,"target_chembl_id":tid,"mechanism":m.get("mechanism_of_action"),"action_type":m.get("action_type")},source=self.name,source_record_id=mid,source_url=f"https://www.ebi.ac.uk/chembl/explore/compound/{mid}"))
            if len(out)>=max_results:break
        return out
