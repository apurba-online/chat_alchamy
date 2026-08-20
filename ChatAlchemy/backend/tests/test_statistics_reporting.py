import pytest

from chatalchemy.benchmark.statistics import holm_bonferroni, mcnemar_exact, paired_bootstrap_ci


def test_holm_bonferroni_reports_monotone_adjusted_p_values_in_original_order():
    raw = [0.01, 0.04, 0.03]
    result = holm_bonferroni(raw, alpha=0.05)

    assert [item["index"] for item in result] == [0, 1, 2]
    # Sorted p-values are .01, .03, .04 -> multipliers 3,2,1.
    # Holm adjusted values are .03, .06, .06, mapped back to original order.
    assert result[0]["adjusted_p_value"] == pytest.approx(0.03)
    assert result[1]["adjusted_p_value"] == pytest.approx(0.06)
    assert result[2]["adjusted_p_value"] == pytest.approx(0.06)
    assert result[0]["reject"] is True
    assert result[1]["reject"] is False
    assert result[2]["reject"] is False


def test_holm_rejects_invalid_p_values():
    with pytest.raises(ValueError, match="between 0 and 1"):
        holm_bonferroni([0.2, 1.2])


def test_exact_mcnemar_no_discordance_is_one():
    result = mcnemar_exact([True, False], [True, False])
    assert result["discordant"] == 0
    assert result["p_value"] == 1.0


def test_paired_bootstrap_is_deterministic_for_fixed_seed():
    first = paired_bootstrap_ci([1.0, 0.8, 0.6], [0.7, 0.6, 0.5], n_boot=200, seed=1729)
    second = paired_bootstrap_ci([1.0, 0.8, 0.6], [0.7, 0.6, 0.5], n_boot=200, seed=1729)
    assert first == second
    assert first["estimate"] == pytest.approx(0.2)
