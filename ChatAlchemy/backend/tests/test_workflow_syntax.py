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
