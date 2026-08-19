from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from chatalchemy.benchmark import LiveOracle, generate_cases, score_value, select_cases, validate_cases
from chatalchemy.evaluation import FaultInjectedSource
from chatalchemy.reasoning import ChatAlchemyEngine
from scripts.run_live_benchmark import prediction, user_evidence

PUBLIC_BENCHMARK_N = 1500
METHOD_BY_SOURCE = {
    "rxnorm": {"resolve"},
    "dailymed": {"label_records"},
    "openfda": {"approval_records"},
    "clinicaltrials": {"search_trials"},
    "chembl": {"target_drugs"},
    "opentargets": {"gene_details", "disease_genes"},
    "pubchem": {"compound"},
}


def _aggregate(rows):
    scored = [float(r["task_score"]) for r in rows if r.get("task_score") is not None]
    claimed = [r for r in rows if int(r.get("claim_count", 0)) > 0]
    return {
        "n": len(rows),
        "oracle_coverage": statistics.mean(bool(r["oracle_available"]) for r in rows) if rows else 0.0,
        "mean_task_score": statistics.mean(scored) if scored else None,
        "claiming_rate": len(claimed) / len(rows) if rows else 0.0,
        "mean_supported_claim_rate_on_claimed": statistics.mean(float(r["supported_claim_rate"]) for r in claimed) if claimed else None,
        "failure_trace_rate": statistics.mean(bool(r["failure_trace_detected"]) for r in rows) if rows else 0.0,
        "qualified_or_abstained_rate": statistics.mean(bool(r["qualified_or_abstained"]) for r in rows) if rows else 0.0,
        "unsupported_claim_case_rate": statistics.mean(bool(r["unsupported_claim_case"]) for r in rows) if rows else 0.0,
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=sorted(METHOD_BY_SOURCE), required=True)
    parser.add_argument("--mode", choices=["exception", "empty"], default="exception")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--split", choices=["dev", "test", "stress", "all"], default="test")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard", "all"], default="all")
    parser.add_argument("--limit", type=int, default=150, help="0 means all selected cases requiring the source")
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--out", default="benchmark/failure-injection.json")
    args = parser.parse_args()

    all_cases = generate_cases(PUBLIC_BENCHMARK_N, args.seed)
    manifest = validate_cases(all_cases)
    cases = select_cases(
        all_cases,
        split=args.split,
        difficulty=args.difficulty,
        families=None,
        limit=None,
        num_shards=args.num_shards,
        shard_index=args.shard_index,
    )
    cases = [case for case in cases if args.source in case.sources]
    if args.limit != 0:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No cases require the selected source under the requested filters")

    engine = ChatAlchemyEngine()
    underlying = engine.sources[args.source]
    source_display_name = getattr(underlying, "name", args.source)
    engine.sources[args.source] = FaultInjectedSource(
        underlying,
        fail_methods=METHOD_BY_SOURCE[args.source],
        mode=args.mode,
    )
    oracle = LiveOracle()
    rows = []
    started = datetime.now(timezone.utc)
    try:
        for case in cases:
            gold = None
            oracle_error = None
            try:
                gold = await oracle.execute(case)
            except Exception as exc:
                oracle_error = f"{type(exc).__name__}: {exc}"

            response = await engine.answer(case.question, user_evidence=user_evidence(case))
            pred = prediction(case, response)
            score = score_value(gold.kind, pred, gold.value) if gold is not None else None
            failed_trace = any(
                trace.source == source_display_name and not trace.ok
                for trace in response.traces
            )
            unsupported = any(not claim.supported for claim in response.claims)
            qualified_or_abstained = bool(response.warnings) or not response.claims
            rows.append(
                {
                    "id": case.id,
                    "task_signature": case.task_signature,
                    "split": case.split,
                    "difficulty": case.difficulty,
                    "family": case.family,
                    "question": case.question,
                    "task_score": score,
                    "oracle_available": gold is not None,
                    "oracle_error": oracle_error,
                    "prediction": pred,
                    "oracle": gold.value if gold is not None else None,
                    "supported_claim_rate": response.supported_claim_rate,
                    "claim_count": len(response.claims),
                    "failure_trace_detected": failed_trace,
                    "qualified_or_abstained": qualified_or_abstained,
                    "unsupported_claim_case": unsupported,
                    "warnings": response.warnings,
                    "answer": response.answer,
                }
            )
    finally:
        await asyncio.gather(engine.close(), oracle.close())

    result = {
        "schema": "ChatAlchemyFailureInjection/v2",
        "run": {
            "source": args.source,
            "source_display_name": source_display_name,
            "mode": args.mode,
            "split_filter": args.split,
            "difficulty_filter": args.difficulty,
            "limit": args.limit,
            "num_shards": args.num_shards,
            "shard_index": args.shard_index,
            "seed": args.seed,
            "started_at_utc": started.isoformat(),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "benchmark": {**manifest, "seed": args.seed},
        "summary": _aggregate(rows),
        "cases": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"run": result["run"], "summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
