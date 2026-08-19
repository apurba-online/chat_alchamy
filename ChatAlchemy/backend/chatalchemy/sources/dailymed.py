from __future__ import annotations
from uuid import uuid4
from .base import BaseSource
from ..models import EvidenceItem

class DailyMedSource(BaseSource):
    name='dailymed'; base='https://dailymed.nlm.nih.gov/dailymed/services/v2'
    async def labels(self, drug: str, rxcui: str|None=None, max_results: int=20):
        params={'pagesize':max_results}; params['rxcui' if rxcui else 'drug_name']=rxcui or drug
        data,latency=await self._request_json('GET',f'{self.base}/spls.json',params=params); items=data.get('data',[]) if isinstance(data,dict) else []
        out=[]
        for item in items[:max_results]:
            setid=str(item.get('setid') or item.get('set_id') or ''); title=item.get('title') or item.get('drug_name') or drug
            out.append(EvidenceItem(id=f'dailymed-{uuid4().hex[:12]}',source=self.name,source_record_id=setid or None,source_url=f'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}' if setid else None,subject=drug,canonical_subject=drug,predicate='label_record',value=title,context={'spl_version':item.get('spl_version'),'published_date':item.get('published_date')},raw=item))
        return out,latency
