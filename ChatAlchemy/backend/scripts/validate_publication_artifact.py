from __future__ import annotations

import hashlib
import json
from pathlib import Path

from chatalchemy.benchmark import generate_cases, validate_cases
from chatalchemy.benchmark.generator import BENCHMARK_VERSION, ENTITY_POOLS

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"

REQUIRED_FILES = [
    ROOT / "PUBLICATION_PROTOCOL.md",
    BACKEND / "benchmark" / "BENCHMARK_CARD.md",
    BACKEND / "benchmark" / "EXPERT_EVALUATION.md",
    BACKEND / "scripts" / "run_live_benchmark.py",
    BACKEND / "scripts" / "run_model_baseline.py",
    BACKEND / "scripts" / "run_ablation.py",
    BACKEND / "scripts" / "run_counterfactual.py",
    BACKEND / "scripts" / "run_failure_injection.py",
    BACKEND / "scripts" / "compare_temporal_runs.py",
    BACKEND / "scripts" / "freeze_external_holdout.py",
    BACKEND / "scripts" / "summarize_results.py",
]

FORBIDDEN_TEXT = (
    "dangerouslyAllowBrowser",
    "VITE_OPENAI_API_KEY",
)


def _pool_values(pool, key: str) -> set[str]:
    return {str(value).lower() for value in getattr(pool, key)}


def validate_split_isolation() -> None:
    names = list(ENTITY_POOLS)
    for i, left_name in enumerate(names):
        left = ENTITY_POOLS[left_name]
        for right_name in names[i + 1 :]:
            right = ENTITY_POOLS[right_name]
            for key in ("drugs", "targets", "conditions", "genes"):
                overlap = _pool_values(left, key) & _pool_values(right, key)
                if overlap:
                    raise AssertionError(f"benchmark leakage in {key}: {left_name}/{right_name}: {sorted(overlap)}")


def validate_security() -> None:
    candidates = list((ROOT / "src").rglob("*.ts")) + list((ROOT / "src").rglob("*.tsx"))
    for path in candidates:
        text = path.read_text(errors="replace")
        for forbidden in FORBIDDEN_TEXT:
            if forbidden in text:
                raise AssertionError(f"forbidden browser credential pattern {forbidden!r} in {path.relative_to(ROOT)}")
    env_file = ROOT / ".env"
    if env_file.exists():
        raise AssertionError("ChatAlchemy/.env must not be committed; use server environment configuration")


def main() -> None:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        raise AssertionError(f"missing publication files: {missing}")

    cases = generate_cases(1500, 1729)
    manifest = validate_cases(cases)
    if len(cases) != 1500:
        raise AssertionError("publication benchmark must generate exactly 1500 nominal cases")
    if len({case.id for case in cases}) != len(cases):
        raise AssertionError("benchmark case IDs must be unique")
    validate_split_isolation()
    validate_security()

    serialized = json.dumps([case.__dict__ for case in cases], sort_keys=True, default=str).encode()
    summary = {
        "benchmark_version": BENCHMARK_VERSION,
        "case_count": len(cases),
        "benchmark_sha256": hashlib.sha256(serialized).hexdigest(),
        "manifest": manifest,
        "publication_files": len(REQUIRED_FILES),
        "security_gate": "passed",
    }
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
