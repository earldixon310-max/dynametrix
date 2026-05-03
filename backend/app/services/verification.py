"""Verification scoring functions for forecast performance.

Pure functions — no database, no I/O. All inputs are passed as
arguments, all outputs are returned. This keeps the math testable in
isolation and protects the verification record from changes to data
plumbing elsewhere in the system.

Conventions:
- A "prediction" is a tuple (probability: float in [0,1], observed: bool).
- The decision threshold turns a probability into a yes/no forecast.
- 'hit', 'miss', 'false_alarm', 'correct_negative' are the four cells of
  the standard 2x2 contingency table for binary forecasts.
"""

from typing import Iterable, List, Optional, Tuple
import math

# A single (forecast probability, ground truth) pair.
Prediction = Tuple[float, bool]


# ---------------------------------------------------------------------------
# Outcome classification
# ---------------------------------------------------------------------------

OUTCOME_HIT = "hit"
OUTCOME_MISS = "miss"
OUTCOME_FALSE_ALARM = "false_alarm"
OUTCOME_CORRECT_NEGATIVE = "correct_negative"


def classify_outcome(
    predicted_probability: float,
    observed: bool,
    threshold: float = 0.5,
) -> str:
    """Classify a single prediction into one of the 2x2 contingency cells.

    threshold: probability cutoff for binary forecast. A forecast at or
    above the threshold is treated as 'yes'.
    """
    forecast_yes = predicted_probability >= threshold
    if forecast_yes and observed:
        return OUTCOME_HIT
    if forecast_yes and not observed:
        return OUTCOME_FALSE_ALARM
    if not forecast_yes and observed:
        return OUTCOME_MISS
    return OUTCOME_CORRECT_NEGATIVE


# ---------------------------------------------------------------------------
# Contingency table metrics
# ---------------------------------------------------------------------------


def pod(hits: int, misses: int) -> Optional[float]:
    """Probability of Detection (a.k.a. hit rate, recall, sensitivity).

    POD = hits / (hits + misses)
    Returns None when no events were observed (denominator zero).
    """
    denom = hits + misses
    if denom == 0:
        return None
    return hits / denom


def far(hits: int, false_alarms: int) -> Optional[float]:
    """False Alarm Ratio (the share of forecasts of yes that were wrong).

    FAR = false_alarms / (hits + false_alarms)
    Returns None when no 'yes' forecasts were issued.
    """
    denom = hits + false_alarms
    if denom == 0:
        return None
    return false_alarms / denom


def csi(hits: int, misses: int, false_alarms: int) -> Optional[float]:
    """Critical Success Index (Threat Score).

    CSI = hits / (hits + misses + false_alarms)
    Returns None when there were no events and no yes-forecasts.
    """
    denom = hits + misses + false_alarms
    if denom == 0:
        return None
    return hits / denom


# ---------------------------------------------------------------------------
# Probabilistic scores
# ---------------------------------------------------------------------------


def brier_score(predictions: Iterable[Prediction]) -> Optional[float]:
    """Mean squared error between forecast probability and observed outcome.

    BS = mean((p - o)^2) where o is 0 or 1.
    Range [0, 1]. Lower is better.
    """
    items = list(predictions)
    if not items:
        return None
    return sum((p - (1.0 if o else 0.0)) ** 2 for p, o in items) / len(items)


def brier_skill_score(
    predictions: Iterable[Prediction],
    reference_probability: float,
) -> Optional[float]:
    """Brier Skill Score relative to a constant reference forecast.

    BSS = 1 - BS / BS_reference
    Positive: better than the reference. Negative: worse.
    Common reference: climatological base rate (observed event frequency).
    """
    items = list(predictions)
    if not items:
        return None

    bs = brier_score(items)
    if bs is None:
        return None

    bs_ref = brier_score([(reference_probability, o) for _, o in items])
    if bs_ref is None or bs_ref == 0:
        return None
    return 1 - (bs / bs_ref)


def base_rate(predictions: Iterable[Prediction]) -> Optional[float]:
    """Climatological base rate (fraction of observations that were positive)."""
    items = list(predictions)
    if not items:
        return None
    return sum(1 for _, o in items if o) / len(items)


# ---------------------------------------------------------------------------
# Reliability diagram bins
# ---------------------------------------------------------------------------


