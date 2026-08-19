from __future__ import annotations

import argparse
import json
from pathlib import Path

from chatalchemy.benchmark import SNAPSHOT_SCHEMA


def merge(paths: list[Path], expected_shards: int | None = None) -> dict:
    if not paths:
        raise ValueError("no oracle snapshot shards supplied")
    payloads = [json.loads(path.read_text()) for path in paths]
    if any(payload.get("schema") != SNAPSHOT_SCHEMA for payload in payloads):
        raise ValueError("all inputs must use the current oracle snapshot schema")

    fingerprints = {payload["benchmark"].get("fingerprint_sha256") for payload in payloads}
    if len(fingerprints) != 1:
        raise ValueError(f"benchmark fingerprint mismatch: {sorted(fingerprints)}")
    seeds = {payload["benchmark"].get("seed") for payload in payloads}
    if len(seeds) != 1:
        raise ValueError(f"benchmark seed mismatch: {sorted(seeds)}")

    declared_counts = {payload["selection"].get("num_shards") for payload in payloads}
    if len(declared_counts) != 1:
        raise ValueError(f"num_shards mismatch: {sorted(declared_counts)}")
    declared = next(iter(declared_counts))
    if expected_shards is not None and declared != expected_shards:
        raise ValueError(f"expected {expected_shards} shards, inputs declare {declared}")
    indexes = {payload["selection"].get("shard_index") for payload in payloads}
    if indexes != set(range(declared)):
        raise ValueError(f"missing or unexpected snapshot shard indexes: {sorted(indexes)}")

    invariant_keys = ("split_filter", "difficulty_filter")
    reference = payloads[0]["selection"]
    for payload in payloads[1:]:
        for key in invariant_keys:
            if payload["selection"].get(key) != reference.get(key):
                raise ValueError(f"snapshot selection mismatch for {key}")

    cases = [row for payload in payloads for row in payload["cases"]]
    ids = [row["id"] for row in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case IDs across oracle snapshot shards")
    signatures = [row.get("task_signature") for row in cases]
    if len(signatures) != len(set(signatures)):
        raise ValueError("duplicate task signatures across oracle snapshot shards")
    cases.sort(key=lambda row: row["id"])

    return {
        "schema": SNAPSHOT_SCHEMA,
        "created_at_utc": max(str(payload.get("created_at_utc")) for payload in payloads),
        "started_at_utc": min(str(payload.get("started_at_utc")) for payload in payloads),
        "benchmark": payloads[0]["benchmark"],
        "selection": {
            "split_filter": reference.get("split_filter"),
            "difficulty_filter": reference.get("difficulty_filter"),
            "full_selection": True,
            "limit": None,
            "num_shards": 1,
            "shard_index": 0,
            "merged_from_shards": declared,
        },
        "oracle_coverage": sum(bool(row.get("oracle_available")) for row in cases) / len(cases),
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--expected-shards", type=int, default=None)
    parser.add_argument("--out", default="benchmark/oracle-snapshot-merged.json")
    args = parser.parse_args()
    result = merge([Path(path) for path in args.paths], args.expected_shards)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"schema": result["schema"], "benchmark": result["benchmark"], "selection": result["selection"], "oracle_coverage": result["oracle_coverage"], "case_count": len(result["cases"])}, indent=2))


if __name__ == "__main__":
    main()
