from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.run_live_benchmark import aggregate_rows, group_rows


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError(f"{path} is not a benchmark-run JSON object")
    return payload


def merge(paths: list[Path], expected_shards: int | None = None) -> dict:
    if not paths:
        raise ValueError("no shard files supplied")
    runs = [_load(path) for path in paths]
    fingerprints = {run.get("benchmark", {}).get("fingerprint_sha256") for run in runs}
    fingerprints.discard(None)
    if len(fingerprints) != 1:
        raise ValueError(f"benchmark fingerprint mismatch across shards: {sorted(fingerprints)}")

    shard_pairs = {
        (run.get("run", {}).get("shard_index"), run.get("run", {}).get("num_shards"))
        for run in runs
    }
    num_shards_values = {pair[1] for pair in shard_pairs}
    if len(num_shards_values) != 1:
        raise ValueError(f"num_shards mismatch: {sorted(num_shards_values)}")
    declared_shards = next(iter(num_shards_values))
    if expected_shards is not None and declared_shards != expected_shards:
        raise ValueError(f"expected {expected_shards} shards but files declare {declared_shards}")
    indexes = {pair[0] for pair in shard_pairs}
    if indexes != set(range(declared_shards)):
        raise ValueError(f"missing or unexpected shard indexes: {sorted(indexes)}")

    benchmark_keys = ("schema", "case_count", "fingerprint_sha256")
    first_benchmark = runs[0]["benchmark"]
    for run in runs[1:]:
        for key in benchmark_keys:
            if run["benchmark"].get(key) != first_benchmark.get(key):
                raise ValueError(f"benchmark metadata mismatch for {key}")

    invariant_run_keys = ("seed", "benchmark_n", "split_filter", "difficulty_filter", "max_results", "system")
    first_meta = runs[0]["run"]
    for run in runs[1:]:
        for key in invariant_run_keys:
            if run["run"].get(key) != first_meta.get(key):
                raise ValueError(f"run configuration mismatch for {key}")

    rows = [row for run in runs for row in run["cases"]]
    ids = [row.get("id") for row in rows]
    duplicate_ids = sorted(case_id for case_id, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        raise ValueError(f"duplicate benchmark IDs across shards: {duplicate_ids[:10]}")
    rows.sort(key=lambda row: str(row.get("id")))

    merged = {
        "schema": "ChatAlchemyBenchmarkRunMerged/v1",
        "run": {
            **{key: first_meta.get(key) for key in invariant_run_keys},
            "num_shards": declared_shards,
            "merged_case_count": len(rows),
            "shard_files": [path.name for path in paths],
            "component_started_at_utc": [run["run"].get("started_at_utc") for run in runs],
            "component_finished_at_utc": [run["run"].get("finished_at_utc") for run in runs],
            "component_git_sha": sorted({str(run["run"].get("git_sha")) for run in runs}),
        },
        "benchmark": first_benchmark,
        "summary": aggregate_rows(rows),
        "by_split": group_rows(rows, "split"),
        "by_difficulty": group_rows(rows, "difficulty"),
        "by_family": group_rows(rows, "family"),
        "error_counts": dict(Counter(row.get("oracle_error") for row in rows if row.get("oracle_error"))),
        "cases": rows,
    }
    return merged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="Shard result JSON files")
    parser.add_argument("--expected-shards", type=int, default=None)
    parser.add_argument("--out", default="benchmark/merged-results.json")
    args = parser.parse_args()
    result = merge([Path(path) for path in args.paths], args.expected_shards)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"run": result["run"], "summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
