from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from chatalchemy.benchmark.external_holdout import load_external_holdout


def freeze(path: str, manifest: str) -> dict:
    source = Path(path)
    raw = source.read_bytes()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Holdout must be valid JSON: {exc}")
    if not isinstance(parsed, list) or not parsed:
        raise SystemExit("Holdout JSON must contain a non-empty list of cases")

    try:
        cases, validated = load_external_holdout(source)
    except Exception as exc:
        raise SystemExit(f"Holdout schema validation failed: {exc}") from exc

    result = {
        "schema": "ChatAlchemyExternalHoldoutFreeze/v2",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_count": len(cases),
        "sha256_raw_file": hashlib.sha256(raw).hexdigest(),
        "canonical_holdout_fingerprint": validated["fingerprint_sha256"],
        "independently_authored": validated["independently_authored"],
        "answers_embedded": validated["answers_embedded"],
        "note": "Keep the source holdout private from system developers until the system configuration is frozen. Evaluate the frozen system once.",
    }
    out = Path(manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and fingerprint an independently authored external holdout.")
    parser.add_argument("path", nargs="?", help="Private holdout JSON")
    parser.add_argument("--input", dest="input_path", help="Backward-compatible input flag")
    parser.add_argument("--manifest", default=None, help="Backward-compatible output flag")
    parser.add_argument("--out", default=None, help="Output freeze manifest")
    args = parser.parse_args()
    input_path = args.path or args.input_path
    if not input_path:
        parser.error("a holdout path is required")
    output = args.out or args.manifest or "benchmark/external_holdout_manifest.json"
    print(json.dumps(freeze(input_path, output), indent=2))


if __name__ == "__main__":
    main()
