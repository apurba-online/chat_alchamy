from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import statistics
import time
from pathlib import Path

from chatalchemy.benchmark import LiveOracle, generate_cases, score_value
from chatalchemy.reasoning import ChatAlchemyEngine


def prediction(case, response):
    family = case.family
    if family == "identity":
        evidence = next((x for x in response.evidence if x.predicate == "canonical_drug_identity"), None)
        return str(evidence.value).lower() if evidence else None
    if family == "label":
        return sorted({str(e.source_record_id) for e in response.evidence if e.predicate == "dailymed_label_record" and e.source_record_id})
    if family == "approval":
        return sorted({str(e.value) for e in response.evidence if e.predicate == "fda_application_record"})
    if family == "trials":
        return sorted({str(e.value) for e in response.evidence if e.predicate == "clinical_trial" and e.value})
    if family == "target":
        return sorted({str(e.value).lower() for e in response.evidence if e.predicate == "targeting_drug"})
    if family == "gene":
        return sorted({f"{e.predicate}:{str(e.value).lower()}" for e in response.evidence if e.predicate in {"gene_disease_association", "known_drug"}})
    if family == "compound":
        evidence = next((x for x in response.evidence if x.predicate == "compound_properties"), None)
        return evidence.value if evidence else {}
    if family == "cross":
        return sorted({str(row[0]).lower() for row in (response.table.rows if response.table else [])})
    return None


def stable_snapshot_hash(kind, value, records):
    payload = {
        "kind": kind,
        "value": value,
        "records": sorted(
            ({"source": r.get("source"), "record": r.get("record")} for r in records),
            key=lambda x: (str(x.get("source")), str(x.get("record"))),
        ),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=24)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--out", default="benchmark/results.json")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    n = 1500 if args.full else args.n
    cases = generate_cases(n, args.seed)
    engine = ChatAlchemyEngine()
    oracle = LiveOracle()
    rows = []
    try:
        for case in cases:
            started = time.perf_counter()
            oracle_available = True
            oracle_error = None
            gold = None
            try:
                gold = await oracle.execute(case)
            except Exception as exc:
                oracle_available = False
                oracle_error = f"{type(exc).__name__}: {exc}"

            response = await engine.answer(case.question)
            pred = prediction(case, response)
            score = score_value(gold.kind, pred, gold.value) if gold is not None else None
            source_records = gold.source_records if gold is not None else []
            snapshot_hash = stable_snapshot_hash(gold.kind, gold.value, source_records) if gold is not None else None
            rows.append(
                {
                    "id": case.id,
                    "family": case.family,
                    "question": case.question,
                    "expected_operation": case.expected_operation,
                    "planned_intent": response.plan.intent,
                    "routing_correct": response.plan.intent == case.expected_operation,
                    "task_score": score,
                    "supported_claim_rate": response.supported_claim_rate,
                    "execution_ok": all(t.ok for t in response.traces) if response.traces else False,
                    "latency_ms": (time.perf_counter() - started) * 1000,
                    "oracle_available": oracle_available,
                    "oracle_error": oracle_error,
                    "oracle": gold.value if gold is not None else None,
                    "prediction": pred,
                    "oracle_source_records": source_records,
                    "oracle_snapshot_hash": snapshot_hash,
                    "agent_source_records": [
                        {"source": e.source, "record": e.source_record_id, "retrieved_at": e.retrieved_at}
                        for e in response.evidence
                    ],
                    "warnings": response.warnings,
                }
            )
    finally:
        await asyncio.gather(engine.close(), oracle.close())

    scored = [r["task_score"] for r in rows if r["task_score"] is not None]
    summary = {
        "n": len(rows),
        "oracle_coverage": sum(r["oracle_available"] for r in rows) / len(rows) if rows else 0,
        "routing_accuracy": sum(r["routing_correct"] for r in rows) / len(rows) if rows else 0,
        "mean_task_score": statistics.mean(scored) if scored else None,
        "execution_success": sum(r["execution_ok"] for r in rows) / len(rows) if rows else 0,
        "mean_supported_claim_rate": statistics.mean(r["supported_claim_rate"] for r in rows) if rows else 0,
        "median_latency_ms": statistics.median(r["latency_ms"] for r in rows) if rows else 0,
        "p95_latency_ms": sorted(r["latency_ms"] for r in rows)[max(0, int(0.95 * len(rows)) - 1)] if rows else 0,
    }
    by_family = {}
    for family in sorted({r["family"] for r in rows}):
        subset = [r for r in rows if r["family"] == family]
        family_scores = [r["task_score"] for r in subset if r["task_score"] is not None]
        by_family[family] = {
            "n": len(subset),
            "oracle_coverage": sum(r["oracle_available"] for r in subset) / len(subset),
            "mean_task_score": statistics.mean(family_scores) if family_scores else None,
            "routing_accuracy": statistics.mean(r["routing_correct"] for r in subset),
            "execution_success": statistics.mean(r["execution_ok"] for r in subset),
        }

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"summary": summary, "by_family": by_family, "cases": rows}, indent=2))
    print(json.dumps({"summary": summary, "by_family": by_family}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
