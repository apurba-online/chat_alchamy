from chatalchemy.benchmark import generate_cases


def test_publication_scale_generator_is_deterministic():
    a = generate_cases(1500, 42)
    b = generate_cases(1500, 42)
    assert len(a) == 1500
    assert a == b
    assert len({x.id for x in a}) == 1500
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
