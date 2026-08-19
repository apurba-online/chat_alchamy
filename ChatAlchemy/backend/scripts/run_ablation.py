from __future__ import annotations
import argparse,asyncio,json,pathlib,yaml
from chatalchemy.benchmark.schema import BenchmarkCase
from chatalchemy.benchmark.oracle import execute_oracle
from chatalchemy.reasoning.engine import ReasoningEngine,EngineConfig
from chatalchemy.experiments.metrics import set_f1
CONFIGS={'full':EngineConfig(),'no_normalization':EngineConfig(use_normalization=False),'no_deterministic_joins':EngineConfig(use_deterministic_joins=False),'no_conflict':EngineConfig(use_conflict_analysis=False),'no_verifier':EngineConfig(use_claim_verifier=False)}
async def run(cases_path,output,limit=None):
    cases=[BenchmarkCase.model_validate(x) for x in yaml.safe_load(pathlib.Path(cases_path).read_text())]; cases=cases[:limit] if limit else cases; results={}
    for name,cfg in CONFIGS.items():
        engine=ReasoningEngine(config=cfg); rows=[]
        for case in cases:
            oracle=await execute_oracle(case.oracle); res=await engine.answer(case.question); expected=[str(e.value) for e in oracle]; predicted=[str(e.value) for e in res.evidence if not case.required_sources or e.source in case.required_sources]; rows.append({'id':case.id,'f1':set_f1(predicted,expected),'routing':res.plan.intent==case.intent,'support':res.supported_claim_rate,'conflicts':len(res.conflicts)})
        results[name]={'mean_f1':sum(r['f1'] for r in rows)/len(rows),'routing_accuracy':sum(r['routing'] for r in rows)/len(rows),'mean_support':sum(r['support'] for r in rows)/len(rows),'rows':rows}
    pathlib.Path(output).write_text(json.dumps(results,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--cases',default='benchmark/live_cases.yaml'); p.add_argument('--output',default='ablation_results.json'); p.add_argument('--limit',type=int); a=p.parse_args(); asyncio.run(run(a.cases,a.output,a.limit))
