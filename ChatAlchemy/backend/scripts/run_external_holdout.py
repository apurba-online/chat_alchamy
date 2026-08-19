from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from chatalchemy.benchmark.external_holdout import load_external_holdout
from chatalchemy.benchmark.oracle import LiveOracle
from chatalchemy.benchmark.metrics import score_value
from chatalchemy.reasoning import ChatAlchemyEngine
from scripts.run_live_benchmark import prediction, user_evidence

VARIANTS = {
    "full": {},
    "no_normalization": {"use_normalization": False},
    "no_deterministic_join": {"use_deterministic_join": False},
    "no_conflict": {"use_conflict": False},
    "no_verifier": {"use_verifier": False},
}


def _summary(rows: list[dict]) -> dict:
    scored = [float(row["task_score"]) for row in rows if row.get("task_score") is not None]
    return {
        "n": len(rows),
        "oracle_coverage": statistics.mean(bool(row["oracle_available"]) for row in rows) if rows else 0.0,
        "mean_task_score": statistics.mean(scored) if scored else None,
        "execution_success": statistics.mean(bool(row["execution_ok"]) for row in rows) if rows else 0.0,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", required=True, help="Private independently authored holdout JSON")
    parser.add_argument("--limit", type=int, default=0, help="0 means all holdout cases")
    parser.add_argument("--variants", nargs="*", choices=list(VARIANTS), default=["full"])
    parser.add_argument("--out", default="benchmark/external-holdout-results.json")
    args = parser.parse_args()

    cases, manifest = load_external_holdout(args.holdout)
    if args.limit:
        cases = cases[: args.limit]
    engines = {name: ChatAlchemyEngine(**VARIANTS[name]) for name in args.variants}
    oracle = LiveOracle()
    rows_by_system = {name: [] for name in args.variants}
    started = datetime.now(timezone.utc)
    try:
        for case in cases:
            gold = None
            oracle_error = None
            try:
                gold = await oracle.execute(case)
            except Exception as exc:
                oracle_error = f"{type(exc).__name__}: {exc}"
            for name, engine in engines.items():
                response = await engine.answer(case.question, user_evidence=user_evidence(case))
                pred = prediction(case, response)
                score = score_value(gold.kind, pred, gold.value) if gold is not None else None
                rows_by_system[name].append({
                    "id": case.id,
                    "task_signature": case.task_signature,
                    "family": case.family,
                    "difficulty": case.difficulty,
                    "question": case.question,
                    "oracle_available": gold is not None,
                    "oracle_error": oracle_error,
                    "oracle": gold.value if gold is not None else None,
                    "prediction": pred,
                    "task_score": score,
                    "execution_ok": all(trace.ok for trace in response.traces) if response.traces else False,
                    "supported_claim_rate": response.supported_claim_rate,
                    "claim_count": len(response.claims),
                })
    finally:
        await asyncio.gather(*(engine.close() for engine in engines.values()), oracle.close(), return_exceptions=True)

    systems = [
        {
            "system": name,
            "config": VARIANTS[name],
            "summary": _summary(rows_by_system[name]),
            "by_family": {
                family: _summary([row for row in rows_by_system[name] if row["family"] == family])
                for family in sorted({row["family"] for row in rows_by_system[name]})
            },
            "cases": rows_by_system[name],
        }
        for name in args.variants
    ]
    result = {
        "schema": "ChatAlchemyExternalHoldoutRun/v1",
        "run": {
            "started_at_utc": started.isoformat(),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "holdout_path_recorded": Path(args.holdout).name,
            "limit": args.limit,
            "oracle_snapshot_policy": "one independent live oracle result per case shared across all system variants",
        },
        "holdout": manifest,
        "systems": systems,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"run": result["run"], "holdout": manifest, "systems": [{"system": item["system"], "summary": item["summary"]} for item in systems]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
