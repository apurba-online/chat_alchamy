from __future__ import annotations
import argparse,asyncio,hashlib,json,pathlib,time,yaml
from datetime import datetime,timezone
from chatalchemy.benchmark.schema import BenchmarkCase
from chatalchemy.benchmark.oracle import execute_oracle
from chatalchemy.reasoning.engine import ReasoningEngine
async def run(cases_path,output):
    raw=yaml.safe_load(pathlib.Path(cases_path).read_text()); cases=[BenchmarkCase.model_validate(x) for x in raw if 'temporal' in x.get('tags',[])]; engine=ReasoningEngine(); rows=[]
    for c in cases:
        oracle=await execute_oracle(c.oracle); result=await engine.answer(c.question); truth=sorted((e.source,e.source_record_id,str(e.value),e.context) for e in oracle); state_hash=hashlib.sha256(json.dumps(truth,sort_keys=True,default=str).encode()).hexdigest(); rows.append({'id':c.id,'timestamp':datetime.now(timezone.utc).isoformat(),'source_state_hash':state_hash,'oracle_record_ids':[e.source_record_id for e in oracle],'system_record_ids':[e.source_record_id for e in result.evidence],'warnings':result.warnings})
    pathlib.Path(output).write_text(json.dumps({'run_timestamp':datetime.now(timezone.utc).isoformat(),'cases':rows},indent=2)); print(f'wrote {len(rows)} temporal observations')
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--cases',default='benchmark/livebioevidencebench_1500.yaml'); p.add_argument('--output',default=f'temporal_{int(time.time())}.json'); a=p.parse_args(); asyncio.run(run(a.cases,a.output))
