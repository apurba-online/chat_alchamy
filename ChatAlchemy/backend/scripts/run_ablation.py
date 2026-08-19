from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from pathlib import Path

from chatalchemy.benchmark import LiveOracle, generate_cases, score_value
from chatalchemy.reasoning import ChatAlchemyEngine
from scripts.run_live_benchmark import prediction, user_evidence

VARIANTS = {
    "full": {},
    "no_normalization": {"use_normalization": False},
    "no_deterministic_join": {"use_deterministic_join": False},
    "no_conflict": {"use_conflict": False},
    "no_verifier": {"use_verifier": False},
}


async def evaluate(name: str, n: int, seed: int):
    engine = ChatAlchemyEngine(**VARIANTS[name])
    oracle = LiveOracle()
    case_rows = []
    try:
        for case in generate_cases(n, seed):
            try:
                gold = await oracle.execute(case)
            except Exception as exc:
                case_rows.append(
                    {
                        "id": case.id,
                        "family": case.family,
                        "oracle_available": False,
                        "oracle_error": f"{type(exc).__name__}: {exc}",
                        "task_score": None,
                    }
                )
                continue
            response = await engine.answer(case.question, user_evidence=user_evidence(case))
            case_rows.append(
                {
                    "id": case.id,
                    "family": case.family,
                    "oracle_available": True,
                    "task_score": score_value(gold.kind, prediction(case, response), gold.value),
                    "supported_claim_rate": response.supported_claim_rate,
                    "execution_ok": all(trace.ok for trace in response.traces) if response.traces else False,
                }
            )
    finally:
        await asyncio.gather(engine.close(), oracle.close())

    scored = [row for row in case_rows if row.get("task_score") is not None]
    by_family = {}
    for family in sorted({row["family"] for row in case_rows}):
        subset = [row for row in case_rows if row["family"] == family]
        family_scored = [row["task_score"] for row in subset if row.get("task_score") is not None]
        by_family[family] = {
            "n": len(subset),
            "oracle_coverage": sum(row["oracle_available"] for row in subset) / len(subset),
            "mean_task_score": statistics.mean(family_scored) if family_scored else None,
        }
    return {
        "system": name,
        "n": len(case_rows),
        "oracle_coverage": len(scored) / len(case_rows) if case_rows else 0,
        "mean_task_score": statistics.mean(row["task_score"] for row in scored) if scored else None,
        "mean_supported_claim_rate": statistics.mean(
            row.get("supported_claim_rate", 0.0) for row in scored
        ) if scored else None,
        "execution_success": statistics.mean(
            bool(row.get("execution_ok")) for row in scored
        ) if scored else None,
        "by_family": by_family,
        "cases": case_rows,
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=128)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--out", default="benchmark/ablations.json")
    parser.add_argument("--variants", nargs="*", choices=list(VARIANTS), default=list(VARIANTS))
    args = parser.parse_args()
    rows = [await evaluate(name, args.n, args.seed) for name in args.variants]
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2))
    print(json.dumps([{k: v for k, v in row.items() if k != "cases"} for row in rows], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
