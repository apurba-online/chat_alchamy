from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from chatalchemy.benchmark import benchmark_manifest, generate_cases, validate_cases

PUBLIC_BENCHMARK_N = 1500
DEFAULT_SEED = 1729


def _git_sha() -> str | None:
    env_sha = os.getenv("GITHUB_SHA") or os.getenv("VERCEL_GIT_COMMIT_SHA")
    if env_sha:
        return env_sha
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def _version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Record the immutable configuration used for a paper experiment.")
    parser.add_argument("--out", default="benchmark/study-manifest.json")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--experiment", default=os.getenv("CHAT_ALCHEMY_EXPERIMENT", "unspecified"))
    parser.add_argument("--split", default=os.getenv("CHAT_ALCHEMY_SPLIT", "test"))
    parser.add_argument("--difficulty", default=os.getenv("CHAT_ALCHEMY_DIFFICULTY", "all"))
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL"))
    args = parser.parse_args()

    cases = generate_cases(PUBLIC_BENCHMARK_N, args.seed)
    validate_cases(cases)
    bench = benchmark_manifest(cases)

    manifest = {
        "schema": "ChatAlchemyStudyManifest/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git": {
            "sha": _git_sha(),
            "branch_or_ref": os.getenv("GITHUB_REF") or os.getenv("VERCEL_GIT_COMMIT_REF"),
            "repository": os.getenv("GITHUB_REPOSITORY"),
        },
        "experiment": {
            "name": args.experiment,
            "split": args.split,
            "difficulty": args.difficulty,
            "seed": args.seed,
            "model": args.model,
        },
        "benchmark": {**bench, "seed": args.seed},
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": {
                name: _version(name)
                for name in (
                    "fastapi",
                    "httpx",
                    "pydantic",
                    "PyYAML",
                    "pypdf",
                    "openpyxl",
                    "pytest",
                )
            },
            "openai_credential_present": bool(os.getenv("OPENAI_API_KEY")),
        },
        "protocol": {
            "primary_confirmatory_split": "test",
            "development_split": "dev",
            "stress_split": "stress",
            "oracle": "independent live API oracle",
            "ground_truth_policy": "answers are recomputed from live sources at evaluation time",
            "pairing_policy": "system comparisons use common case IDs with available oracle outputs",
            "multiple_testing": "Holm-Bonferroni for pre-specified paired comparisons",
            "confidence_intervals": "paired bootstrap, 10000 resamples unless otherwise stated",
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
