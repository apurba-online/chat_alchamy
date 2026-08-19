import pytest

from chatalchemy.benchmark import generate_cases, select_cases


def test_shards_are_disjoint_and_cover_selected_cases():
    cases = generate_cases(1500, 1729)
    expected = select_cases(cases, split="test")
    shards = [select_cases(cases, split="test", num_shards=5, shard_index=i) for i in range(5)]
    ids = [{case.id for case in shard} for shard in shards]
    assert sum(len(group) for group in ids) == len(expected)
    assert set().union(*ids) == {case.id for case in expected}
    for i, left in enumerate(ids):
        for right in ids[i + 1:]:
            assert not left & right


def test_limit_is_applied_after_split_and_shard_selection():
    cases = generate_cases(1500, 1729)
    selected = select_cases(cases, split="test", num_shards=3, shard_index=1, limit=7)
    assert len(selected) == 7
    assert all(case.split == "test" for case in selected)


def test_invalid_shard_configuration_is_rejected():
    cases = generate_cases(1500, 1729)
    with pytest.raises(ValueError):
        select_cases(cases, num_shards=0)
    with pytest.raises(ValueError):
        select_cases(cases, num_shards=2, shard_index=2)
