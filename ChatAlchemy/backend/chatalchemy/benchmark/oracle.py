from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Any
from .generator import BenchmarkCase
from ..sources import ChEMBLSource,ClinicalTrialsSource,DailyMedSource,OpenFDASource,OpenTargetsSource,PubChemSource,RxNormSource
@dataclass
class OracleResult:kind:str;value:Any;source_records:list[dict[str,Any]]
class LiveOracle:
    def __init__(self):self.sources={"rxnorm":RxNormSource(),"dailymed":DailyMedSource(),"openfda":OpenFDASource(),"clinicaltrials":ClinicalTrialsSource(),"chembl":ChEMBLSource(),"opentargets":OpenTargetsSource(),"pubchem":PubChemSource()}
    async def close(self):await asyncio.gather(*(x.close() for x in self.sources.values()),return_exceptions=True)
    @staticmethod
    def _records(rows):return [{"source":e.source,"record":e.source_record_id,"retrieved_at":e.retrieved_at} for e in rows]
    async def execute(self,case:BenchmarkCase)->OracleResult:
        p=case.params;f=case.family
        if f=="identity":rows=await self.sources["rxnorm"].resolve(p["drug"]);return OracleResult("scalar",str(rows[0].value).lower() if rows else None,self._records(rows))
        if f=="label":rows=await self.sources["dailymed"].label_records(p["drug"],20);return OracleResult("set",sorted({str(e.source_record_id) for e in rows if e.source_record_id}),self._records(rows))
        if f=="approval":rows=await self.sources["openfda"].approval_records(p["drug"],20);return OracleResult("set",sorted({str(e.value) for e in rows}),self._records(rows))
        if f=="trials":rows=await self.sources["clinicaltrials"].search_trials(p["drug"],p["condition"],p["phase"],None,20);return OracleResult("set",sorted({str(e.value) for e in rows if e.value}),self._records(rows))
        if f=="target":rows=await self.sources["chembl"].target_drugs(p["target"],20);return OracleResult("set",sorted({str(e.value).lower() for e in rows}),self._records(rows))
        if f=="gene":rows=await self.sources["opentargets"].gene_details(p["gene"],20);return OracleResult("set",sorted({f"{e.predicate}:{str(e.value).lower()}" for e in rows if e.predicate in {"gene_disease_association","known_drug"}}),self._records(rows))
        if f=="compound":rows=await self.sources["pubchem"].compound(p["drug"]);return OracleResult("record",rows[0].value if rows else {},self._records(rows))
        if f=="cross":
            candidates=await self.sources["chembl"].target_drugs(p["target"],15)
            async def check(name):apps,trials=await asyncio.gather(self.sources["openfda"].approval_records(name,3),self.sources["clinicaltrials"].search_trials(name,p["condition"],p["phase"],p["status"],10));return name,apps,trials
            checked=await asyncio.gather(*(check(str(e.value)) for e in candidates[:10]));accepted=sorted({name.lower() for name,apps,trials in checked if apps and trials});rows=candidates[:]
            for _,apps,trials in checked:rows.extend(apps);rows.extend(trials)
            return OracleResult("set",accepted,self._records(rows))
        raise ValueError(f"Unknown family {f}")
