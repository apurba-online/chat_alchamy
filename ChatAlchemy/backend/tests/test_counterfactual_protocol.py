from scripts.run_counterfactual import generate_cases


def test_counterfactual_suite_is_deterministic_and_stratified():
    a = generate_cases(120, 1729)
    b = generate_cases(120, 1729)
    assert a == b
    assert len(a) == 120
    assert len({row["id"] for row in a}) == 120
    assert {row["family"] for row in a} == {
        "mechanism_reversal",
        "regulatory_reversal",
        "target_reversal",
        "trial_status_reversal",
    }
    assert all(len(row["required"]) == 1 for row in a)
    assert all(len(row["forbidden"]) == 1 for row in a)
    assert all("Synthetic evaluation record" in row["evidence"] for row in a)
