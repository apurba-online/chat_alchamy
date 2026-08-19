from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from chatalchemy.benchmark.generator import ENTITY_POOLS
from chatalchemy.sources import RxNormSource


def _norm(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _summary(rows: list[dict]) -> dict:
    resolved = [row for row in rows if row["resolved"]]
    latencies = [float(row["latency_ms"]) for row in rows]
    return {
        "n": len(rows),
        "resolution_rate": statistics.mean(bool(row["resolved"]) for row in rows) if rows else 0.0,
        "exact_canonical_accuracy": statistics.mean(bool(row["exact_match"]) for row in rows) if rows else 0.0,
        "accuracy_on_resolved": statistics.mean(bool(row["exact_match"]) for row in resolved) if resolved else None,
        "no_normalization_exact_accuracy": statistics.mean(bool(row["raw_alias_matches_generic"]) for row in rows) if rows else 0.0,
        "median_latency_ms": statistics.median(latencies) if latencies else 0.0,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate live RxNorm alias-to-canonical normalization used by ChatAlchemy.")
    parser.add_argument("--split", choices=["dev", "test", "stress", "all"], default="all")
    parser.add_argument("--out", default="benchmark/entity-normalization.json")
    args = parser.parse_args()

    selected_splits = list(ENTITY_POOLS) if args.split == "all" else [args.split]
    source = RxNormSource()
    rows: list[dict] = []
    started = datetime.now(timezone.utc)
    try:
        for split in selected_splits:
            for alias, expected_generic in ENTITY_POOLS[split].aliases:
                t0 = time.perf_counter()
                evidence = []
                error = None
                try:
                    evidence = await source.resolve(alias)
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                latency_ms = (time.perf_counter() - t0) * 1000
                predicted = str(evidence[0].value) if evidence else None
                rows.append(
                    {
                        "split": split,
                        "alias": alias,
                        "expected_generic": expected_generic,
                        "predicted_generic": predicted,
                        "resolved": predicted is not None,
                        "exact_match": _norm(predicted) == _norm(expected_generic) if predicted is not None else False,
                        "raw_alias_matches_generic": _norm(alias) == _norm(expected_generic),
                        "rxcui": evidence[0].qualifiers.get("rxcui") if evidence else None,
                        "source_record_id": evidence[0].source_record_id if evidence else None,
                        "latency_ms": latency_ms,
                        "error": error,
                    }
                )
    finally:
        await source.close()

    result = {
        "schema": "ChatAlchemyEntityNormalizationEval/v1",
        "run": {
            "started_at_utc": started.isoformat(),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "split_filter": args.split,
            "source": "live RxNorm/RxNav",
        },
        "summary": _summary(rows),
        "by_split": {
            split: _summary([row for row in rows if row["split"] == split])
            for split in selected_splits
        },
        "cases": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"run": result["run"], "summary": result["summary"], "by_split": result["by_split"]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
