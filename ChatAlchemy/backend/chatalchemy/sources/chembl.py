from __future__ import annotations
import asyncio
from uuid import uuid4
from .base import BaseSource
from ..models import EvidenceItem

class ChEMBLSource(BaseSource):
    name='chembl'; base='https://www.ebi.ac.uk/chembl/api/data'
    async def target_drugs(self, target: str, max_results: int=20):
        data,latency=await self._request_json('GET',f'{self.base}/target/search.json',params={'q':target,'limit':20}); targets=data.get('targets',[]) or []
        def score(t):
            return ((t.get('pref_name') or '').upper()==target.upper())*10+('Homo sapiens' in (t.get('organism') or ''))*4+(t.get('target_type')=='SINGLE PROTEIN')*2
        candidates=sorted(targets,key=score,reverse=True)[:6]; out=[]; total=latency
        for t in candidates:
            tid=t.get('target_chembl_id')
            if not tid: continue
            mech,l2=await self._request_json('GET',f'{self.base}/mechanism.json',params={'target_chembl_id':tid,'limit':100}); total+=l2; ids=[]
            for m in mech.get('mechanisms',[]) or []:
                mid=m.get('molecule_chembl_id')
                if mid and mid not in ids: ids.append(mid)
            async def fetch_name(mid):
                try: md,l=await self._request_json('GET',f'{self.base}/molecule/{mid}.json',retries=1); return mid,md.get('pref_name') or mid,l
                except Exception: return mid,mid,0.0
            names=await asyncio.gather(*(fetch_name(mid) for mid in ids[:max_results]))
            for mid,name,l in names:
                total+=l; out.append(EvidenceItem(id=f'chembl-{uuid4().hex[:12]}',source=self.name,source_record_id=mid,source_url=f'https://www.ebi.ac.uk/chembl/explore/compound/{mid}',subject=target.upper(),canonical_subject=target.upper(),predicate='target_drug',value=name,identifiers={'chembl_id':mid,'target_chembl_id':tid},context={'target_name':t.get('pref_name')}))
                if len(out)>=max_results: return out,total
        return out,total
