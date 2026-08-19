from __future__ import annotations
import argparse,asyncio,hashlib,json,statistics,time
from pathlib import Path
from chatalchemy.benchmark import LiveOracle,generate_cases,score_value
from chatalchemy.reasoning import ChatAlchemyEngine
def prediction(case,response):
    f=case.family
    if f=="identity":e=next((x for x in response.evidence if x.predicate=="canonical_drug_identity"),None);return str(e.value).lower() if e else None
    if f=="label":return sorted({str(e.source_record_id) for e in response.evidence if e.predicate=="dailymed_label_record" and e.source_record_id})
    if f=="approval":return sorted({str(e.value) for e in response.evidence if e.predicate=="fda_application_record"})
    if f=="trials":return sorted({str(e.value) for e in response.evidence if e.predicate=="clinical_trial" and e.value})
    if f=="target":return sorted({str(e.value).lower() for e in response.evidence if e.predicate=="targeting_drug"})
    if f=="gene":return sorted({f"{e.predicate}:{str(e.value).lower()}" for e in response.evidence if e.predicate in {"gene_disease_association","known_drug"}})
    if f=="compound":e=next((x for x in response.evidence if x.predicate=="compound_properties"),None);return e.value if e else {}
    if f=="cross":return sorted({str(row[0]).lower() for row in (response.table.rows if response.table else [])})
async def main():
    p=argparse.ArgumentParser();p.add_argument("--n",type=int,default=24);p.add_argument("--seed",type=int,default=1729);p.add_argument("--out",default="benchmark/results.json");p.add_argument("--full",action="store_true");a=p.parse_args();n=1500 if a.full else a.n;cases=generate_cases(n,a.seed);engine=ChatAlchemyEngine();oracle=LiveOracle();rows=[]
    try:
        for case in cases:
            started=time.perf_counter();gold=await oracle.execute(case);response=await engine.answer(case.question);pred=prediction(case,response);score=score_value(gold.kind,pred,gold.value);snapshot=json.dumps(gold.source_records,sort_keys=True).encode();rows.append({"id":case.id,"family":case.family,"question":case.question,"expected_operation":case.expected_operation,"planned_intent":response.plan.intent,"routing_correct":response.plan.intent==case.expected_operation,"task_score":score,"supported_claim_rate":response.supported_claim_rate,"execution_ok":all(t.ok for t in response.traces) if response.traces else False,"latency_ms":(time.perf_counter()-started)*1000,"oracle":gold.value,"prediction":pred,"oracle_source_records":gold.source_records,"oracle_snapshot_hash":hashlib.sha256(snapshot).hexdigest(),"agent_source_records":[{"source":e.source,"record":e.source_record_id,"retrieved_at":e.retrieved_at} for e in response.evidence],"warnings":response.warnings})
    finally:await asyncio.gather(engine.close(),oracle.close())
    summary={"n":len(rows),"routing_accuracy":sum(r["routing_correct"] for r in rows)/len(rows) if rows else 0,"mean_task_score":statistics.mean(r["task_score"] for r in rows) if rows else 0,"execution_success":sum(r["execution_ok"] for r in rows)/len(rows) if rows else 0,"mean_supported_claim_rate":statistics.mean(r["supported_claim_rate"] for r in rows) if rows else 0,"median_latency_ms":statistics.median(r["latency_ms"] for r in rows) if rows else 0,"p95_latency_ms":sorted(r["latency_ms"] for r in rows)[max(0,int(.95*len(rows))-1)] if rows else 0};by_family={}
    for f in sorted({r['family'] for r in rows}):
        subset=[r for r in rows if r['family']==f];by_family[f]={"n":len(subset),"mean_task_score":statistics.mean(r['task_score'] for r in subset),"routing_accuracy":statistics.mean(r['routing_correct'] for r in subset)}
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({"summary":summary,"by_family":by_family,"cases":rows},indent=2));print(json.dumps({"summary":summary,"by_family":by_family},indent=2))
if __name__=="__main__":asyncio.run(main())
