"""Unit tests for verification scoring functions."""

import math
import pytest

from app.services.verification import (
    OUTCOME_HIT,
    OUTCOME_MISS,
    OUTCOME_FALSE_ALARM,
    OUTCOME_CORRECT_NEGATIVE,
    base_rate,
    brier_score,
    brier_skill_score,
    classify_outcome,
    csi,
    far,
    pod,
    reliability_bins,
    summarize,
    wilson_score_interval,
)


# ---------- classify_outcome ----------


def test_classify_outcome_hit():
    assert classify_outcome(0.8, observed=True, threshold=0.5) == OUTCOME_HIT


def test_classify_outcome_miss():
    assert classify_outcome(0.2, observed=True, threshold=0.5) == OUTCOME_MISS


def test_classify_outcome_false_alarm():
    assert classify_outcome(0.8, observed=False, threshold=0.5) == OUTCOME_FALSE_ALARM


def test_classify_outcome_correct_negative():
    assert classify_outcome(0.2, observed=False, threshold=0.5) == OUTCOME_CORRECT_NEGATIVE


def test_classify_outcome_at_threshold_is_yes():
    # >= threshold is treated as a yes-forecast.
    assert classify_outcome(0.5, observed=True, threshold=0.5) == OUTCOME_HIT
    assert classify_outcome(0.5, observed=False, threshold=0.5) == OUTCOME_FALSE_ALARM


# ---------- contingency table metrics ----------


def test_pod_perfect():
    assert pod(hits=10, misses=0) == 1.0


def test_pod_complete_miss():
    assert pod(hits=0, misses=10) == 0.0


def test_pod_no_events_returns_none():
    assert pod(hits=0, misses=0) is None


def test_far_no_false_alarms():
    assert far(hits=10, false_alarms=0) == 0.0


def test_far_all_false_alarms():
    assert far(hits=0, false_alarms=10) == 1.0


def test_far_no_yes_forecasts_returns_none():
    assert far(hits=0, false_alarms=0) is None


def test_csi_perfect():
    assert csi(hits=10, misses=0, false_alarms=0) == 1.0


def test_csi_typical():
    # 5 hits, 3 misses, 2 false alarms -> 5 / 10 = 0.5
    assert csi(hits=5, misses=3, false_alarms=2) == 0.5


def test_csi_no_activity_returns_none():
    assert csi(hits=0, misses=0, false_alarms=0) is None


# ---------- probabilistic scores ----------


def test_brier_score_perfect_certain_forecasts():
    preds = [(1.0, True), (0.0, False), (1.0, True), (0.0, False)]
    assert brier_score(preds) == 0.0


def test_brier_score_worst_case():
    # Forecast 0.0 when event happens, 1.0 when it doesn't.
    preds = [(0.0, True), (1.0, False)]
    assert brier_score(preds) == 1.0


def test_brier_score_50_50():
    preds = [(0.5, True), (0.5, False), (0.5, True), (0.5, False)]
    assert brier_score(preds) == 0.25


def test_brier_score_empty_returns_none():
    assert brier_score([]) is None


def test_base_rate_typical():
    preds = [(0.5, True), (0.5, False), (0.5, True), (0.5, True)]
    assert base_rate(preds) == 0.75


def test_base_rate_empty_returns_none():
    assert base_rate([]) is None


def test_brier_skill_score_better_than_climatology():
    # Forecasts perfectly track outcomes; reference is the base rate.
    preds = [(1.0, True), (0.0, False), (1.0, True), (0.0, False)]
    bss = brier_skill_score(preds, reference_probability=0.5)
    assert bss == 1.0  # Perfect skill versus 50/50 reference.


def test_brier_skill_score_zero_when_matches_reference():
    # Constant forecast at the base rate scores 0 BSS by construction.
    preds = [(0.5, True), (0.5, False), (0.5, True), (0.5, False)]
    bss = brier_skill_score(preds, reference_probability=0.5)
    assert bss == 0.0


# ---------- reliability bins ----------


def test_reliability_bins_empty_returns_empty():
    assert reliability_bins([]) == []


def test_reliability_bins_invalid_n():
    with pytest.raises(ValueError):
        reliability_bins([(0.5, True)], n_bins=0)


def test_reliability_bins_count_correctness():
    preds = [
        (0.05, False), (0.15, False),  # bin 0 (0.0-0.1) and bin 1 (0.1-0.2)
        (0.55, True),  (0.65, True),   # bin 5 and 6
        (0.95, True),  (1.00, True),   # bin 9 (last bin includes 1.0)
    ]
    bins = reliability_bins(preds, n_bins=10)
    counts = [b["n"] for b in bins]
    assert sum(counts) == 6
    assert bins[0]["n"] == 1
    assert bins[1]["n"] == 1
    assert bins[5]["n"] == 1
    assert bins[6]["n"] == 1
    assert bins[9]["n"] == 2  # 0.95 and 1.0


