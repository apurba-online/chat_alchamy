from __future__ import annotations

import argparse
import json
from pathlib import Path

from chatalchemy.benchmark.temporal import compare_runs

parser = argparse.ArgumentParser()
parser.add_argument("earlier")
parser.add_argument("later")
parser.add_argument("--out", default="benchmark/temporal-comparison.json")
args = parser.parse_args()

earlier = json.loads(Path(args.earlier).read_text())
later = json.loads(Path(args.later).read_text())
result = compare_runs(earlier, later)
Path(args.out).parent.mkdir(parents=True, exist_ok=True)
Path(args.out).write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