def reliability_bins(
    predictions: Iterable[Prediction],
    n_bins: int = 10,
) -> List[dict]:
    """Bin predictions by forecast probability and compute observed
    frequency per bin. Used to render reliability (calibration) diagrams.

    Returns a list of dicts with keys:
        bin_lower, bin_upper, n, mean_forecast, observed_frequency
    """
    items = list(predictions)
    if not items:
        return []
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")

    bins: List[dict] = []
    for i in range(n_bins):
        lo = i / n_bins
        hi = (i + 1) / n_bins

        if i == n_bins - 1:
            in_bin = [(p, o) for p, o in items if lo <= p <= hi]
        else:
            in_bin = [(p, o) for p, o in items if lo <= p < hi]

        if not in_bin:
            bins.append(
                {
                    "bin_lower": lo,
                    "bin_upper": hi,
                    "n": 0,
                    "mean_forecast": (lo + hi) / 2,
                    "observed_frequency": None,
                }
            )
            continue

        mean_fc = sum(p for p, _ in in_bin) / len(in_bin)
        obs_freq = sum(1 for _, o in in_bin if o) / len(in_bin)
        bins.append(
            {
                "bin_lower": lo,
                "bin_upper": hi,
                "n": len(in_bin),
                "mean_forecast": mean_fc,
                "observed_frequency": obs_freq,
            }
        )

    return bins

# ---------------------------------------------------------------------------
# Confidence intervals on proportions
# ---------------------------------------------------------------------------


def wilson_score_interval(
    successes: int,
    n: int,
    confidence: float = 0.95,
) -> Optional[Tuple[float, float]]:
    """Wilson score confidence interval for a binomial proportion.

    More accurate than the normal-approximation interval, especially for
    small n or proportions near 0 or 1. Used here for POD, FAR, and CSI,
    all of which are proportions estimated from the contingency table.

    Args:
        successes: number of "successes" (e.g., hits for POD).
        n:         total number of trials (e.g., hits + misses for POD).
        confidence: confidence level. Supports 0.90, 0.95, 0.99.

    Returns:
        (lower, upper) bounds in [0, 1], or None if n == 0.
    """
    if n == 0:
        return None
    if successes < 0 or successes > n:
        raise ValueError(f"successes={successes} must be in [0, {n}]")

    z_table = {0.90: 1.6449, 0.95: 1.9600, 0.99: 2.5758}
    if confidence not in z_table:
        raise ValueError(
            f"Unsupported confidence level {confidence}. "
            "Use 0.90, 0.95, or 0.99."
        )
    z = z_table[confidence]
    z_sq = z * z

    p = successes / n
    denom = 1.0 + z_sq / n
    center = (p + z_sq / (2.0 * n)) / denom
    half_width = (z * math.sqrt(p * (1.0 - p) / n + z_sq / (4.0 * n * n))) / denom

    lower = max(0.0, center - half_width)
    upper = min(1.0, center + half_width)
    return (lower, upper)

# ---------------------------------------------------------------------------
# Aggregate summary
# ---------------------------------------------------------------------------


def summarize(
    predictions: Iterable[Prediction],
    threshold: float = 0.5,
    n_bins: int = 10,
) -> dict:
    """Compute a complete verification summary for a set of predictions.

    This is the entry point most callers will use. Returns a single
    dict with all metrics, sample size, and bins.
    """
    items = list(predictions)
    n = len(items)

    if n == 0:
        return {
            "n": 0,
            "threshold": threshold,
            "hits": 0,
            "misses": 0,
            "false_alarms": 0,
            "correct_negatives": 0,
            "pod": None,
            "pod_ci": None,
            "far": None,
            "far_ci": None,
            "csi": None,
            "csi_ci": None,
            "brier": None,
            "brier_skill_score": None,
            "base_rate": None,
            "reliability_bins": [],
        }

    hits = misses = false_alarms = correct_negatives = 0
    for p, o in items:
        outcome = classify_outcome(p, o, threshold)
        if outcome == OUTCOME_HIT:
            hits += 1
        elif outcome == OUTCOME_MISS:
            misses += 1
        elif outcome == OUTCOME_FALSE_ALARM:
            false_alarms += 1
        else:
            correct_negatives += 1

    rate = base_rate(items)

    return {
        "n": n,
        "threshold": threshold,
        "hits": hits,
        "misses": misses,
        "false_alarms": false_alarms,
        "correct_negatives": correct_negatives,
        "pod": pod(hits, misses),
        "pod_ci": wilson_score_interval(hits, hits + misses),
        "far": far(hits, false_alarms),
        "far_ci": wilson_score_interval(false_alarms, hits + false_alarms),
        "csi": csi(hits, misses, false_alarms),
        "csi_ci": wilson_score_interval(hits, hits + misses + false_alarms),
        "brier": brier_score(items),
        "brier_skill_score": brier_skill_score(items, rate) if rate is not None else None,
        "base_rate": rate,
        "reliability_bins": reliability_bins(items, n_bins=n_bins),
    }