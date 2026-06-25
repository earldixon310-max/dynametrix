#!/usr/bin/env python3
"""judge_perturbation.py - DETECTOR_PERTURBATION_OVP candidate study (OVP real candidate #5).
Implements PRE_REGISTRATION_DETECTOR_PERTURBATION_OVP.md. First real instantiation of the adopted
OVP v0.2 reference template; Descriptor Justification Layer second contact.

Judges whether `perturbation_spread` (std of predicted_prob_ai across {original + valid paraphrases})
adds Held-out Discriminative Gain beyond folded confidence B = max(p,1-p) in predicting detector
correctness y, against the SAME cut points frozen by DETECTOR_OVP_CALIB.

  D > TAU_HI            -> Validated
  D < TAU_LO            -> Not-Validated   (mechanism-agnostic in v0.1)
  TAU_LO <= D <= TAU_HI -> Inconclusive
where D = median(HDG_AUC over R=200 stratified 50/50 PAIRED splits), no trimming.

Hybrid substrate: (B, y, domain) INHERITED + hash-verified from the calibration lock; the candidate
C = perturbation_spread (+ flip_rate sensitivity + text_length confound covariate) is MATERIALIZED
separately and hash-verified here. Non-gating: permuted-C foil, [B,length,domain] confound diagnostic
(eps_confound), flip-rate sensitivity panel. Single-execution under seed 0x5B5EAD.

The lock/H1 guard runs before any candidate or input load; only the single-execution argv
refusal and the constant seed/reps/out assignment precede it (v0.2 template).
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import ovp_guard
import compute_core

# --- constants PINNED in these locked bytes (identity-covered by H1 via SEALED_SOURCES) ----------
LOCK_TAG = "detector-perturbation-ovp-lock"
LOCKED_PATH = "judge_perturbation.py"
OUT_PATH = "detector_perturbation_results.json"
MASTER_SEED = 0x5B5EAD
R = 200
EPS_CONFOUND = 0.005

TAU_LO = 0.02458901317356486
TAU_HI = 0.06829080323934116
CALIB_RESULT_TAG = "detector-ovp-calib-result"
CALIB_RESULTS_JSON = os.path.join("..", "detector_truncation_ovp", "detector_calibration_results.json")

INHERITED_PER_EXAMPLE = os.path.join("..", "detector_truncation_ovp", "detector_per_example.csv")
EXPECTED_INHERITED_SHA256 = "24dac07828949a7e93fcc686ff3df70229c026195d3db873e688c1b401afc643"
MATERIALIZED_PER_EXAMPLE = "detector_perturbation_per_example.csv"
EXPECTED_MATERIALIZED_SHA256 = "ad5901b160b37c763752607f85cfd2f3ed2a3fe2bf5d0d48627ae5b1bddd5318"   # rev-2 materialization

MODEL_ID = "Hello-SimpleAI/chatgpt-detector-roberta"
MODEL_REVISION = "d2b342c61775d5dd0221808a79983ed3b86ffd86"
DATASET_SHA256 = "a29f8f2c0ff8f5eca1a1a3c07e771a28b0709d0f9f060a9024c935eaff615a47"
PARAPHRASER_ID = "Qwen/Qwen2.5-7B-Instruct"   # rev-2: 4-bit via bitsandbytes (AWQ unreachable on Windows)
PARAPHRASER_REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"
PARAPHRASE_SEED = 20260618
K_PARAPHRASES = 5
THETA_COSINE = 0.80
DELTA_JACCARD = 0.30
MIN_VALID = 3          # operative per-text gate: texts with < MIN_VALID valid paraphrases are excluded (substrate attrition)

# EVERY source file on the sealed compute path (identity-covered by H1).
SEALED_SOURCES = {
    LOCKED_PATH: os.path.abspath(__file__),
    "compute_core.py": os.path.abspath(compute_core.__file__),
    "ovp_guard.py": os.path.abspath(ovp_guard.__file__),
    ".gitattributes": os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gitattributes"),
}
EXPECTED_INPUT_SHA256 = {
    INHERITED_PER_EXAMPLE: EXPECTED_INHERITED_SHA256,
    MATERIALIZED_PER_EXAMPLE: EXPECTED_MATERIALIZED_SHA256,
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_cut_points():
    if not os.path.exists(CALIB_RESULTS_JSON):
        raise SystemExit("ABORT: %s not found; cannot verify inherited cut points." % CALIB_RESULTS_JSON)
    cal = json.load(open(CALIB_RESULTS_JSON))
    if not (cal.get("tau_lo") == TAU_LO and cal.get("tau_hi") == TAU_HI):
        raise SystemExit("ABORT: hardcoded cut points (%r, %r) != calibration result (%r, %r); drift."
                         % (TAU_LO, TAU_HI, cal.get("tau_lo"), cal.get("tau_hi")))


def sealed_loader():
    """Loads the REAL candidate. Reached ONLY after the guard verifies the lock + input hashes."""
    df_inh = pd.read_csv(INHERITED_PER_EXAMPLE)
    df_mat = pd.read_csv(MATERIALIZED_PER_EXAMPLE)
    # id-set identity: materialized must cover exactly the inherited example set (sec 2)
    inh_ids, mat_ids = df_inh["id"].tolist(), df_mat["id"].tolist()
    if len(inh_ids) != len(set(inh_ids)) or len(mat_ids) != len(set(mat_ids)):
        raise SystemExit("ABORT: duplicate ids in inherited or materialized per-example.")
    if set(inh_ids) != set(mat_ids):
        raise SystemExit("ABORT: materialized id set != inherited id set (missing/extra ids).")
    df = df_inh.merge(df_mat, on="id", how="inner", validate="one_to_one")
    if len(df) != len(df_inh):
        raise SystemExit("ABORT: id join did not preserve the example set.")
    n_total = len(df)
    # OPERATIVE per-text gate (sec 6): include only texts with >= MIN_VALID valid paraphrases; the rest
    # are honestly EXCLUDED as substrate attrition (the verdict is scope-stamped to the paraphraseable subset).
    incl = df["n_valid"].to_numpy(int) >= MIN_VALID
    df = df[incl].reset_index(drop=True)
    n_included, n_excluded = int(len(df)), int(n_total - int(incl.sum()))
    if n_included == 0:
        raise SystemExit("ABORT: no texts cleared the per-text >=%d-valid gate." % MIN_VALID)
    B = df["B_confidence"].to_numpy(float)
    y = df["y_correct"].to_numpy(int)
    C = df["perturbation_spread"].to_numpy(float)
    C_alt = df["flip_rate"].to_numpy(float)
    length = df["text_length"].to_numpy(float)
    domain_oh = pd.get_dummies(df["source_domain"].astype("category")).reindex(
        sorted(df["source_domain"].astype("category").cat.categories), axis=1).to_numpy(float)
    Z = np.column_stack([length, domain_oh])
    info = {"n_total": n_total, "n_included": n_included, "n_excluded_attrition": n_excluded,
            "attrition_fraction": n_excluded / n_total,
            "domains": sorted(df["source_domain"].unique().tolist())}
    return B, y, C, C_alt, Z, info


def main():
    # SINGLE-EXECUTION IS STRUCTURAL (cold-pass #3 (a) fix). The judge takes NO arguments: the only
    # runnable configuration is the canonical seed/reps/out. A flag surface (--seed/--reps/--out) that
    # computes the sealed HDG under varied params would let an operator run many configs to new output
    # files and cherry-pick the verdict, defeating single-execution. Any extra argv is refused; the
    # output-exists guard then enforces once-per-checkout. Reproducibility verification is a fresh
    # checkout of the lock tag + this canonical run, compared to the committed result tag.
    if len(sys.argv) > 1:
        sys.exit("ABORT: judge_perturbation.py takes NO arguments; single-execution permits only the "
                 "canonical no-flag run (seed=%s, reps=%d, out=%s)." % (hex(MASTER_SEED), R, OUT_PATH))
    seed, reps, out = MASTER_SEED, R, OUT_PATH

    try:
        ovp_guard.assert_locked_or_refuse(LOCK_TAG, SEALED_SOURCES, os.path.abspath(__file__))
        ovp_guard.output_exists_or_refuse(out)
        ovp_guard.verify_input_hashes(EXPECTED_INPUT_SHA256)   # empty/placeholder -> refuse
    except ovp_guard.GuardRefusal as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(2)

    verify_cut_points()
    print("[1/2] inheriting (B, y, domain) + joining materialized (spread, flip_rate, length) ...")
    B, y, C, C_alt, Z, info = sealed_loader()
    print("      PARAPHRASEABLE SUBSET: %d of %d examples (substrate attrition %d = %.1f%%); accuracy=%.3f n_errors=%d domains=%d"
          % (info["n_included"], info["n_total"], info["n_excluded_attrition"], 100 * info["attrition_fraction"],
             y.mean(), int((y == 0).sum()), len(info["domains"])))

    print("[2/2] judging `perturbation_spread` (+ foil + confound + flip-rate) over %d paired splits ..." % reps)
    res = compute_core.compute_sealed(B, y, C, C_alt, Z, TAU_LO, TAU_HI, EPS_CONFOUND, seed, reps)
    res["support_nongating"]["n_examples"] = int(len(B))
    res["support_nongating"]["n_errors"] = int((y == 0).sum())
    res["support_nongating"]["n_total_substrate"] = int(info["n_total"])
    res["support_nongating"]["n_excluded_substrate_attrition"] = int(info["n_excluded_attrition"])
    res["support_nongating"]["attrition_fraction"] = float(info["attrition_fraction"])
    res["scope"] = ("Verdict scope: the %d of %d RAID examples for which the pre-committed paraphrase-quality "
                    "control produced >= %d valid paraphrases (substrate attrition %.1f%%, concentrated in poetry/reddit "
                    "under this paraphraser/config). Says nothing about detector reliability on the excluded texts."
                    % (info["n_included"], info["n_total"], MIN_VALID, 100 * info["attrition_fraction"]))
    res["meta"] = {
        "candidate": "perturbation_spread", "baseline": "confidence (folded max(p,1-p))",
        "master_seed_canonical": hex(MASTER_SEED), "seed_used": hex(seed),
        "foil_seed_xor": hex(compute_core.FOIL_SEED_XOR), "R_canonical": R, "reps_used": reps,
        "eps_confound": EPS_CONFOUND,
        "model_id": MODEL_ID, "model_revision": MODEL_REVISION, "dataset_sha256": DATASET_SHA256,
        "paraphraser_id": PARAPHRASER_ID, "paraphraser_revision": PARAPHRASER_REVISION,
        "paraphrase_seed": PARAPHRASE_SEED, "K_paraphrases": K_PARAPHRASES,
        "theta_cosine": THETA_COSINE, "delta_jaccard": DELTA_JACCARD, "spread_ddof": 1,
        "inherited_per_example_sha256": sha256_file(INHERITED_PER_EXAMPLE),
        "materialized_per_example_sha256": sha256_file(MATERIALIZED_PER_EXAMPLE),
        "estimator": compute_core.ESTIMATOR_DESC, "cut_points_provenance": CALIB_RESULT_TAG,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
    sg = res["support_nongating"]
    print(json.dumps({k: res[k] for k in ["D_median_HDG_AUC", "verdict", "tau_lo", "tau_hi", "band_relation"]}, indent=2))
    print("foil (non-gating): D_foil=%.6f verdict=%s met=%s clears_tau_lo=%s" %
          (sg["foil_D_median"], sg["foil_verdict"], sg["foil_pre_commitment_met"], sg["foil_clears_tau_lo"]))
    print("confound (non-gating): HDG_ext=%.6f gap=%.6f genuine=%s | flip_rate D=%.6f (%s)" %
          (sg["confound_HDG_extended_median"], sg["confound_gap"], sg["confound_genuine"],
           sg["flip_rate_D_median"], sg["flip_rate_verdict"]))


if __name__ == "__main__":
    main()
