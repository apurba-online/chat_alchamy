from __future__ import annotations

import math
import random
from collections.abc import Sequence


def paired_bootstrap_ci(a: Sequence[float], b: Sequence[float] | None = None, *, n_boot: int = 10000, alpha: float = 0.05, seed: int = 1729) -> dict[str, float]:
    if not a:
        raise ValueError("empty sample")
    if b is not None and len(a) != len(b):
        raise ValueError("paired samples must have equal length")
    n = len(a)
    rng = random.Random(seed)
    def statistic(indices: list[int]) -> float:
        ma = sum(a[i] for i in indices) / n
        return ma if b is None else ma - sum(b[i] for i in indices) / n
    boots = sorted(statistic([rng.randrange(n) for _ in range(n)]) for _ in range(n_boot))
    observed = sum(a) / n if b is None else sum(x-y for x,y in zip(a,b)) / n
    lo = boots[max(0, int((alpha/2)*n_boot))]
    hi = boots[min(n_boot-1, int((1-alpha/2)*n_boot))]
    return {"estimate": observed, "ci_low": lo, "ci_high": hi, "n": n}


def mcnemar_exact(a_correct: Sequence[bool], b_correct: Sequence[bool]) -> dict[str, float | int]:
    if len(a_correct) != len(b_correct):
        raise ValueError("paired samples must have equal length")
    a_only = sum(bool(a) and not bool(b) for a,b in zip(a_correct,b_correct))
    b_only = sum(not bool(a) and bool(b) for a,b in zip(a_correct,b_correct))
    n = a_only + b_only
    if n == 0:
        p = 1.0
    else:
        k = min(a_only, b_only)
        p = min(1.0, 2.0 * sum(math.comb(n,i) for i in range(k+1)) / (2**n))
    return {"a_only": a_only, "b_only": b_only, "discordant": n, "p_value": p}


def holm_bonferroni(p_values: Sequence[float], alpha: float = 0.05) -> list[dict[str, float | bool | int]]:
    ordered = sorted(enumerate(p_values), key=lambda x:x[1]); m=len(ordered); out=[None]*m; active=True
    for rank,(idx,p) in enumerate(ordered, start=1):
        threshold=alpha/(m-rank+1); reject=active and p<=threshold
        if not reject: active=False
        out[idx]={"index":idx,"p_value":float(p),"threshold":threshold,"reject":reject}
    return out
