import csv
import json
from pathlib import Path

from scripts.freeze_external_holdout import freeze
from scripts.generate_paper_tables import _paired_statistics, _write_main_csv, _write_main_tex


def _system(name, scores):
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
            {"id": f"case-{i}", "task_score": score}
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
