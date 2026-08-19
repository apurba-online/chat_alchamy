from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import statistics
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from chatalchemy.benchmark import LiveOracle, generate_cases, score_value, validate_cases
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
    if family in {"cross", "user_approval", "user_trials", "user_target"}:
        return sorted({str(row[0]).lower() for row in (response.table.rows if response.table else [])})
    return None


def user_evidence(case):
    if not case.family.startswith("user_"):
        return []
    return [
        {
            "subject": name,
            "predicate": "candidate_drug",
            "value": name,
            "qualifiers": {"source": "benchmark uploaded list"},
            "id": f"candidate-{index}",
        }
        for index, name in enumerate(case.params["candidates"])
    ]


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


def _source_key(value: object) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def provenance_record_f1(oracle_records, agent_records) -> float:
    gold = {
        (_source_key(item.get("source")), str(item.get("record")))
        for item in oracle_records
        if item.get("record") is not None
    }
    pred = {
        (_source_key(item.get("source")), str(item.get("record")))
        for item in agent_records
        if item.get("record") is not None
    }
    if not gold and not pred:
        return 1.0
    if not gold or not pred:
        return 0.0
    tp = len(gold & pred)
    precision = tp / len(pred)
    recall = tp / len(gold)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return ordered[index]


def _aggregate(rows: list[dict]) -> dict:
    scored = [float(r["task_score"]) for r in rows if r.get("task_score") is not None]
    latencies = [float(r["latency_ms"]) for r in rows]
    claimed = [r for r in rows if int(r.get("claim_count", 0)) > 0]
    provenance = [float(r["provenance_record_f1"]) for r in rows if r.get("provenance_record_f1") is not None]
    return {
        "n": len(rows),
        "oracle_coverage": statistics.mean(bool(r["oracle_available"]) for r in rows) if rows else 0.0,
        "routing_accuracy": statistics.mean(bool(r["routing_correct"]) for r in rows) if rows else 0.0,
        "mean_task_score": statistics.mean(scored) if scored else None,
        "execution_success": statistics.mean(bool(r["execution_ok"]) for r in rows) if rows else 0.0,
        "claiming_rate": len(claimed) / len(rows) if rows else 0.0,
        "mean_supported_claim_rate_on_claimed": statistics.mean(float(r["supported_claim_rate"]) for r in claimed) if claimed else None,
        "fully_supported_claim_case_rate": statistics.mean(
            int(r.get("claim_count", 0)) > 0 and float(r["supported_claim_rate"]) == 1.0 for r in rows
        ) if rows else 0.0,
        "mean_provenance_record_f1": statistics.mean(provenance) if provenance else None,
        "median_latency_ms": statistics.median(latencies) if latencies else 0.0,
        "p95_latency_ms": _percentile(latencies, 0.95),
        "mean_api_calls": statistics.mean(int(r["api_calls"]) for r in rows) if rows else 0.0,
        "mean_evidence_items": statistics.mean(int(r["evidence_count"]) for r in rows) if rows else 0.0,
    }


def _group(rows: list[dict], key: str) -> dict[str, dict]:
    return {
        value: _aggregate([row for row in rows if str(row.get(key)) == value])
        for value in sorted({str(row.get(key)) for row in rows})
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=24)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--out", default="benchmark/results.json")
    parser.add_argument("--full", action="store_true", help="Run the full 1,500-case public benchmark")
    parser.add_argument("--split", choices=["all", "dev", "test", "stress"], default="all")
    parser.add_argument("--difficulty", choices=["all", "easy", "medium", "hard"], default="all")
    parser.add_argument("--max-results", type=int, default=20)
    args = parser.parse_args()

    n = 1500 if args.full else args.n
    all_cases = generate_cases(n, args.seed)
    manifest = validate_cases(all_cases)
    cases = [
        case
        for case in all_cases
        if (args.split == "all" or case.split == args.split)
        and (args.difficulty == "all" or case.difficulty == args.difficulty)
    ]
    if not cases:
        raise SystemExit("No benchmark cases matched the requested split/difficulty filters")

    run_started = datetime.now(timezone.utc)
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

            response = await engine.answer(case.question, max_results=args.max_results, user_evidence=user_evidence(case))
            pred = prediction(case, response)
            score = score_value(gold.kind, pred, gold.value) if gold is not None else None
            source_records = gold.source_records if gold is not None else []
            snapshot_hash = stable_snapshot_hash(gold.kind, gold.value, source_records) if gold is not None else None
            agent_source_records = [
                {"source": e.source, "record": e.source_record_id, "retrieved_at": e.retrieved_at}
                for e in response.evidence
            ]
            rows.append(
                {
                    "id": case.id,
                    "split": case.split,
                    "difficulty": case.difficulty,
                    "family": case.family,
                    "template_id": case.template_id,
                    "primary_entity": case.primary_entity,
                    "primary_entity_type": case.primary_entity_type,
                    "question": case.question,
                    "required_sources": case.sources,
                    "expected_operation": case.expected_operation,
                    "planned_intent": response.plan.intent,
                    "routing_correct": response.plan.intent == case.expected_operation,
                    "task_score": score,
                    "supported_claim_rate": response.supported_claim_rate,
                    "execution_ok": all(t.ok for t in response.traces) if response.traces else False,
                    "latency_ms": (time.perf_counter() - started) * 1000,
                    "api_calls": len(response.traces),
                    "evidence_count": len(response.evidence),
                    "claim_count": len(response.claims),
                    "oracle_available": oracle_available,
                    "oracle_error": oracle_error,
                    "oracle": gold.value if gold is not None else None,
                    "prediction": pred,
                    "oracle_source_records": source_records,
                    "oracle_snapshot_hash": snapshot_hash,
                    "agent_source_records": agent_source_records,
                    "provenance_record_f1": provenance_record_f1(source_records, agent_source_records) if gold is not None else None,
                    "warnings": response.warnings,
                    "params": case.params,
                }
            )
    finally:
        await asyncio.gather(engine.close(), oracle.close())

    run_finished = datetime.now(timezone.utc)
    result = {
        "schema": "ChatAlchemyBenchmarkRun/v2",
        "run": {
            "started_at_utc": run_started.isoformat(),
            "finished_at_utc": run_finished.isoformat(),
            "wall_clock_seconds": (run_finished - run_started).total_seconds(),
            "git_sha": os.getenv("GITHUB_SHA") or os.getenv("VERCEL_GIT_COMMIT_SHA"),
            "seed": args.seed,
            "requested_n": n,
            "split_filter": args.split,
            "difficulty_filter": args.difficulty,
            "max_results": args.max_results,
            "system": "ChatAlchemy-full",
        },
        "benchmark": {**manifest, "seed": args.seed},
        "summary": _aggregate(rows),
        "by_split": _group(rows, "split"),
        "by_difficulty": _group(rows, "difficulty"),
        "by_family": _group(rows, "family"),
        "error_counts": dict(Counter(row["oracle_error"] for row in rows if row.get("oracle_error"))),
        "cases": rows,
    }

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("run", "benchmark", "summary", "by_split", "by_difficulty", "by_family")}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
