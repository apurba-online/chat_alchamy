from __future__ import annotations

import math
import random
from collections.abc import Sequence


def paired_bootstrap_ci(
    a: Sequence[float],
    b: Sequence[float] | None = None,
    *,
    n_boot: int = 10000,
    alpha: float = 0.05,
    seed: int = 1729,
) -> dict[str, float]:
    if not a:
        raise ValueError("empty sample")
    if b is not None and len(a) != len(b):
        raise ValueError("paired samples must have equal length")
    n = len(a)
    rng = random.Random(seed)

    def statistic(indices: list[int]) -> float:
        mean_a = sum(a[index] for index in indices) / n
        return mean_a if b is None else mean_a - sum(b[index] for index in indices) / n

    boots = sorted(statistic([rng.randrange(n) for _ in range(n)]) for _ in range(n_boot))
    observed = sum(a) / n if b is None else sum(x - y for x, y in zip(a, b)) / n
    lo = boots[max(0, int((alpha / 2) * n_boot))]
    hi = boots[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return {"estimate": observed, "ci_low": lo, "ci_high": hi, "n": n}


def mcnemar_exact(a_correct: Sequence[bool], b_correct: Sequence[bool]) -> dict[str, float | int]:
    if len(a_correct) != len(b_correct):
        raise ValueError("paired samples must have equal length")
    a_only = sum(bool(a) and not bool(b) for a, b in zip(a_correct, b_correct))
    b_only = sum(not bool(a) and bool(b) for a, b in zip(a_correct, b_correct))
    n = a_only + b_only
    if n == 0:
        p_value = 1.0
    else:
        k = min(a_only, b_only)
        p_value = min(1.0, 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / (2**n))
    return {"a_only": a_only, "b_only": b_only, "discordant": n, "p_value": p_value}


def holm_bonferroni(
    p_values: Sequence[float],
    alpha: float = 0.05,
) -> list[dict[str, float | bool | int]]:
    """Holm step-down correction with both decisions and adjusted p-values.

    Adjusted p-values are monotone in sorted raw-p order:
    p_adj(i) = max_{j<=i} ((m-j+1) * p_(j)), capped at 1.
    The return order matches the caller's original p-value order.
    """
    if any(not 0.0 <= float(value) <= 1.0 for value in p_values):
        raise ValueError("p-values must be between 0 and 1")
    m = len(p_values)
    if m == 0:
        return []

    ordered = sorted(enumerate(float(value) for value in p_values), key=lambda item: item[1])
    out: list[dict[str, float | bool | int] | None] = [None] * m
    running_adjusted = 0.0
    continue_rejecting = True

    for rank, (original_index, p_value) in enumerate(ordered, start=1):
        multiplier = m - rank + 1
        threshold = alpha / multiplier
        running_adjusted = max(running_adjusted, min(1.0, p_value * multiplier))
        reject = continue_rejecting and p_value <= threshold
        if not reject:
            continue_rejecting = False
        out[original_index] = {
            "index": original_index,
            "rank": rank,
            "p_value": p_value,
            "adjusted_p_value": running_adjusted,
            "threshold": threshold,
            "reject": reject,
        }

    return [item for item in out if item is not None]
