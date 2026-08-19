from __future__ import annotations

import argparse
import json
from pathlib import Path
from chatalchemy.benchmark.statistics import paired_bootstrap_ci, mcnemar_exact, holm_bonferroni


def rows(payload):
    if isinstance(payload,dict) and isinstance(payload.get("cases"),list): return payload["cases"]
    if isinstance(payload,list): return payload
    raise ValueError("Expected a list of cases or an object containing cases")

def score(row):
    for key in ("task_score","score","f1","accuracy"):
        if row.get(key) is not None:return float(row[key])
    raise KeyError("No score field found")

def main(a_path,b_path,out):
    a=rows(json.loads(Path(a_path).read_text())); b=rows(json.loads(Path(b_path).read_text())); bmap={r["id"]:r for r in b}; pairs=[(r,bmap[r["id"]]) for r in a if r.get("id") in bmap]
    av=[score(x) for x,_ in pairs]; bv=[score(y) for _,y in pairs]; stats={"paired_n":len(pairs),"score_difference":paired_bootstrap_ci(av,bv),"mcnemar_threshold_0_5":mcnemar_exact([x>=0.5 for x in av],[x>=0.5 for x in bv])}
    Path(out).write_text(json.dumps(stats,indent=2)+"\n"); return stats

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--system-a",required=True); p.add_argument("--system-b",required=True); p.add_argument("--out",default="benchmark/comparison.json"); a=p.parse_args(); print(json.dumps(main(a.system_a,a.system_b,a.out),indent=2))
