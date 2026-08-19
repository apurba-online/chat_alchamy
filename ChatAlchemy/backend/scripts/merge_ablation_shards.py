from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.run_ablation import _aggregate


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text())
    if payload.get("schema") != "ChatAlchemyAblationRun/v3" or not isinstance(payload.get("systems"), list):
        raise ValueError(f"{path} is not a current ablation result")
    return payload


def merge(paths: list[Path], expected_shards: int | None = None) -> dict:
    if not paths:
        raise ValueError("no ablation shards supplied")
    runs = [_load(path) for path in paths]
    fingerprints = {run["benchmark"].get("fingerprint_sha256") for run in runs}
    if len(fingerprints) != 1:
        raise ValueError("benchmark fingerprint mismatch across ablation shards")

    declared_values = {run["run"].get("num_shards") for run in runs}
    if len(declared_values) != 1:
        raise ValueError("ablation num_shards mismatch")
    declared = next(iter(declared_values))
    if expected_shards is not None and declared != expected_shards:
        raise ValueError(f"expected {expected_shards} shards, files declare {declared}")
    indexes = {run["run"].get("shard_index") for run in runs}
    if indexes != set(range(declared)):
        raise ValueError(f"missing or unexpected ablation shard indexes: {sorted(indexes)}")

    invariant_keys = (
        "seed", "split_filter", "difficulty_filter", "max_results", "variants",
        "oracle_mode", "oracle_snapshot_file_sha256",
    )
    first_meta = runs[0]["run"]
    for run in runs[1:]:
        for key in invariant_keys:
            if run["run"].get(key) != first_meta.get(key):
                raise ValueError(f"ablation configuration mismatch for {key}")

    variant_names = list(first_meta.get("variants") or [])
    systems = []
    for variant in variant_names:
        rows = []
        config = None
        for run in runs:
            entry = next((item for item in run["systems"] if item.get("system") == variant), None)
            if entry is None:
                raise ValueError(f"variant {variant} missing from an ablation shard")
            config = entry.get("config")
            rows.extend(entry.get("cases") or [])
        ids = [str(row.get("id")) for row in rows]
        duplicates = [case_id for case_id, count in Counter(ids).items() if count > 1]
        if duplicates:
            raise ValueError(f"duplicate case IDs for variant {variant}: {duplicates[:10]}")
        rows.sort(key=lambda row: str(row.get("id")))
        systems.append({
            "system": variant,
            "config": config,
            "summary": _aggregate(rows),
            "by_family": {
                family: _aggregate([row for row in rows if row.get("family") == family])
                for family in sorted({str(row.get("family")) for row in rows})
            },
            "cases": rows,
        })

    return {
        "schema": "ChatAlchemyAblationRunMerged/v1",
        "run": {
            **{key: first_meta.get(key) for key in invariant_keys},
            "num_shards": declared,
            "merged_case_count": len(systems[0]["cases"]) if systems else 0,
            "component_git_sha": sorted({str(run["run"].get("git_sha")) for run in runs if run["run"].get("git_sha")}),
        },
        "benchmark": runs[0]["benchmark"],
        "systems": systems,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge and validate sharded ablation results.")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--expected-shards", type=int, default=None)
    parser.add_argument("--out", default="benchmark/ablations-merged.json")
    args = parser.parse_args()
    result = merge([Path(path) for path in args.paths], args.expected_shards)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"run": result["run"], "systems": [{"system": item["system"], "summary": item["summary"]} for item in result["systems"]]}, indent=2))


if __name__ == "__main__":
    main()
