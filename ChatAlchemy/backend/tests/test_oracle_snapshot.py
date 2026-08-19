import json

import pytest

from chatalchemy.benchmark import SNAPSHOT_SCHEMA, generate_cases, load_oracle_snapshot, oracle_result_for_case, validate_cases


def test_oracle_snapshot_requires_matching_benchmark_and_task_signature(tmp_path):
    cases = generate_cases(1500, 1729)
    manifest = validate_cases(cases)
    case = cases[0]
    payload = {
        "schema": SNAPSHOT_SCHEMA,
        "benchmark": manifest,
        "cases": [
            {
                "id": case.id,
                "task_signature": case.task_signature,
                "oracle_available": True,
                "kind": case.output_kind,
                "value": "example",
                "source_records": [{"source": "unit", "record": "1"}],
            }
        ],
    }
    path = tmp_path / "oracle.json"
    path.write_text(json.dumps(payload))
    snapshot = load_oracle_snapshot(path, expected_fingerprint=manifest["fingerprint_sha256"])
    result, error = oracle_result_for_case(snapshot, case)
    assert error is None
    assert result is not None
    assert result.value == "example"
    with pytest.raises(ValueError):
        load_oracle_snapshot(path, expected_fingerprint="wrong")


def test_missing_snapshot_case_is_reported_not_invented(tmp_path):
    cases = generate_cases(1500, 1729)
    manifest = validate_cases(cases)
    path = tmp_path / "oracle.json"
    path.write_text(json.dumps({"schema": SNAPSHOT_SCHEMA, "benchmark": manifest, "cases": []}))
    snapshot = load_oracle_snapshot(path, expected_fingerprint=manifest["fingerprint_sha256"])
    result, error = oracle_result_for_case(snapshot, cases[0])
    assert result is None
    assert error == "case missing from oracle snapshot"
