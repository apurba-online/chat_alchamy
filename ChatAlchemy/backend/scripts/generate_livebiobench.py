from __future__ import annotations
import argparse,json
from pathlib import Path
from chatalchemy.benchmark import generate_cases
p=argparse.ArgumentParser();p.add_argument("--n",type=int,default=1500);p.add_argument("--seed",type=int,default=1729);p.add_argument("--out",default="benchmark/livebiobench.json");a=p.parse_args();cases=generate_cases(a.n,a.seed);out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps([c.__dict__ for c in cases],indent=2));print(f"wrote {len(cases)} cases to {out}")
