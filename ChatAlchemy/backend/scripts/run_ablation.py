from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path

from chatalchemy.benchmark import EvaluationOracle, generate_cases, score_value, select_cases, validate_cases
from chatalchemy.reasoning import ChatAlchemyEngine
from scripts.run_live_benchmark import prediction, provenance_record_f1, user_evidence

VARIANTS = {
    "full": {},
    "no_normalization": {"use_normalization": False},
    "no_deterministic_join": {"use_deterministic_join": False},
    "no_conflict": {"use_conflict": False},
    "no_verifier": {"use_verifier": False},
}


def _aggregate(rows: list[dict]) -> dict:
    scored = [float(row["task_score"]) for row in rows if row.get("task_score") is not None]
    claimed = [row for row in rows if int(row.get("claim_count", 0)) > 0]
    provenance = [float(row["provenance_record_f1"]) for row in rows if row.get("provenance_record_f1") is not None]
    return {
        "n": len(rows),
        "oracle_coverage": statistics.mean(bool(row["oracle_available"]) for row in rows) if rows else 0.0,
        "mean_task_score": statistics.mean(scored) if scored else None,
        "execution_success": statistics.mean(bool(row["execution_ok"]) for row in rows) if rows else 0.0,
        "claiming_rate": len(claimed) / len(rows) if rows else 0.0,
        "mean_supported_claim_rate_on_claimed": statistics.mean(float(row["supported_claim_rate"]) for row in claimed) if claimed else None,
        "mean_provenance_record_f1": statistics.mean(provenance) if provenance else None,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--split", choices=["dev", "test", "stress", "all"], default="dev")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard", "all"], default="all")
    parser.add_argument("--limit", type=int, default=128, help="0 means all cases after filtering/sharding")
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--oracle-snapshot", default=None)
    parser.add_argument("--variants", nargs="*", choices=list(VARIANTS), default=list(VARIANTS))
    parser.add_argument("--out", default="benchmark/ablations.json")
    args = parser.parse_args()

    all_cases = generate_cases(1500, args.seed)
    manifest = validate_cases(all_cases)
    cases = select_cases(
        all_cases,
        split=args.split,
        difficulty=args.difficulty,
        limit=None if args.limit == 0 else args.limit,
        num_shards=args.num_shards,
        shard_index=args.shard_index,
    )
    if not cases:
        raise SystemExit("No benchmark cases matched the requested filters")

    engines = {name: ChatAlchemyEngine(**VARIANTS[name]) for name in args.variants}
    oracle = EvaluationOracle(
        benchmark_fingerprint=manifest["fingerprint_sha256"],
        snapshot_path=args.oracle_snapshot,
    )
    rows_by_variant: dict[str, list[dict]] = {name: [] for name in args.variants}
    started = datetime.now(timezone.utc)
    try:
        for case in cases:
            gold, oracle_error = await oracle.get(case)
            for name, engine in engines.items():
                response = await engine.answer(case.question, max_results=args.max_results, user_evidence=user_evidence(case))
                pred = prediction(case, response)
                score = score_value(gold.kind, pred, gold.value) if gold is not None else None
                oracle_records = gold.source_records if gold is not None else []
                agent_records = [
                    {"source": evidence.source, "record": evidence.source_record_id}
                    for evidence in response.evidence
                ]
                rows_by_variant[name].append(
                    {
                        "id": case.id,
                        "task_signature": case.task_signature,
                        "split": case.split,
                        "difficulty": case.difficulty,
                        "family": case.family,
                        "task_score": score,
                        "oracle_available": gold is not None,
                        "oracle_error": oracle_error,
                        "oracle": gold.value if gold is not None else None,
                        "prediction": pred,
                        "execution_ok": all(trace.ok for trace in response.traces) if response.traces else False,
                        "supported_claim_rate": response.supported_claim_rate,
                        "claim_count": len(response.claims),
                        "evidence_count": len(response.evidence),
                        "api_calls": len(response.traces),
                        "provenance_record_f1": provenance_record_f1(oracle_records, agent_records) if gold is not None else None,
                    }
                )
    finally:
        await asyncio.gather(*(engine.close() for engine in engines.values()), oracle.close(), return_exceptions=True)

    systems = []
    for name in args.variants:
        rows = rows_by_variant[name]
        systems.append(
            {
                "system": name,
                "config": VARIANTS[name],
                "summary": _aggregate(rows),
                "by_family": {
                    family: _aggregate([row for row in rows if row["family"] == family])
                    for family in sorted({row["family"] for row in rows})
                },
                "cases": rows,
            }
        )

    result = {
        "schema": "ChatAlchemyAblationRun/v3",
        "run": {
            "started_at_utc": started.isoformat(),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "git_sha": os.getenv("GITHUB_SHA") or os.getenv("VERCEL_GIT_COMMIT_SHA"),
            "seed": args.seed,
            "split_filter": args.split,
            "difficulty_filter": args.difficulty,
            "limit": args.limit,
            "num_shards": args.num_shards,
            "shard_index": args.shard_index,
            "max_results": args.max_results,
            "variants": args.variants,
            **oracle.metadata(),
            "oracle_snapshot_policy": "one oracle result per case shared across all variants",
        },
        "benchmark": {**manifest, "seed": args.seed},
        "systems": systems,
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"run": result["run"], "benchmark": result["benchmark"], "systems": [{"system": item["system"], "summary": item["summary"]} for item in systems]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
