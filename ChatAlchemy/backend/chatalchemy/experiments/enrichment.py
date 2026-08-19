from __future__ import annotations
from dataclasses import dataclass
from math import comb

@dataclass(frozen=True)
class EnrichmentResult:
    term: str
    overlap: tuple[str, ...]
    p_value: float
    fdr: float


def hypergeom_sf(k_minus_one: int, population: int, successes: int, draws: int) -> float:
    lo = max(k_minus_one + 1, 0); hi = min(successes, draws); denom = comb(population, draws)
    if denom == 0: return 1.0
    return min(1.0, sum(comb(successes, k) * comb(population - successes, draws - k) for k in range(lo, hi + 1)) / denom)


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    m = len(p_values); order = sorted(range(m), key=lambda i: p_values[i]); adjusted = [1.0] * m; running = 1.0
    for rank_idx in range(m - 1, -1, -1):
        i = order[rank_idx]; rank = rank_idx + 1; running = min(running, p_values[i] * m / rank); adjusted[i] = min(1.0, running)
    return adjusted


def overrepresentation(query_genes: set[str], gene_sets: dict[str, set[str]], universe: set[str]) -> list[EnrichmentResult]:
    q = query_genes & universe; raw = []
    for term, genes in gene_sets.items():
        gs = genes & universe; overlap = sorted(q & gs)
        if not overlap: continue
        p = hypergeom_sf(len(overlap) - 1, len(universe), len(gs), len(q)); raw.append((term, tuple(overlap), p))
    fdr = benjamini_hochberg([x[2] for x in raw])
    return sorted([EnrichmentResult(t, o, p, qv) for (t, o, p), qv in zip(raw, fdr)], key=lambda x: (x.fdr, x.p_value, x.term))
