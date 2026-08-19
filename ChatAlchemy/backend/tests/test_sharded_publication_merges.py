import json
from pathlib import Path

from scripts.generate_paper_tables import _compatible_reference
from scripts.merge_ablation_shards import merge as merge_ablations
from scripts.merge_model_baseline_shards import merge as merge_baselines


FINGERPRINT = "f" * 64
SNAPSHOT = "s" * 64


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload))
    return path


def _model_row(case_id: str, baseline: float, full: float) -> dict:
    return {
        "id": case_id,
        "family": "identity",
        "task_score": baseline,
        "chatalchemy_task_score": full,
        "oracle_available": True,
        "baseline_latency_ms": 10.0,
        "model_error": None,
        "retrieval_error": None,
        "model_usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        "tool_call_count": 0,
    }


def test_model_baseline_shards_merge_with_one_frozen_oracle(tmp_path: Path):
    paths = []
    for shard in range(2):
        payload = {
            "schema": "ChatAlchemyModelBaselineRun/v4",
            "run": {
                "mode": "llm_only",
                "model": "test-model",
                "prompt_version": "model-baseline-v4",
                "seed": 1729,
                "split_filter": "test",
                "difficulty_filter": "all",
                "max_results": 20,
                "max_tool_steps": 0,
                "oracle_mode": "frozen_snapshot",
                "oracle_snapshot_file_sha256": SNAPSHOT,
                "num_shards": 2,
                "shard_index": shard,
                "started_at_utc": f"2026-08-19T00:0{shard}:00+00:00",
                "finished_at_utc": f"2026-08-19T00:0{shard}:01+00:00",
                "git_sha": "abc",
            },
            "benchmark": {"fingerprint_sha256": FINGERPRINT},
            "cases": [_model_row(f"case-{shard}", 0.0, 1.0)],
        }
        paths.append(_write(tmp_path / f"model-{shard}.json", payload))
    merged = merge_baselines(paths, expected_shards=2)
    assert merged["run"]["oracle_snapshot_file_sha256"] == SNAPSHOT
    assert merged["run"]["merged_case_count"] == 2
    assert merged["summary"]["paired_mean_chatalchemy_minus_baseline"] == 1.0


def _ablation_row(case_id: str, score: float) -> dict:
    return {
        "id": case_id,
        "family": "identity",
        "task_score": score,
        "oracle_available": True,
        "execution_ok": True,
        "claim_count": 1,
        "supported_claim_rate": 1.0,
        "provenance_record_f1": 1.0,
    }


def test_ablation_shards_merge_variant_by_variant(tmp_path: Path):
    paths = []
    variants = ["full", "no_normalization"]
    for shard in range(2):
        systems = [
            {"system": name, "config": {}, "cases": [_ablation_row(f"case-{shard}", 1.0 if name == "full" else 0.0)]}
            for name in variants
        ]
        payload = {
            "schema": "ChatAlchemyAblationRun/v3",
            "run": {
                "seed": 1729,
                "split_filter": "test",
                "difficulty_filter": "all",
                "max_results": 20,
                "variants": variants,
                "oracle_mode": "frozen_snapshot",
                "oracle_snapshot_file_sha256": SNAPSHOT,
                "num_shards": 2,
                "shard_index": shard,
            },
            "benchmark": {"fingerprint_sha256": FINGERPRINT},
            "systems": systems,
        }
        paths.append(_write(tmp_path / f"ablation-{shard}.json", payload))
    merged = merge_ablations(paths, expected_shards=2)
    full = next(item for item in merged["systems"] if item["system"] == "full")
    no_norm = next(item for item in merged["systems"] if item["system"] == "no_normalization")
    assert full["summary"]["mean_task_score"] == 1.0
    assert no_norm["summary"]["mean_task_score"] == 0.0
    assert merged["run"]["oracle_snapshot_file_sha256"] == SNAPSHOT


def test_paper_statistics_refuse_different_oracle_states():
    reference = {"benchmark_fingerprint": FINGERPRINT, "oracle_state": "snapshot:aaa"}
    other = {"benchmark_fingerprint": FINGERPRINT, "oracle_state": "snapshot:bbb"}
    assert "oracle state mismatch" in _compatible_reference(reference, other)


def test_paper_statistics_refuse_different_benchmark_fingerprints():
    reference = {"benchmark_fingerprint": "aaa", "oracle_state": "snapshot:same"}
    other = {"benchmark_fingerprint": "bbb", "oracle_state": "snapshot:same"}
    assert _compatible_reference(reference, other) == "benchmark fingerprint mismatch"
