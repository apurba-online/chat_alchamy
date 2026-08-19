from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from chatalchemy.benchmark import LiveOracle, SNAPSHOT_SCHEMA, generate_cases, select_cases, validate_cases
from scripts.run_live_benchmark import stable_snapshot_hash

PUBLIC_BENCHMARK_N = 1500


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--split", choices=["all", "dev", "test", "stress"], default="test")
    parser.add_argument("--difficulty", choices=["all", "easy", "medium", "hard"], default="all")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--out", default="benchmark/oracle-snapshot.json")
    args = parser.parse_args()

    all_cases = generate_cases(PUBLIC_BENCHMARK_N, args.seed)
    manifest = validate_cases(all_cases)
    cases = select_cases(
        all_cases,
        split=args.split,
        difficulty=args.difficulty,
        limit=None if args.full else args.limit,
        num_shards=args.num_shards,
        shard_index=args.shard_index,
    )
    if not cases:
        raise SystemExit("No cases matched the requested snapshot selection")

    oracle = LiveOracle()
    rows = []
    started = datetime.now(timezone.utc)
    try:
        for case in cases:
            result = None
            error = None
            try:
                result = await oracle.execute(case)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            source_records = result.source_records if result is not None else []
            rows.append(
                {
                    "id": case.id,
                    "task_signature": case.task_signature,
                    "split": case.split,
                    "difficulty": case.difficulty,
                    "family": case.family,
                    "oracle_available": result is not None,
                    "oracle_error": error,
                    "kind": result.kind if result is not None else case.output_kind,
                    "value": result.value if result is not None else None,
                    "source_records": source_records,
                    "snapshot_hash": stable_snapshot_hash(result.kind, result.value, source_records) if result is not None else None,
                }
            )
    finally:
        await oracle.close()

    payload = {
        "schema": SNAPSHOT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "started_at_utc": started.isoformat(),
        "benchmark": {**manifest, "seed": args.seed},
        "selection": {
            "split_filter": args.split,
            "difficulty_filter": args.difficulty,
            "full_selection": args.full,
            "limit": None if args.full else args.limit,
            "num_shards": args.num_shards,
            "shard_index": args.shard_index,
        },
        "oracle_coverage": sum(row["oracle_available"] for row in rows) / len(rows),
        "cases": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"schema": payload["schema"], "benchmark": payload["benchmark"], "selection": payload["selection"], "oracle_coverage": payload["oracle_coverage"], "case_count": len(rows)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
