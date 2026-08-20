import pytest

from scripts.run_ablation import _aggregate as ablation_aggregate
from scripts.run_live_benchmark import aggregate_rows
from scripts.run_model_baseline import _aggregate as baseline_aggregate


def test_main_benchmark_latency_excludes_oracle_time():
    rows = [
        {
            "task_score": 1.0,
            "latency_ms": 100.0,
            "source_latency_ms": 80.0,
            "oracle_latency_ms": 900.0,
            "claim_count": 1,
            "supported_claim_rate": 1.0,
            "provenance_record_f1": 1.0,
            "oracle_available": True,
            "routing_correct": True,
            "execution_ok": True,
            "api_calls": 1,
            "evidence_count": 1,
        },
        {
            "task_score": 0.5,
            "latency_ms": 200.0,
            "source_latency_ms": 160.0,
            "oracle_latency_ms": 1100.0,
            "claim_count": 0,
            "supported_claim_rate": 0.0,
            "provenance_record_f1": 0.5,
            "oracle_available": True,
            "routing_correct": True,
            "execution_ok": True,
            "api_calls": 2,
            "evidence_count": 2,
        },
    ]
    summary = aggregate_rows(rows)
    assert summary["median_latency_ms"] == pytest.approx(150.0)
    assert summary["median_source_latency_ms"] == pytest.approx(120.0)
    assert summary["median_oracle_latency_ms"] == pytest.approx(1000.0)
    assert summary["median_latency_ms"] < summary["median_oracle_latency_ms"]


def test_model_baseline_reports_end_to_end_baseline_separately_from_reference_and_oracle():
    rows = [
        {
            "task_score": 0.5,
            "chatalchemy_task_score": 1.0,
            "oracle_available": True,
            "baseline_latency_ms": 300.0,
            "baseline_model_latency_ms": 200.0,
            "baseline_retrieval_latency_ms": 100.0,
            "chatalchemy_latency_ms": 150.0,
            "oracle_latency_ms": 1000.0,
            "model_error": None,
            "retrieval_error": None,
            "model_usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            "tool_call_count": 2,
        }
    ]
    summary = baseline_aggregate(rows)
    assert summary["median_baseline_latency_ms"] == pytest.approx(300.0)
    assert summary["median_baseline_model_latency_ms"] == pytest.approx(200.0)
    assert summary["median_baseline_retrieval_latency_ms"] == pytest.approx(100.0)
    assert summary["median_chatalchemy_latency_ms"] == pytest.approx(150.0)
    assert summary["median_oracle_latency_ms"] == pytest.approx(1000.0)


def test_ablation_latency_excludes_oracle_time():
    rows = [
        {
            "task_score": 1.0,
            "oracle_available": True,
            "execution_ok": True,
            "supported_claim_rate": 1.0,
            "claim_count": 1,
            "provenance_record_f1": 1.0,
            "latency_ms": 75.0,
            "source_latency_ms": 50.0,
            "oracle_latency_ms": 700.0,
        }
    ]
    summary = ablation_aggregate(rows)
    assert summary["median_latency_ms"] == pytest.approx(75.0)
    assert summary["median_source_latency_ms"] == pytest.approx(50.0)
    assert summary["median_oracle_latency_ms"] == pytest.approx(700.0)
