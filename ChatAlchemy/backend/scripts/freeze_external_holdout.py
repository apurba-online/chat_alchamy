from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def freeze(path: str, manifest: str) -> dict:
    raw = Path(path).read_bytes()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Holdout must be valid JSON: {exc}")
    if not isinstance(parsed, list):
        raise SystemExit("Holdout JSON must contain a list of cases")
    result = {
        "schema": "ChatAlchemyExternalHoldout/v1",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_count": len(parsed),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "note": "Keep the source holdout private from system developers until the model/system configuration is frozen.",
    }
    Path(manifest).write_text(json.dumps(result, indent=2) + "\n")
    return result

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--manifest",default="benchmark/external_holdout_manifest.json"); a=p.parse_args(); print(json.dumps(freeze(a.input,a.manifest),indent=2))
