from __future__ import annotations

from .generator import BenchmarkCase


def select_cases(
    cases: list[BenchmarkCase],
    *,
    split: str = "all",
    difficulty: str = "all",
    families: set[str] | None = None,
    limit: int | None = None,
    shard_index: int = 0,
    num_shards: int = 1,
) -> list[BenchmarkCase]:
    if num_shards < 1:
        raise ValueError("num_shards must be >= 1")
    if shard_index < 0 or shard_index >= num_shards:
        raise ValueError("shard_index must satisfy 0 <= shard_index < num_shards")
    selected = [
        case
        for case in cases
        if (split == "all" or case.split == split)
        and (difficulty == "all" or case.difficulty == difficulty)
        and (not families or case.family in families)
    ]
    selected = [case for index, case in enumerate(selected) if index % num_shards == shard_index]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        selected = selected[:limit]
    return selected
