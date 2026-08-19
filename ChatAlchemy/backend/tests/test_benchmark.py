from collections import Counter

from chatalchemy.benchmark import benchmark_fingerprint, generate_cases, validate_cases


def test_publication_scale_generator_is_deterministic_and_validated():
    a = generate_cases(1500, 42)
    b = generate_cases(1500, 42)
    assert len(a) == 1500
    assert a == b
    assert benchmark_fingerprint(a) == benchmark_fingerprint(b)
    manifest = validate_cases(a)
    assert manifest["case_count"] == 1500
    assert manifest["split_counts"] == {"dev": 300, "test": 900, "stress": 300}
    assert len({x.id for x in a}) == 1500
    assert len({x.task_signature for x in a}) == 1500
    assert manifest["task_signature_count"] == 1500
    assert 0 < manifest["surface_question_count"] <= 1500
    assert {x.family for x in a} >= {
        "identity",
        "label",
        "approval",
        "trials",
        "target",
        "cross",
        "gene",
        "compound",
        "user_approval",
        "user_trials",
        "user_target",
    }
    assert all(x.oracle == "independent_live_api_oracle" for x in a)
    assert all(len(x.params["candidates"]) == 3 for x in a)
    assert {x.difficulty for x in a} == {"easy", "medium", "hard"}


def test_families_are_stratified_within_each_public_split():
    cases = generate_cases(1500, 1729)
    for split in ("dev", "test", "stress"):
        counts = Counter(x.family for x in cases if x.split == split)
        assert max(counts.values()) - min(counts.values()) <= 1


def test_primary_entities_are_disjoint_across_splits():
    cases = generate_cases(1500, 1729)
    by_type = {}
    for entity_type in ("drug", "target", "gene"):
        by_type[entity_type] = {
            split: {
                x.primary_entity.lower()
                for x in cases
                if x.split == split and x.primary_entity_type == entity_type
            }
            for split in ("dev", "test", "stress")
        }
        assert not (by_type[entity_type]["dev"] & by_type[entity_type]["test"])
        assert not (by_type[entity_type]["dev"] & by_type[entity_type]["stress"])
        assert not (by_type[entity_type]["test"] & by_type[entity_type]["stress"])
