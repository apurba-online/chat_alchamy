from __future__ import annotations

from chatalchemy.benchmark.generator import BENCHMARK_VERSION, ENTITY_POOLS, generate_cases


def _canonicals(pool):
    return {
        "drugs": set(pool.drugs),
        "compounds": set(pool.compounds),
        "targets": set(pool.targets),
        "conditions": set(pool.conditions),
        "genes": set(pool.genes),
        "aliases": {alias.lower() for alias, _ in pool.aliases},
        "alias_targets": {canonical.lower() for _, canonical in pool.aliases},
    }


def test_benchmark_version_is_explicit():
    assert BENCHMARK_VERSION.startswith("LiveBioEvidenceBench-v")


def test_entity_pools_are_disjoint_across_splits():
    names = list(ENTITY_POOLS)
    for i, left_name in enumerate(names):
        left = _canonicals(ENTITY_POOLS[left_name])
        for right_name in names[i + 1 :]:
            right = _canonicals(ENTITY_POOLS[right_name])
            for key in ("drugs", "targets", "conditions", "genes"):
                assert left[key].isdisjoint(right[key]), f"{key} leakage: {left_name} vs {right_name}"
            assert left["aliases"].isdisjoint(right["aliases"]), f"alias leakage: {left_name} vs {right_name}"
            assert left["alias_targets"].isdisjoint(right["alias_targets"]), f"alias canonical leakage: {left_name} vs {right_name}"


def test_aliases_resolve_within_same_split():
    for split, pool in ENTITY_POOLS.items():
        canonicals = {drug.lower() for drug in pool.drugs}
        for alias, canonical in pool.aliases:
            assert alias
            assert canonical.lower() in canonicals, f"{split}: {alias} maps outside its split"


def test_generation_is_deterministic_for_frozen_seed():
    a = generate_cases(300, 1729)
    b = generate_cases(300, 1729)
    assert a == b
    assert len({case.id for case in a}) == len(a)


def test_generated_cases_have_split_and_difficulty_metadata():
    cases = generate_cases(600, 1729)
    assert {case.split for case in cases} == {"dev", "test", "stress"}
    assert {case.difficulty for case in cases}.issubset({"easy", "medium", "hard"})
    assert all(case.family and case.sources and case.expected_operation for case in cases)
