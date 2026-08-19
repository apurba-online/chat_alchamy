from __future__ import annotations

import hashlib
import json
from pathlib import Path

from chatalchemy.benchmark import generate_cases, validate_cases
from chatalchemy.benchmark.generator import BENCHMARK_VERSION, ENTITY_POOLS

ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent
BACKEND = ROOT / "backend"

REQUIRED_FILES = [
    ROOT / "PUBLICATION_PROTOCOL.md",
    BACKEND / "benchmark" / "BENCHMARK_CARD.md",
    BACKEND / "benchmark" / "EXPERT_EVALUATION.md",
    BACKEND / "benchmark" / "expert_eval_template.csv",
    BACKEND / "chatalchemy" / "benchmark" / "statistics.py",
    BACKEND / "chatalchemy" / "benchmark" / "oracle_snapshot.py",
    BACKEND / "chatalchemy" / "benchmark" / "oracle_provider.py",
    BACKEND / "scripts" / "generate_livebiobench.py",
    BACKEND / "scripts" / "build_oracle_snapshot.py",
    BACKEND / "scripts" / "merge_oracle_snapshots.py",
    BACKEND / "scripts" / "run_live_benchmark.py",
    BACKEND / "scripts" / "merge_benchmark_shards.py",
    BACKEND / "scripts" / "run_model_baseline.py",
    BACKEND / "scripts" / "run_ablation.py",
    BACKEND / "scripts" / "run_counterfactual.py",
    BACKEND / "scripts" / "run_failure_injection.py",
    BACKEND / "scripts" / "compare_temporal_runs.py",
    BACKEND / "scripts" / "freeze_external_holdout.py",
    BACKEND / "scripts" / "summarize_results.py",
    REPO_ROOT / ".github" / "workflows" / "chatalchemy-live-ci.yml",
    REPO_ROOT / ".github" / "workflows" / "chatalchemy-paper-experiments.yml",
]

FORBIDDEN_TEXT = (
    "dangerouslyAllowBrowser",
    "VITE_OPENAI_API_KEY",
)
FORBIDDEN_BUNDLED_PHARMA = (
    ROOT / "public" / "data" / "ttd_drug_disease.csv",
    ROOT / "public" / "data" / "ttd_drug_disease.xlsx",
)


def _pool_values(pool, key: str) -> set[str]:
    return {str(value).lower() for value in getattr(pool, key)}


def validate_split_isolation() -> None:
    names = list(ENTITY_POOLS)
    for i, left_name in enumerate(names):
        left = ENTITY_POOLS[left_name]
        for right_name in names[i + 1 :]:
            right = ENTITY_POOLS[right_name]
            for key in ("drugs", "compounds", "targets", "conditions", "genes"):
                overlap = _pool_values(left, key) & _pool_values(right, key)
                if overlap:
                    raise AssertionError(f"benchmark leakage in {key}: {left_name}/{right_name}: {sorted(overlap)}")
            left_aliases = {str(alias).lower() for alias, _ in left.aliases}
            right_aliases = {str(alias).lower() for alias, _ in right.aliases}
            if left_aliases & right_aliases:
                raise AssertionError(f"brand alias leakage: {left_name}/{right_name}")
            left_generics = {str(generic).lower() for _, generic in left.aliases}
            right_generics = {str(generic).lower() for _, generic in right.aliases}
            if left_generics & right_generics:
                raise AssertionError(f"identity generic leakage: {left_name}/{right_name}")


def validate_security() -> None:
    candidates = (
        list((ROOT / "src").rglob("*.ts"))
        + list((ROOT / "src").rglob("*.tsx"))
        + list(BACKEND.rglob("*.py"))
    )
    for path in candidates:
        text = path.read_text(errors="replace")
        for forbidden in FORBIDDEN_TEXT:
            if forbidden in text:
                raise AssertionError(f"forbidden browser credential pattern {forbidden!r} in {path.relative_to(ROOT)}")
    env_file = ROOT / ".env"
    if env_file.exists():
        raise AssertionError("ChatAlchemy/.env must not be committed; use server environment configuration")
    existing_pharma = [str(path.relative_to(ROOT)) for path in FORBIDDEN_BUNDLED_PHARMA if path.exists()]
    if existing_pharma:
        raise AssertionError(f"bundled pharmaceutical corpus is forbidden: {existing_pharma}")


def validate_protocol_alignment(manifest: dict) -> None:
    protocol = (ROOT / "PUBLICATION_PROTOCOL.md").read_text()
    card = (BACKEND / "benchmark" / "BENCHMARK_CARD.md").read_text()
    if BENCHMARK_VERSION not in protocol or BENCHMARK_VERSION not in card:
        raise AssertionError("publication protocol and benchmark card must name the current benchmark version")
    if manifest.get("case_count") != 1500:
        raise AssertionError("publication benchmark must contain 1500 task states")
    if manifest.get("task_signature_count") != 1500:
        raise AssertionError("publication benchmark task signatures must be unique")
    if manifest.get("split_counts") != {"dev": 300, "test": 900, "stress": 300}:
        raise AssertionError(f"unexpected publication split counts: {manifest.get('split_counts')}")
    if not manifest.get("fingerprint_sha256"):
        raise AssertionError("benchmark fingerprint is missing")


def main() -> None:
    missing = [str(path.relative_to(REPO_ROOT)) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        raise AssertionError(f"missing publication files: {missing}")

    cases = generate_cases(1500, 1729)
    manifest = validate_cases(cases)
    if len({case.id for case in cases}) != len(cases):
        raise AssertionError("benchmark case IDs must be unique")
    if len({case.task_signature for case in cases}) != len(cases):
        raise AssertionError("benchmark task signatures must be unique")

    validate_split_isolation()
    validate_security()
    validate_protocol_alignment(manifest)

    serialized = json.dumps([case.__dict__ for case in cases], sort_keys=True, default=str).encode()
    summary = {
        "benchmark_version": BENCHMARK_VERSION,
        "case_count": len(cases),
        "task_signature_count": len({case.task_signature for case in cases}),
        "benchmark_sha256": hashlib.sha256(serialized).hexdigest(),
        "manifest": manifest,
        "publication_files": len(REQUIRED_FILES),
        "security_gate": "passed",
        "split_isolation_gate": "passed",
        "protocol_alignment_gate": "passed",
    }
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
