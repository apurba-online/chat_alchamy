from __future__ import annotations
from uuid import uuid4
from .base import BaseSource
from ..models import EvidenceItem

class RxNormSource(BaseSource):
    name='rxnorm'; base='https://rxnav.nlm.nih.gov/REST'
    async def resolve(self, drug: str, max_results: int = 5):
        data,latency=await self._request_json('GET',f'{self.base}/approximateTerm.json',params={'term':drug,'maxEntries':max_results})
        candidates=data.get('approximateGroup',{}).get('candidate',[]) or []
        if not candidates: return [],latency
        best=sorted(candidates,key=lambda c:int(c.get('score',0)),reverse=True)[0]; rxcui=str(best.get('rxcui',''))
        prop,l2=await self._request_json('GET',f'{self.base}/rxcui/{rxcui}/properties.json'); latency+=l2
        properties=prop.get('properties',{}) or {}; name=properties.get('name') or drug; tty=properties.get('tty') or ''
        if tty not in {'IN','PIN','MIN'}:
            rel,l3=await self._request_json('GET',f'{self.base}/rxcui/{rxcui}/related.json',params={'tty':'IN+PIN+MIN'}); latency+=l3
            concepts=[]
            for group in rel.get('relatedGroup',{}).get('conceptGroup',[]) or []: concepts += group.get('conceptProperties',[]) or []
            rank={'IN':0,'PIN':1,'MIN':2}
            if concepts:
                chosen=sorted(concepts,key=lambda x:(rank.get(x.get('tty',''),9),x.get('name','')))[0]; name=chosen.get('name',name); rxcui=str(chosen.get('rxcui',rxcui)); tty=chosen.get('tty',tty)
        return [EvidenceItem(id=f'rxnorm-{uuid4().hex[:12]}',source=self.name,source_record_id=rxcui,source_url=f'https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json',subject=drug,canonical_subject=name,predicate='canonical_identity',value=name,identifiers={'rxcui':rxcui},context={'tty':tty,'query':drug},raw=best)],latency
