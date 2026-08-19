from __future__ import annotations

import math
import random
from collections.abc import Sequence


def paired_bootstrap_ci(a: Sequence[float], b: Sequence[float] | None = None, *, n_boot: int = 10000, alpha: float = 0.05, seed: int = 42) -> tuple[float, float, float]:
    if not a: raise ValueError("empty sample")
    if b is not None and len(a) != len(b): raise ValueError("paired samples must have equal length")
    rng = random.Random(seed); n = len(a)
    def statistic(indices):
        ma = sum(a[i] for i in indices) / n
        if b is None: return ma
        return ma - sum(b[i] for i in indices) / n
    vals = sorted(statistic([rng.randrange(n) for _ in range(n)]) for _ in range(n_boot))
    lo = vals[int((alpha / 2) * n_boot)]; hi = vals[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    observed = sum(a) / n if b is None else sum(x - y for x, y in zip(a, b)) / n
    return observed, lo, hi


def mcnemar_exact(a_correct: Sequence[bool], b_correct: Sequence[bool]) -> dict[str, float | int]:
    if len(a_correct) != len(b_correct): raise ValueError("paired samples must have equal length")
    b = sum(bool(x) and not bool(y) for x, y in zip(a_correct, b_correct)); c = sum(not bool(x) and bool(y) for x, y in zip(a_correct, b_correct)); n = b + c
    if n == 0: p = 1.0
    else:
        k = min(b, c); p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n))
    return {"a_only": b, "b_only": c, "discordant": n, "p_value": p}


def holm_bonferroni(p_values: Sequence[float], alpha: float = 0.05) -> list[dict[str, float | bool | int]]:
    indexed = sorted(enumerate(p_values), key=lambda x: x[1]); m = len(indexed); out = [None] * m; active = True
    for rank, (idx, p) in enumerate(indexed, start=1):
        threshold = alpha / (m - rank + 1); reject = active and p <= threshold
        if not reject: active = False
        out[idx] = {"index": idx, "p_value": p, "threshold": threshold, "reject": reject}
    return out
