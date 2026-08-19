from __future__ import annotations
import os
from uuid import uuid4
from .base import BaseSource
from ..models import EvidenceItem

class OpenFDASource(BaseSource):
    name='openfda'; base='https://api.fda.gov/drug/drugsfda.json'
    async def approvals(self, drug: str, max_results: int=20):
        terms=[f'products.brand_name:"{drug}"',f'products.active_ingredients.name:"{drug}"',f'openfda.generic_name:"{drug}"']; key=os.getenv('OPENFDA_API_KEY'); total=0.0; results=[]; seen=set()
        for term in terms:
            params={'search':term,'limit':min(max_results,100)}
            if key: params['api_key']=key
            try: data,latency=await self._request_json('GET',self.base,params=params,retries=1); total+=latency
            except Exception: continue
            for item in data.get('results',[]) or []:
                app=str(item.get('application_number') or '')
                if app in seen: continue
                seen.add(app); products=item.get('products',[]) or []; names=sorted({p.get('brand_name') for p in products if p.get('brand_name')}); ingredients=sorted({a.get('name') for p in products for a in (p.get('active_ingredients') or []) if a.get('name')})
                results.append(EvidenceItem(id=f'openfda-{uuid4().hex[:12]}',source=self.name,source_record_id=app or None,source_url=f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={''.join(ch for ch in app if ch.isdigit())}" if app else None,subject=drug,canonical_subject=drug,predicate='fda_application_record',value=app,context={'brand_names':names,'active_ingredients':ingredients},raw=item))
                if len(results)>=max_results: return results,total
        return results,total
