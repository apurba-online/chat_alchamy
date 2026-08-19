from __future__ import annotations


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a or b else 1.0


def cluster_gene_profiles(profiles: dict[str, set[str]], threshold: float = 0.35) -> list[list[str]]:
    genes = sorted(profiles); graph = {g: set() for g in genes}
    for i, a in enumerate(genes):
        for b in genes[i + 1:]:
            if jaccard(profiles[a], profiles[b]) >= threshold:
                graph[a].add(b); graph[b].add(a)
    seen = set(); clusters = []
    for g in genes:
        if g in seen: continue
        stack = [g]; comp = []; seen.add(g)
        while stack:
            x = stack.pop(); comp.append(x)
            for y in graph[x]:
                if y not in seen: seen.add(y); stack.append(y)
        clusters.append(sorted(comp))
    return sorted(clusters, key=lambda c: (-len(c), c))
