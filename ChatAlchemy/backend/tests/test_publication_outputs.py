import csv
import json
from pathlib import Path

from scripts.freeze_external_holdout import freeze
from scripts.generate_paper_tables import (
    _normalize_summary,
    _paired_statistics,
    _write_main_csv,
    _write_main_tex,
)
from scripts.prepare_expert_evaluation import _render_response, _sample_common_case_ids
from scripts.prepare_failure_review import _is_failure


def _system(name, scores, family="identity"):
    return {
        "name": name,
        "summary": {
            "n": len(scores),
            "oracle_coverage": 1.0,
            "mean_task_score": sum(scores) / len(scores),
            "execution_success": 1.0,
        },
        "by_family": {},
        "cases": [
            {"id": f"case-{i}", "task_score": score, "family": family, "question": f"Question {i}"}
            for i, score in enumerate(scores)
        ],
    }


def test_paired_paper_statistics_use_common_case_ids():
    full = _system("ChatAlchemy-full", [1.0, 1.0, 1.0, 0.0])
    baseline = _system("LLM-only", [1.0, 0.0, 0.0, 0.0])
    result = _paired_statistics([full, baseline], "ChatAlchemy-full")
    assert result["reference"] == "ChatAlchemy-full"
    comparison = result["comparisons"][0]
    assert comparison["n_common"] == 4
    assert comparison["reference_minus_system"]["estimate"] == 0.5
    assert comparison["mcnemar"]["a_only"] == 2
    assert "holm_bonferroni" in comparison


def test_model_baseline_summary_maps_to_common_paper_schema():
    normalized = _normalize_summary({
        "n": 10,
        "baseline_mean_task_score": 0.65,
        "median_baseline_latency_ms": 321.5,
        "mean_model_total_tokens": 480.0,
    })
    assert normalized["mean_task_score"] == 0.65
    assert normalized["median_latency_ms"] == 321.5
    assert normalized["mean_model_total_tokens"] == 480.0


def test_paper_tables_are_machine_and_latex_readable(tmp_path: Path):
    systems = [_system("ChatAlchemy-full", [1.0, 0.5]), _system("LLM_only", [0.5, 0.0])]
    csv_path = tmp_path / "table.csv"
    tex_path = tmp_path / "table.tex"
    _write_main_csv(systems, csv_path)
    _write_main_tex(systems, tex_path)
    rows = list(csv.DictReader(csv_path.open()))
    assert [row["system"] for row in rows] == ["ChatAlchemy-full", "LLM_only"]
    tex = tex_path.read_text()
    assert "ChatAlchemy-full" in tex
    assert r"LLM\_only" in tex
    assert "\\begin{tabular}" in tex
    assert "\\end{tabular}" in tex


def test_external_holdout_freeze_validates_and_fingerprints(tmp_path: Path):
    holdout = [
        {
            "id": "external-0001",
            "family": "identity",
            "question": "What is the generic identity of a held-out drug alias?",
            "params": {"drug": "held-out-alias"},
            "primary_entity": "held-out-alias",
            "primary_entity_type": "drug",
        }
    ]
    source = tmp_path / "holdout.json"
    manifest_path = tmp_path / "freeze.json"
    source.write_text(json.dumps(holdout))
    result = freeze(str(source), str(manifest_path))
    assert result["case_count"] == 1
    assert result["answers_embedded"] is False
    assert len(result["sha256_raw_file"]) == 64
    assert len(result["canonical_holdout_fingerprint"]) == 64
    assert manifest_path.exists()


def test_expert_packet_sampling_requires_common_ids_and_is_deterministic():
    a = {"label": "A", "payload": {"cases": _system("A", [1, 0.5, 0])["cases"]}}
    b = {"label": "B", "payload": {"cases": _system("B", [0.5, 0.5, 1])["cases"]}}
    first = _sample_common_case_ids([a, b], 2, 1729)
    second = _sample_common_case_ids([a, b], 2, 1729)
    assert first == second
    assert len(first) == 2


def test_expert_response_prefers_saved_answer_text():
    assert _render_response({"answer_text": "Auditable answer", "prediction": ["x"]}) == "Auditable answer"


def test_failure_review_flags_scientific_and_execution_failures():
    assert _is_failure({"task_score": 0.5, "execution_ok": True, "routing_correct": True})
    assert _is_failure({"task_score": 1.0, "execution_ok": False, "routing_correct": True})
    assert _is_failure({"task_score": 1.0, "execution_ok": True, "routing_correct": False})
    assert not _is_failure({"task_score": 1.0, "execution_ok": True, "routing_correct": True})
