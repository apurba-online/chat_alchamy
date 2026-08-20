from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.run_model_baseline import _aggregate

SUPPORTED_SCHEMAS = {
    "ChatAlchemyModelBaselineRun/v4",
    "ChatAlchemyModelBaselineRun/v5",
    "ChatAlchemyModelBaselineRun/v6",
}


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError(f"{path} is not a model-baseline result")
    if payload.get("schema") not in SUPPORTED_SCHEMAS:
        raise ValueError(f"unexpected model-baseline schema in {path}: {payload.get('schema')}")
    return payload


def merge(paths: list[Path], expected_shards: int | None = None) -> dict:
    if not paths:
        raise ValueError("no model-baseline shards supplied")
    runs = [_load(path) for path in paths]

    schemas = {run.get("schema") for run in runs}
    if len(schemas) != 1:
        raise ValueError(f"model baseline schema mismatch: {sorted(schemas)}")

    fingerprints = {run.get("benchmark", {}).get("fingerprint_sha256") for run in runs}
    if len(fingerprints) != 1 or None in fingerprints:
        raise ValueError(f"benchmark fingerprint mismatch: {sorted(str(x) for x in fingerprints)}")

    num_shards_values = {run["run"].get("num_shards") for run in runs}
    if len(num_shards_values) != 1:
        raise ValueError(f"num_shards mismatch: {sorted(num_shards_values)}")
    declared = next(iter(num_shards_values))
    if expected_shards is not None and declared != expected_shards:
        raise ValueError(f"expected {expected_shards} shards, files declare {declared}")
    indexes = {run["run"].get("shard_index") for run in runs}
    if indexes != set(range(declared)):
        raise ValueError(f"missing or unexpected model shard indexes: {sorted(indexes)}")

    invariant_keys = (
        "mode", "model", "prompt_version", "seed", "split_filter", "difficulty_filter",
        "max_results", "max_tool_steps", "oracle_mode", "oracle_snapshot_file_sha256",
    )
    optional_invariants = (
        "latency_definition", "same_retrieval_latency_note", "provenance_definition",
    )
    first_meta = runs[0]["run"]
    for run in runs[1:]:
        for key in invariant_keys:
            if run["run"].get(key) != first_meta.get(key):
                raise ValueError(f"model baseline configuration mismatch for {key}")
        for key in optional_invariants:
            values = {item["run"].get(key) for item in runs}
            non_null = {value for value in values if value is not None}
            if len(non_null) > 1:
                raise ValueError(f"model baseline configuration mismatch for {key}")

    rows = [row for run in runs for row in run["cases"]]
    ids = [str(row.get("id")) for row in rows]
    duplicates = sorted(case_id for case_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate case IDs across model shards: {duplicates[:10]}")
    rows.sort(key=lambda row: str(row.get("id")))

    by_family = {
        family: _aggregate([row for row in rows if row.get("family") == family])
        for family in sorted({str(row.get("family")) for row in rows})
    }
    run_meta = {key: first_meta.get(key) for key in invariant_keys}
    for key in optional_invariants:
        if first_meta.get(key) is not None:
            run_meta[key] = first_meta.get(key)

    return {
        "schema": "ChatAlchemyModelBaselineRunMerged/v3",
        "source_schema": next(iter(schemas)),
        "run": {
            **run_meta,
            "num_shards": declared,
            "merged_case_count": len(rows),
            "shard_files": [path.name for path in paths],
            "component_started_at_utc": [run["run"].get("started_at_utc") for run in runs],
            "component_finished_at_utc": [run["run"].get("finished_at_utc") for run in runs],
            "component_git_sha": sorted({str(run["run"].get("git_sha")) for run in runs if run["run"].get("git_sha")}),
        },
        "benchmark": runs[0]["benchmark"],
        "summary": _aggregate(rows),
        "by_family": by_family,
        "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge and validate deterministic model-baseline shards.")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--expected-shards", type=int, default=None)
    parser.add_argument("--out", default="benchmark/model-baseline-merged.json")
    args = parser.parse_args()
    result = merge([Path(path) for path in args.paths], args.expected_shards)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"run": result["run"], "summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
