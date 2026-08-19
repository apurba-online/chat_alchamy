from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from chatalchemy.benchmark import generate_cases, validate_cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--out", default="benchmark/livebiobench.json")
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args()

    cases = generate_cases(args.n, args.seed)
    manifest = validate_cases(cases)
    manifest["seed"] = args.seed

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([asdict(case) for case in cases], indent=2) + "\n")

    manifest_path = Path(args.manifest) if args.manifest else out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
