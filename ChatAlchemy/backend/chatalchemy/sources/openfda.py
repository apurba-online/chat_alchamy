from __future__ import annotations
import os
from ..models import EvidenceItem
from .base import LiveSource
class OpenFDASource(LiveSource):
    name="Drugs@FDA/openFDA";base_url="https://api.fda.gov/drug/drugsfda.json"
    async def approval_records(self,drug:str,max_results:int=20)->list[EvidenceItem]:
        if not drug:return[]
        terms=[f'openfda.generic_name:"{drug}"',f'openfda.brand_name:"{drug}"',f'products.active_ingredients.name:"{drug}"'];params={"limit":min(max_results,100)};key=os.getenv("OPENFDA_API_KEY")
        if key:params["api_key"]=key
        data=None
        for search in terms:
            try:
                data=await self._get(self.base_url,params={**params,"search":search},attempts=1)
                if data.get("results"):break
            except Exception:continue
        if not data:return[]
        out=[]
        for app in (data.get("results") or [])[:max_results]:
            appno=app.get("application_number");names=sorted({p.get("brand_name") for p in app.get("products") or [] if p.get("brand_name")});out.append(EvidenceItem.build(subject=drug,predicate="fda_application_record",value=appno or "application record",qualifiers={"sponsor":app.get("sponsor_name"),"brand_names":names},source=self.name,source_record_id=appno,source_url="https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm"))
        return out
