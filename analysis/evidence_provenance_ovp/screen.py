"""screen.py — Evidence Provenance Stage 0 y-free feasibility screen.

Reads ONLY `stage0_screen_input.csv` (qid, entropy, confidence, max_retrieval_score). Computes the
four pre-registered y-free statistics, applies the LOCKED decision rule, writes the three-way verdict.
Imports NO grader; reads NO gold/correctness column. The firewall is the import graph + the header check.
"""
import csv
import json
import numpy as np

import config

# NO `import grader`, and no access to any correctness/gold source. (Firewall.)


def load_features(path):
    """Read the four-column screen input; assert the firewall schema."""
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        assert header == config.SCREEN_INPUT_COLUMNS, \
            "FIREWALL: header %r != %r" % (header, config.SCREEN_INPUT_COLUMNS)
        ent, conf, mx = [], [], []
        for row in r:
            assert len(row) == 4, "screen input row must have exactly four fields, got %d" % len(row)
            ent.append(float(row[1])); conf.append(float(row[2])); mx.append(float(row[3]))
    return np.asarray(ent, float), np.asarray(conf, float), np.asarray(mx, float)


def multiple_R(entropy, confidence, max_score):
    """Joint least-squares fit  entropy ~ 1 + confidence + max_score ; return (multiple R, R^2).

    Multiple R (not max pairwise correlation): captures the joint explanatory power of BOTH baseline
    features, which is the redundancy the rule checks. Fit on the same data the decision is read from.
    """
    X = np.column_stack([np.ones_like(confidence), confidence, max_score])
    beta, *_ = np.linalg.lstsq(X, entropy, rcond=None)
    pred = X @ beta
    ss_res = float(np.sum((entropy - pred) ** 2))
    ss_tot = float(np.sum((entropy - entropy.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(np.sqrt(max(r2, 0.0))), float(r2)


def decide(entropy, confidence, max_score):
    sd = float(np.std(entropy, ddof=1))
    R, r2 = multiple_R(entropy, confidence, max_score)
    # LOCKED rule: CLOSE if (multiple-R >= rho) OR (sd < eps_sd); else PROCEED.
    # Degeneracy is checked FIRST: if entropy has no variance the regression R is ill-defined, and a
    # broken-retriever close is a different finding than a redundancy close (pre-reg sec 5/8). Both
    # produce verdict CLOSE; only the annotation label differs. This precedence does not change the
    # locked rule's CLOSE/PROCEED outcome, only which CLOSE arm is recorded.
    if sd < config.EPS_SD:
        verdict = "CLOSE-degenerate"
    elif R >= config.RHO:
        verdict = "CLOSE-redundant"
    else:
        verdict = "PROCEED"
    return verdict, sd, R, r2


def main():
    entropy, confidence, max_score = load_features(config.SCREEN_INPUT_PATH)
    verdict, sd, R, r2 = decide(entropy, confidence, max_score)
    result = {
        "study": "EVIDENCE_PROVENANCE_STAGE0",
        "verdict": verdict,  # PROCEED | CLOSE-redundant | CLOSE-degenerate
        "decision_rule": {
            "rho": config.RHO, "eps_sd_nats": config.EPS_SD,
            "multiple_R": R, "R_squared": r2, "sd_entropy_nats": sd,
            "close_redundant": bool(R >= config.RHO),
            "close_degenerate": bool(sd < config.EPS_SD),
        },
        # descriptive y-free statistics (computed, reported, NOT used by the rule)
        "entropy_spread": {
            "mean": float(entropy.mean()), "sd": sd,
            "min": float(entropy.min()), "max": float(entropy.max()),
            "frac_top_decile_bin": _top_decile_fraction(entropy),
        },
        "corr_entropy_confidence_pearson": float(np.corrcoef(entropy, confidence)[0, 1]),
        "corr_entropy_maxscore_pearson": float(np.corrcoef(entropy, max_score)[0, 1]),
        "n": int(len(entropy)),
        "pins": {k: getattr(config, k) for k in config.MANIFEST_PINS},
    }
    with open(config.RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("VERDICT:", verdict)
    print("  multiple_R=%.4f  sd_entropy=%.4f nats  (rho=%.2f, eps_sd=%.2f)"
          % (R, sd, config.RHO, config.EPS_SD))


def _top_decile_fraction(x):
    counts, _ = np.histogram(x, bins=10)
    return float(counts.max() / counts.sum()) if counts.sum() else 1.0


if __name__ == "__main__":
    main()
