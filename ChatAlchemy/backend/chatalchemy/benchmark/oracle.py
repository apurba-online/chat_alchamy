from __future__ import annotations
import asyncio
from typing import Any
from ..sources.rxnorm import RxNormSource
from ..sources.dailymed import DailyMedSource
from ..sources.openfda import OpenFDASource
from ..sources.clinicaltrials import ClinicalTrialsSource
from ..sources.chembl import ChEMBLSource
from ..sources.opentargets import OpenTargetsSource
from ..sources.pubchem import PubChemSource
SOURCES={'rxnorm':RxNormSource(),'dailymed':DailyMedSource(),'openfda':OpenFDASource(),'clinicaltrials':ClinicalTrialsSource(),'chembl':ChEMBLSource(),'opentargets':OpenTargetsSource(),'pubchem':PubChemSource()}
async def _single(spec:dict[str,Any]):
    source=SOURCES[spec['source']]; action=spec['action']; args=dict(spec.get('arguments') or {})
    if source.name=='rxnorm': items,_=await source.resolve(**args)
    elif source.name=='dailymed': items,_=await source.labels(**args)
    elif source.name=='openfda': items,_=await source.approvals(**args)
    elif source.name=='clinicaltrials': items,_=await source.search(**args)
    elif source.name=='chembl': items,_=await source.target_drugs(**args)
    elif source.name=='opentargets' and action=='disease_targets': items,_=await source.disease_targets(**args)
    elif source.name=='opentargets': items,_=await source.gene_diseases(**args)
    elif source.name=='pubchem': items,_=await source.compound(**args)
    else: raise ValueError(f'Unsupported oracle {source.name}:{action}')
    return items
async def _cross_source(spec:dict[str,Any]):
    chem,_=await SOURCES['chembl'].target_drugs(spec['target'],max_results=spec.get('max_results',20))
    async def check(ev):
        name=str(ev.value); fda,_=await SOURCES['openfda'].approvals(name,max_results=5); trials,_=await SOURCES['clinicaltrials'].search(drug=name,condition=spec.get('condition'),phase=spec.get('phase'),status=spec.get('status'),max_results=5); return [ev,*fda,*trials] if fda and trials else []
    return [x for chunk in await asyncio.gather(*(check(e) for e in chem)) for x in chunk]
async def execute_oracle(spec:dict[str,Any]):
    return await _cross_source(spec) if spec.get('kind')=='cross_source' else await _single(spec)
