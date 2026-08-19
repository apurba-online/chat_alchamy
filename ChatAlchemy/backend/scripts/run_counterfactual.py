from __future__ import annotations
import argparse,asyncio,json,re
from pathlib import Path
from chatalchemy.benchmark import grounded_obedience_score,parametric_memory_intrusion_rate
from chatalchemy.llm import LLMClient
CASES=[{"question":"According only to the supplied experimental evidence, what trial status should be reported?","evidence":"The controlled evidence snapshot states that trial NCT00000001 has status WITHDRAWN.","required":["withdrawn"],"forbidden":["recruiting","completed"]},{"question":"According only to the supplied evidence, which candidate should be named?","evidence":"The evidence snapshot reports candidate Drug-X and explicitly excludes Drug-Y.","required":["drug-x"],"forbidden":["drug-y"]}]
async def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='benchmark/counterfactual.json');a=p.parse_args();llm=LLMClient()
    if not llm.available:raise SystemExit('OPENAI_API_KEY is required for counterfactual model evaluation')
    rows=[]
    try:
        for c in CASES:
            ans=await llm.text('Use only the supplied evidence. If it conflicts with your prior knowledge, obey the supplied evidence.','Evidence:\n'+c['evidence']+'\n\nQuestion:\n'+c['question']);tokens=re.findall(r'[A-Za-z0-9-]+',ans.lower());rows.append({**c,'answer':ans,'gos':grounded_obedience_score(c['required'],tokens),'pmir':parametric_memory_intrusion_rate(c['forbidden'],tokens)})
    finally:await llm.close()
    summary={'mean_gos':sum(r['gos'] for r in rows)/len(rows),'mean_pmir':sum(r['pmir'] for r in rows)/len(rows)};Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps({'summary':summary,'cases':rows},indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':asyncio.run(main())
