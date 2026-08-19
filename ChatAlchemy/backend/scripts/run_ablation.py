from __future__ import annotations
import argparse,asyncio,json,statistics
from pathlib import Path
from chatalchemy.benchmark import LiveOracle,generate_cases,score_value
from chatalchemy.reasoning import ChatAlchemyEngine
from scripts.run_live_benchmark import prediction
async def evaluate(name,n,seed):
    engine=ChatAlchemyEngine(use_conflict=name!='no_conflict',use_verifier=name!='no_verifier');oracle=LiveOracle();scores=[];supports=[]
    try:
        for case in generate_cases(n,seed):gold=await oracle.execute(case);res=await engine.answer(case.question);scores.append(score_value(gold.kind,prediction(case,res),gold.value));supports.append(res.supported_claim_rate)
    finally:await asyncio.gather(engine.close(),oracle.close())
    return {"system":name,"n":n,"mean_task_score":statistics.mean(scores),"mean_supported_claim_rate":statistics.mean(supports)}
async def main():
    p=argparse.ArgumentParser();p.add_argument('--n',type=int,default=64);p.add_argument('--seed',type=int,default=1729);p.add_argument('--out',default='benchmark/ablations.json');a=p.parse_args();rows=[await evaluate(name,a.n,a.seed) for name in ['full','no_conflict','no_verifier']];Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
if __name__=='__main__':asyncio.run(main())
