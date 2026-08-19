from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def test_all_github_workflows_are_valid_yaml():
    files = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    assert files, "no GitHub Actions workflows found"
    for path in files:
        parsed = yaml.safe_load(path.read_text())
        assert isinstance(parsed, dict), f"workflow did not parse as a YAML mapping: {path.name}"
        assert "jobs" in parsed, f"workflow has no jobs mapping: {path.name}"


def test_primary_campaign_freezes_oracle_before_paired_systems():
    path = WORKFLOWS / "chatalchemy-primary-campaign.yml"
    text = path.read_text()
    assert "merge-oracle:" in text
    assert "needs: merge-oracle" in text
    assert "--oracle-snapshot benchmark/oracle-snapshot.json" in text
    assert "max-parallel: 2" in text
    assert "merge_model_baseline_shards.py" in text
    assert "merge_ablation_shards.py" in text
    assert "generate_paper_tables.py" in text
