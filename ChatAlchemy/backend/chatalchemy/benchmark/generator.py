from __future__ import annotations
import random
from dataclasses import dataclass,asdict,field
from typing import Any,Iterable
DRUGS=["pembrolizumab","osimertinib","gefitinib","erlotinib","acetaminophen","trastuzumab","nivolumab","afatinib","cetuximab","panitumumab"];TARGETS=["EGFR","ALK","BRAF","ERBB2","MET","KRAS","PDCD1","VEGFA"];CONDITIONS=["non-small-cell lung cancer","breast cancer","melanoma","colorectal cancer","head and neck cancer"];GENES=["EGFR","ALK","BRAF","ERBB2","MET","KRAS","TP53","BRCA1","BRCA2","PDCD1"];STATUSES=["recruiting","completed","active, not recruiting"];STATUS_CANONICAL={"recruiting":"RECRUITING","completed":"COMPLETED","active, not recruiting":"ACTIVE_NOT_RECRUITING"};PHASES=["Phase 1","Phase 2","Phase 3"];PHASE_CANONICAL={"Phase 1":"PHASE1","Phase 2":"PHASE2","Phase 3":"PHASE3"}
@dataclass(frozen=True)
class BenchmarkCase:
    id:str;family:str;question:str;oracle:str;sources:list[str];expected_operation:str;params:dict[str,Any]=field(default_factory=dict);output_kind:str="set"
TEMPLATES={"identity":("What is the generic identity of {drug}?","identity",["rxnorm"],"scalar"),"label":("What DailyMed label records are available for {drug}?","label",["dailymed"],"set"),"approval":("What FDA application information is available for {drug}?","approval",["openfda"],"set"),"trials":("List {phase} trials involving {drug} for {condition}.","trials",["clinicaltrials"],"set"),"target":("Which drugs target {target}?","target_drugs",["chembl"],"set"),"cross":("Which FDA-approved drugs targeting {target} also have {status} {phase} trials for {condition}?","cross_source",["chembl","openfda","clinicaltrials"],"set"),"gene":("What diseases and known drugs are associated with gene {gene} in Open Targets?","gene",["opentargets"],"set"),"compound":("What are the PubChem compound properties of {drug}?","compound",["pubchem"],"record")}
def generate_cases(n:int=1500,seed:int=1729)->list[BenchmarkCase]:
    rng=random.Random(seed);families=list(TEMPLATES);cases=[]
    for i in range(n):
        family=families[i%len(families)];template,operation,sources,output_kind=TEMPLATES[family];phase=rng.choice(PHASES);status=rng.choice(STATUSES);params={"drug":rng.choice(DRUGS),"target":rng.choice(TARGETS),"condition":rng.choice(CONDITIONS),"gene":rng.choice(GENES),"status":STATUS_CANONICAL[status],"phase":PHASE_CANONICAL[phase],"status_text":status,"phase_text":phase};q=template.format(drug=params["drug"],target=params["target"],condition=params["condition"],gene=params["gene"],status=status,phase=phase);cases.append(BenchmarkCase(id=f"livebio-{i+1:04d}",family=family,question=q,oracle="execute_live_sources",sources=sources,expected_operation=operation,params=params,output_kind=output_kind))
    return cases
def as_jsonable(cases:Iterable[BenchmarkCase]):return [asdict(c) for c in cases]
