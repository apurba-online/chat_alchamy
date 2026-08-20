import json
from pathlib import Path

from scripts.merge_ablation_shards import merge as merge_ablations
from scripts.merge_benchmark_shards import merge as merge_benchmark
from scripts.merge_model_baseline_shards import merge as merge_baselines


FINGERPRINT = "f" * 64
SNAPSHOT = "s" * 64


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload))
    return path


def _main_row(case_id: str, shard: int) -> dict:
    return {
        "id": case_id,
        "task_score": 1.0,
        "latency_ms": 100.0 + shard,
        "source_latency_ms": 80.0,
        "oracle_latency_ms": 10.0,
        "claim_count": 1,
        "supported_claim_rate": 1.0,
        "provenance_record_f1": 1.0,
        "oracle_available": True,
        "routing_correct": True,
        "execution_ok": True,
        "api_calls": 1,
        "evidence_count": 1,
        "split": "test",
        "difficulty": "easy",
        "family": "identity",
        "oracle_error": None,
    }


def test_merge_current_main_benchmark_schema(tmp_path):
    paths = []
    for shard in range(2):
        payload = {
            "schema": "ChatAlchemyBenchmarkRun/v6",
            "run": {
                "seed": 1729,
                "benchmark_n": 1500,
                "split_filter": "test",
                "difficulty_filter": "all",
                "max_results": 20,
                "system": "ChatAlchemy-full",
                "oracle_mode": "frozen_snapshot",
                "oracle_snapshot_file_sha256": SNAPSHOT,
                "latency_definition": "system wall-clock only",
                "num_shards": 2,
                "shard_index": shard,
                "started_at_utc": f"2026-08-20T00:0{shard}:00+00:00",
                "finished_at_utc": f"2026-08-20T00:0{shard}:01+00:00",
                "git_sha": "abc",
            },
            "benchmark": {
                "schema": "LiveBioEvidenceBench-v2.1",
                "case_count": 1500,
                "fingerprint_sha256": FINGERPRINT,
            },
            "cases": [_main_row(f"case-{shard}", shard)],
        }
        paths.append(_write(tmp_path / f"main-{shard}.json", payload))

    merged = merge_benchmark(paths, expected_shards=2)
    assert merged["schema"] == "ChatAlchemyBenchmarkRunMerged/v3"
    assert merged["run"]["merged_case_count"] == 2
    assert merged["summary"]["n"] == 2
    assert merged["summary"]["median_oracle_latency_ms"] == 10.0


def _baseline_row(case_id: str) -> dict:
    return {
        "id": case_id,
        "family": "identity",
        "task_score": 0.5,
        "chatalchemy_task_score": 1.0,
        "oracle_available": True,
        "baseline_latency_ms": 300.0,
        "baseline_model_latency_ms": 200.0,
        "baseline_retrieval_latency_ms": 100.0,
        "chatalchemy_latency_ms": 120.0,
        "oracle_latency_ms": 10.0,
        "execution_success": True,
        "provenance_record_f1": 1.0,
        "model_error": None,
        "retrieval_error": None,
        "api_calls": 1,
        "model_usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        "tool_call_count": 1,
    }


def test_merge_current_model_baseline_schema(tmp_path):
    paths = []
    for shard in range(2):
        payload = {
            "schema": "ChatAlchemyModelBaselineRun/v6",
            "run": {
                "mode": "same_retrieval_llm",
                "model": "gpt-5.6-sol",
                "prompt_version": "model-baseline-v6",
                "seed": 1729,
                "split_filter": "test",
                "difficulty_filter": "all",
                "max_results": 20,
                "max_tool_steps": 0,
                "oracle_mode": "frozen_snapshot",
                "oracle_snapshot_file_sha256": SNAPSHOT,
                "latency_definition": "baseline end-to-end",
                "same_retrieval_latency_note": "conservative",
                "provenance_definition": "record F1",
                "num_shards": 2,
                "shard_index": shard,
                "started_at_utc": f"2026-08-20T00:1{shard}:00+00:00",
                "finished_at_utc": f"2026-08-20T00:1{shard}:01+00:00",
                "git_sha": "abc",
            },
            "benchmark": {"fingerprint_sha256": FINGERPRINT},
            "cases": [_baseline_row(f"case-{shard}")],
        }
        paths.append(_write(tmp_path / f"baseline-{shard}.json", payload))

    merged = merge_baselines(paths, expected_shards=2)
    assert merged["schema"] == "ChatAlchemyModelBaselineRunMerged/v3"
    assert merged["run"]["merged_case_count"] == 2
    assert merged["summary"]["n"] == 2
    assert merged["summary"]["median_baseline_latency_ms"] == 300.0


def _ablation_row(case_id: str) -> dict:
    return {
        "id": case_id,
        "family": "identity",
        "task_score": 1.0,
        "oracle_available": True,
        "execution_ok": True,
        "supported_claim_rate": 1.0,
        "claim_count": 1,
        "provenance_record_f1": 1.0,
        "latency_ms": 90.0,
        "source_latency_ms": 70.0,
        "oracle_latency_ms": 10.0,
    }


def test_merge_current_ablation_schema(tmp_path):
    paths = []
    variants = ["full", "no_normalization"]
    for shard in range(2):
        payload = {
            "schema": "ChatAlchemyAblationRun/v4",
            "run": {
                "seed": 1729,
                "split_filter": "test",
                "difficulty_filter": "all",
                "max_results": 20,
                "variants": variants,
                "oracle_mode": "frozen_snapshot",
                "oracle_snapshot_file_sha256": SNAPSHOT,
                "latency_definition": "per-variant system wall-clock only",
                "num_shards": 2,
                "shard_index": shard,
                "git_sha": "abc",
            },
            "benchmark": {"fingerprint_sha256": FINGERPRINT},
            "systems": [
                {
                    "system": variant,
                    "config": {},
                    "cases": [_ablation_row(f"case-{shard}")],
                }
                for variant in variants
            ],
        }
        paths.append(_write(tmp_path / f"ablation-{shard}.json", payload))

    merged = merge_ablations(paths, expected_shards=2)
    assert merged["schema"] == "ChatAlchemyAblationRunMerged/v2"
    assert merged["run"]["merged_case_count"] == 2
    assert [system["system"] for system in merged["systems"]] == variants
    assert all(system["summary"]["n"] == 2 for system in merged["systems"])