def test_reliability_bin_observed_frequency():
    # All forecasts in 0.7-0.8 bin; half observed.
    preds = [(0.75, True), (0.75, False), (0.75, True), (0.75, False)]
    bins = reliability_bins(preds, n_bins=10)
    bin_7 = bins[7]
    assert bin_7["n"] == 4
    assert bin_7["observed_frequency"] == 0.5
    assert bin_7["mean_forecast"] == 0.75


# ---------- summarize ----------


def test_summarize_empty():
    s = summarize([])
    assert s["n"] == 0
    assert s["pod"] is None
    assert s["reliability_bins"] == []


def test_summarize_typical():
    preds = [
        (0.9, True),   # hit
        (0.8, True),   # hit
        (0.7, False),  # false alarm
        (0.2, True),   # miss
        (0.1, False),  # correct negative
        (0.1, False),  # correct negative
    ]
    s = summarize(preds, threshold=0.5)
    assert s["n"] == 6
    assert s["hits"] == 2
    assert s["misses"] == 1
    assert s["false_alarms"] == 1
    assert s["correct_negatives"] == 2
    assert s["pod"] == pytest.approx(2 / 3)
    assert s["far"] == pytest.approx(1 / 3)
    assert s["csi"] == pytest.approx(2 / 4)
    assert s["base_rate"] == pytest.approx(3 / 6)

# ---------- wilson_score_interval ----------


def test_wilson_zero_n_returns_none():
    assert wilson_score_interval(0, 0) is None


def test_wilson_invalid_inputs_raise():
    with pytest.raises(ValueError):
        wilson_score_interval(5, 3)  # successes > n
    with pytest.raises(ValueError):
        wilson_score_interval(-1, 10)  # negative successes
    with pytest.raises(ValueError):
        wilson_score_interval(5, 10, confidence=0.42)  # unsupported level


def test_wilson_all_successes():
    # 10/10 should give a one-sided-style interval near [0.7, 1.0].
    lower, upper = wilson_score_interval(10, 10)
    assert lower < 1.0
    assert upper == 1.0
    assert lower > 0.6  # meaningful lower bound, not zero


def test_wilson_zero_successes():
    # 0/10 should give an interval near [0.0, 0.3].
    lower, upper = wilson_score_interval(0, 10)
    assert lower == 0.0
    assert upper > 0.0
    assert upper < 0.4


def test_wilson_textbook_example():
    # Wikipedia / Agresti example: 5 successes in 20 trials, 95% CI ~ [0.113, 0.476]
    lower, upper = wilson_score_interval(5, 20)
    assert 0.10 < lower < 0.13
    assert 0.45 < upper < 0.49


def test_wilson_contains_point_estimate():
    # The CI should always contain the point estimate p = successes/n.
    for successes, n in [(1, 10), (5, 20), (50, 100), (99, 100)]:
        lower, upper = wilson_score_interval(successes, n)
        p = successes / n
        assert lower <= p <= upper


def test_wilson_bounds_in_unit_interval():
    # CI bounds must always be in [0, 1] regardless of inputs.
    for successes, n in [(0, 1), (1, 1), (1, 5), (4, 5), (50, 50)]:
        lower, upper = wilson_score_interval(successes, n)
        assert 0.0 <= lower <= 1.0
        assert 0.0 <= upper <= 1.0
        assert lower <= upper


def test_wilson_confidence_levels():
    # 99% CI should be wider than 95% CI, which should be wider than 90% CI.
    s, n = 50, 100
    ci_90 = wilson_score_interval(s, n, confidence=0.90)
    ci_95 = wilson_score_interval(s, n, confidence=0.95)
    ci_99 = wilson_score_interval(s, n, confidence=0.99)

    width_90 = ci_90[1] - ci_90[0]
    width_95 = ci_95[1] - ci_95[0]
    width_99 = ci_99[1] - ci_99[0]
    assert width_90 < width_95 < width_99


# ---------- summarize includes CIs ----------


def test_summarize_includes_confidence_intervals_when_data_present():
    preds = [
        (0.9, True),
        (0.8, True),
        (0.7, False),
        (0.2, True),
        (0.1, False),
        (0.1, False),
    ]
    s = summarize(preds, threshold=0.5)
    assert "pod_ci" in s
    assert "far_ci" in s
    assert "csi_ci" in s
    # Each CI should be a (lower, upper) tuple/list, not None, when n > 0
    # and the relevant denominator > 0.
    assert s["pod_ci"] is not None
    assert s["far_ci"] is not None
    assert s["csi_ci"] is not None


def test_summarize_empty_returns_none_for_cis():
    s = summarize([])
    assert s["pod_ci"] is None
    assert s["far_ci"] is None
    assert s["csi_ci"] is None


def test_summarize_pod_ci_contains_pod():
    preds = [(0.9, True), (0.9, True), (0.2, True), (0.1, False)]
    s = summarize(preds, threshold=0.5)
    if s["pod"] is not None and s["pod_ci"] is not None:
        lower, upper = s["pod_ci"]
        assert lower <= s["pod"] <= upper