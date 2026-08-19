from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .generator import BenchmarkCase
from .oracle import OracleResult

SNAPSHOT_SCHEMA = "LiveBioOracleSnapshot/v1"


def load_oracle_snapshot(path: str | Path, *, expected_fingerprint: str | None = None) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if payload.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError(f"unsupported oracle snapshot schema: {payload.get('schema')}")
    fingerprint = (payload.get("benchmark") or {}).get("fingerprint_sha256")
    if expected_fingerprint and fingerprint != expected_fingerprint:
        raise ValueError(f"oracle snapshot benchmark fingerprint mismatch: {fingerprint} != {expected_fingerprint}")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("oracle snapshot cases must be a list")
    ids = [row.get("id") for row in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case IDs in oracle snapshot")
    payload["case_map"] = {str(row["id"]): row for row in cases}
    return payload


def oracle_result_for_case(snapshot: dict[str, Any], case: BenchmarkCase) -> tuple[OracleResult | None, str | None]:
    row = snapshot.get("case_map", {}).get(case.id)
    if row is None:
        return None, "case missing from oracle snapshot"
    signature = row.get("task_signature")
    if signature and signature != case.task_signature:
        raise ValueError(f"task signature mismatch for {case.id}")
    if row.get("oracle_error"):
        return None, str(row["oracle_error"])
    if not row.get("oracle_available", True):
        return None, "oracle unavailable in snapshot"
    return OracleResult(
        kind=str(row.get("kind") or case.output_kind),
        value=row.get("value"),
        source_records=list(row.get("source_records") or []),
    ), None
