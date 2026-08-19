from __future__ import annotations
from ..models import EvidenceItem
from .base import LiveSource
class DailyMedSource(LiveSource):
    name="DailyMed";base_url="https://dailymed.nlm.nih.gov/dailymed/services/v2"
    async def label_records(self,drug:str,max_results:int=20)->list[EvidenceItem]:
        if not drug:return[]
        rows=(await self._get(f"{self.base_url}/spls.json",params={"drug_name":drug,"pagesize":max_results})).get("data") or [];out=[]
        for row in rows[:max_results]:
            setid=row.get("setid") or row.get("set_id");title=row.get("title") or row.get("spl_version") or drug;out.append(EvidenceItem.build(subject=drug,predicate="dailymed_label_record",value=title,qualifiers={"published_date":row.get("published_date"),"spl_version":row.get("spl_version")},source=self.name,source_record_id=setid,source_url=f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={setid}" if setid else None))
        return out
