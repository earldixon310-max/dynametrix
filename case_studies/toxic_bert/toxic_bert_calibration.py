"""
Toxic-BERT Calibration Verification - Inference and Calibration Analysis

Pre-registration: case_studies/toxic_bert/PRE_REGISTRATION_TOXIC_BERT_v1.md

This script is FROZEN at the lock commit. Per pre-registration Section 4 and
Section 9, the inference parameters and analysis methodology must not be
modified between the lock commit and the recording of the calibration outcome.

Modes:
  setup : Materialize Civil Comments validation subsample (5,000 examples,
          deterministically selected at seed 150914), pin unitary/toxic-bert
          model revision via the HuggingFace Hub, compute SHA-256 hashes.
          Run once during setup. Output values are filled into the
          pre-registration document immediately before the lock commit.

  run   : Verify locked artifacts, run inference on all 5,000 examples at
          the pinned model revision (extracting the sigmoid of the toxic
          head, index 0 of the 6-class multi-label output), compute
          reliability bins per pre-reg Section 5, apply decision criteria
          per Section 6, write per-example predictions and aggregate
          calibration outputs.

Usage:
  python toxic_bert_calibration.py setup
  python toxic_bert_calibration.py run
"""

import argparse
import csv
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np


# --- Pre-registered configuration (pre-reg Sections 2, 3, 4, 5, 6) ---

MODEL_NAME = "unitary/toxic-bert"
DATASET_NAME = "google/civil_comments"
DATASET_SPLIT = "validation"

# Subsample configuration (pre-reg Section 3.1)
SUBSAMPLE_SEED = 150914
SUBSAMPLE_SIZE = 5000

# Output extraction (pre-reg Section 4.2)
TOXIC_LABEL_INDEX = 0  # The 'toxic' head is index 0 in unitary/toxic-bert's
                       # 6-output multi-label classifier:
                       #   [toxic, severe_toxic, obscene, threat, insult, identity_hate]
TOXICITY_BINARIZATION_THRESHOLD = 0.5  # Civil Comments labels are continuous
                                       # in [0, 1]; >= 0.5 is the standard
                                       # binary positive (pre-reg Section 4.2).
MAX_TOKEN_LENGTH = 512

# Reliability binning (pre-reg Section 5)
K_BINS = 10
MIN_BIN_N = 30
WILSON_Z = 1.96  # 95% CI

# Decision-criterion fractions (pre-reg Section 6.1)
STRONG_FRAC = 0.9
ACCEPTABLE_FRAC = 0.8
DRIFT_FRAC = 0.5

# Output formatting precision
PROB_DECIMALS = 6


# --- Paths ---

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_CSV = SCRIPT_DIR / "civil_comments_validation_subsample.csv"
DATA_HASH = SCRIPT_DIR / "civil_comments_validation_subsample_sha256.txt"
MODEL_REVISION_FILE = SCRIPT_DIR / "model_revision.txt"
PREDICTIONS_CSV = SCRIPT_DIR / "predictions.csv"
CALIB_SCORES_CSV = SCRIPT_DIR / "calibration_scores.csv"
CALIB_SUMMARY_JSON = SCRIPT_DIR / "calibration_summary.json"


# --- Helpers ---

def wilson_ci(k, n, z=WILSON_Z):
    """Wilson score 95% confidence interval for proportion p = k/n.

    Returns (lower, upper) clamped to [0, 1].
    """
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    margin = (z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --- Setup: materialize subsample and pin model revision -------------------

def setup():
    print("=" * 72)
    print("Toxic-BERT Calibration - SETUP MODE")
    print("Pre-registration: PRE_REGISTRATION_TOXIC_BERT_v1.md")
    print("=" * 72)
    print()

    existing = [p for p in (DATA_CSV, DATA_HASH, MODEL_REVISION_FILE) if p.exists()]
    if existing:
        print("ERROR: setup outputs already exist:")
        for p in existing:
            print(f"  - {p}")
        print()
        print("Refusing to overwrite. Move/delete these files and re-run.")
        sys.exit(1)

    # 1. Pin model revision via HuggingFace Hub
    print("Step 1/3: Pinning unitary/toxic-bert model revision...")
    try:
        from huggingface_hub import HfApi
    except ImportError as e:
        print(f"ERROR: huggingface-hub not installed: {e}")
        print("Install with: pip install huggingface-hub")
        sys.exit(1)
    api = HfApi()
    repo_info = api.model_info(MODEL_NAME)
    revision = repo_info.sha
    print(f"  Model: {MODEL_NAME}")
    print(f"  Revision (HF commit hash): {revision}")
    MODEL_REVISION_FILE.write_text(revision + "\n", encoding="utf-8")
    print(f"  Wrote {MODEL_REVISION_FILE.name}")
    print()

    # 2. Load Civil Comments validation
    print("Step 2/3: Materializing Civil Comments validation subsample...")
    try:
        import datasets
    except ImportError as e:
        print(f"ERROR: datasets library not installed: {e}")
        print("Install with: pip install datasets")
        sys.exit(1)

    print(f"  Loading {DATASET_NAME} ({DATASET_SPLIT} split)...")
    ds = datasets.load_dataset(DATASET_NAME, split=DATASET_SPLIT)
    n_full = len(ds)
    print(f"  Full validation split: {n_full} examples")

    # 3. Deterministic subsample at seed 150914
    print(f"  Subsampling {SUBSAMPLE_SIZE} examples at seed {SUBSAMPLE_SEED}...")
    rng = random.Random(SUBSAMPLE_SEED)
    all_indices = list(range(n_full))
    rng.shuffle(all_indices)
    selected_indices = sorted(all_indices[:SUBSAMPLE_SIZE])

    # Materialize as CSV. Columns: idx, text, toxicity_score, label.
    # Civil Comments dataset field names may vary slightly across versions;
    # we probe for the canonical field names and adapt.
    sample0 = ds[selected_indices[0]]
    text_field = "text" if "text" in sample0 else "comment_text" if "comment_text" in sample0 else None
    if text_field is None:
        print(f"ERROR: could not locate a text field in the dataset. "
              f"Available fields: {list(sample0.keys())}")
        sys.exit(1)
    if "toxicity" not in sample0:
        print(f"ERROR: could not locate a 'toxicity' field in the dataset. "
              f"Available fields: {list(sample0.keys())}")
        sys.exit(1)

    print(f"  Text field: '{text_field}'")
    print(f"  Toxicity field: 'toxicity'")
    print(f"  Writing CSV...")

    with open(DATA_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["idx", "text", "toxicity_score", "label"])
        for idx in selected_indices:
            ex = ds[idx]
            text = ex[text_field]
            toxicity_score = float(ex["toxicity"])
            label = 1 if toxicity_score >= TOXICITY_BINARIZATION_THRESHOLD else 0
            writer.writerow([idx, text, f"{toxicity_score:.6f}", label])
    print(f"  Wrote {DATA_CSV.name} ({SUBSAMPLE_SIZE} rows)")
    print()

    # 4. Compute SHA-256 of materialized CSV
    print("Step 3/3: Computing SHA-256 of materialized subsample CSV...")
    data_hash = file_sha256(DATA_CSV)
    DATA_HASH.write_text(data_hash + "\n", encoding="utf-8")
    print(f"  SHA-256: {data_hash}")
    print(f"  Wrote {DATA_HASH.name}")
    print()

    print("=" * 72)
    print("SETUP COMPLETE")
    print("=" * 72)
    print()
    print("FILL THESE VALUES INTO PRE_REGISTRATION_TOXIC_BERT_v1.md:")
    print()
    print(f"  Section 2.1 / Revision:         {revision}")
    print(f"  Section 3.1 / SHA-256 of test:  {data_hash}")
    print()
    print("Then commit, in a single lock commit, all of:")
    print("  - PRE_REGISTRATION_TOXIC_BERT_v1.md (with the values above filled in)")
    print("  - toxic_bert_calibration.py")
    print("  - requirements.txt")
    print(f"  - {DATA_CSV.name}")
    print(f"  - {DATA_HASH.name}")
    print(f"  - {MODEL_REVISION_FILE.name}")
    print()
    print("After the lock commit, run with `run` to execute the calibration analysis.")


# --- Run: verify locks, infer, compute calibration -------------------------

def run():
    print("=" * 72)
    print("Toxic-BERT Calibration - RUN MODE")
    print("Pre-registration: PRE_REGISTRATION_TOXIC_BERT_v1.md")
    print("=" * 72)
    print()

    # Step 1: verify locked artifacts
    print("Step 1/4: Verifying locked artifacts...")
    missing = [p for p in (DATA_CSV, DATA_HASH, MODEL_REVISION_FILE) if not p.exists()]
    if missing:
        print("ERROR: required setup artifacts missing:")
        for p in missing:
            print(f"  - {p}")
        print()
        print("Run `python toxic_bert_calibration.py setup` first.")
        sys.exit(1)

    locked_hash = DATA_HASH.read_text().strip().lower()
    actual_hash = file_sha256(DATA_CSV).lower()
    if locked_hash != actual_hash:
        print("ERROR: data hash mismatch.")
        print(f"  Locked: {locked_hash}")
        print(f"  Actual: {actual_hash}")
        print()
        print("The materialized data has been modified since lock. Refusing to run.")
        sys.exit(1)
    revision = MODEL_REVISION_FILE.read_text().strip()
    print(f"  Data hash matches: {locked_hash[:32]}...")
    print(f"  Pinned model revision: {revision}")
    print()

    # Refuse to overwrite outputs
    for p in (PREDICTIONS_CSV, CALIB_SCORES_CSV, CALIB_SUMMARY_JSON):
        if p.exists():
            print(f"ERROR: output {p.name} already exists.")
            print("Refusing to overwrite. The score vector is locked once recorded.")
            sys.exit(1)

    # Step 2: load test data
    print("Step 2/4: Loading Civil Comments subsample...")
    examples = []
    with open(DATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            examples.append({
                "idx": int(row["idx"]),
                "text": row["text"],
                "toxicity_score": float(row["toxicity_score"]),
                "label": int(row["label"]),
            })
    print(f"  Loaded {len(examples)} examples.")
    print()

    # Step 3: run inference
    print("Step 3/4: Running unitary/toxic-bert inference at pinned revision...")
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
    except ImportError as e:
        print(f"ERROR: required library not installed: {e}")
        print("Install with: pip install transformers torch")
        sys.exit(1)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, revision=revision)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, revision=revision
    )
    model.eval()

    predictions = []
    t_start = time.time()
    with torch.no_grad():
        for i, ex in enumerate(examples):
            inputs = tokenizer(
                ex["text"],
                return_tensors="pt",
                truncation=True,
                max_length=MAX_TOKEN_LENGTH,
            )
            logits = model(**inputs).logits[0]  # shape: (6,) - 6 toxicity heads
            # Multi-label sigmoid output (not 2-class softmax) per pre-reg 4.2
            probs = torch.sigmoid(logits)
            prob_toxic = float(probs[TOXIC_LABEL_INDEX].item())
            predicted_class = 1 if prob_toxic >= 0.5 else 0
            predictions.append({
                "idx": ex["idx"],
                "label": ex["label"],
                "toxicity_score": ex["toxicity_score"],
                "predicted_prob_toxic": prob_toxic,
                "predicted_class": predicted_class,
            })
            if (i + 1) % 250 == 0 or (i + 1) == len(examples):
                elapsed = time.time() - t_start
                rate = (i + 1) / max(elapsed, 1e-9)
                eta = (len(examples) - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1:>5}/{len(examples)}]  {rate:.1f} ex/s  ETA {eta:.0f}s")

    # Save per-example predictions
    with open(PREDICTIONS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["idx", "label", "toxicity_score",
                           "predicted_prob_toxic", "predicted_class"]
        )
        writer.writeheader()
        for r in predictions:
            r2 = {
                "idx": r["idx"],
                "label": r["label"],
                "toxicity_score": f"{r['toxicity_score']:.6f}",
                "predicted_prob_toxic": f"{r['predicted_prob_toxic']:.{PROB_DECIMALS}f}",
                "predicted_class": r["predicted_class"],
            }
            writer.writerow(r2)
    print(f"  Wrote {PREDICTIONS_CSV.name} ({len(predictions)} rows)")
    print()

    # Step 4: compute calibration
    print("Step 4/4: Computing calibration metrics and applying decision criteria...")

    preds = np.array([p["predicted_prob_toxic"] for p in predictions], dtype=float)
    labels = np.array([p["label"] for p in predictions], dtype=int)
    classes = np.array([p["predicted_class"] for p in predictions], dtype=int)

    base_rate = float(labels.mean())
    accuracy = float((classes == labels).mean())

    # Reliability bins
    bins_edges = np.linspace(0.0, 1.0, K_BINS + 1)
    bin_data = []
    for k in range(K_BINS):
        lo, hi = bins_edges[k], bins_edges[k + 1]
        if k < K_BINS - 1:
            mask = (preds >= lo) & (preds < hi)
        else:
            mask = (preds >= lo) & (preds <= hi)  # last bin is closed at 1.0
        n = int(mask.sum())
        if n == 0:
            bin_data.append({
                "bin_index": k,
                "bin_lo": float(lo), "bin_hi": float(hi),
                "n": 0,
                "mean_pred": None, "observed_freq": None,
                "wilson_lo": None, "wilson_hi": None,
                "passes": None, "excluded": True,
            })
            continue
        mean_pred = float(preds[mask].mean())
        positives = int(labels[mask].sum())
        observed_freq = positives / n
        w_lo, w_hi = wilson_ci(positives, n)
        excluded = n < MIN_BIN_N
        # Pass criterion: bin's mean predicted probability lies within the
        # Wilson 95% CI of the observed toxic-class frequency (Section 2.2).
        passes = (w_lo <= mean_pred <= w_hi) if not excluded else None
        bin_data.append({
            "bin_index": k,
            "bin_lo": float(lo), "bin_hi": float(hi),
            "n": n,
            "mean_pred": mean_pred, "observed_freq": observed_freq,
            "wilson_lo": float(w_lo), "wilson_hi": float(w_hi),
            "passes": passes, "excluded": excluded,
        })

    # Aggregate metrics
    brier = float(np.mean((preds - labels) ** 2))
    brier_climatology = float(np.mean((base_rate - labels) ** 2))
    bss = (1.0 - (brier / brier_climatology)) if brier_climatology > 0 else 0.0

    valid_bins = [b for b in bin_data if not b["excluded"] and b["n"] > 0]
    n_total = sum(b["n"] for b in valid_bins)
    if n_total > 0:
        ece = sum((b["n"] / n_total) * abs(b["mean_pred"] - b["observed_freq"])
                  for b in valid_bins)
        mce = max(abs(b["mean_pred"] - b["observed_freq"]) for b in valid_bins)
    else:
        ece = float("nan")
        mce = float("nan")

    # Pass count and decision (Section 6.1)
    included = [b for b in bin_data if not b["excluded"]]
    excluded_count = K_BINS - len(included)
    pass_count = sum(1 for b in included if b["passes"])

    if len(included) > 0:
        strong_thr = int(math.ceil(STRONG_FRAC * len(included)))
        acceptable_thr = int(math.ceil(ACCEPTABLE_FRAC * len(included)))
        drift_thr = int(math.ceil(DRIFT_FRAC * len(included)))
    else:
        strong_thr = acceptable_thr = drift_thr = 0

    if pass_count >= strong_thr and bss > 0:
        outcome = "Calibrated (strong)"
    elif pass_count >= acceptable_thr and bss > 0:
        outcome = "Calibrated (acceptable)"
    elif pass_count >= drift_thr:
        outcome = "Calibration drift detected"
    else:
        outcome = "Not calibrated"

    # Mean absolute logit (sanity check 7.4)
    logit_mean_abs = None  # only meaningful if we kept logits; recomputable
                          # from probs as -log((1-p)/p) but adds noise; skip.

    # Write per-bin CSV
    with open(CALIB_SCORES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "bin_index", "bin_lo", "bin_hi", "n",
            "mean_pred", "observed_freq",
            "wilson_lo", "wilson_hi",
            "passes", "excluded",
        ])
        for b in bin_data:
            writer.writerow([
                b["bin_index"], f"{b['bin_lo']:.2f}", f"{b['bin_hi']:.2f}",
                b["n"],
                "" if b["mean_pred"] is None else f"{b['mean_pred']:.6f}",
                "" if b["observed_freq"] is None else f"{b['observed_freq']:.6f}",
                "" if b["wilson_lo"] is None else f"{b['wilson_lo']:.6f}",
                "" if b["wilson_hi"] is None else f"{b['wilson_hi']:.6f}",
                "" if b["passes"] is None else b["passes"],
                b["excluded"],
            ])
    print(f"  Wrote {CALIB_SCORES_CSV.name} ({K_BINS} rows)")

    # Write summary JSON
    summary = {
        "model_name": MODEL_NAME,
        "model_revision": revision,
        "data_csv": DATA_CSV.name,
        "data_sha256": locked_hash,
        "subsample_seed": SUBSAMPLE_SEED,
        "subsample_size": SUBSAMPLE_SIZE,
        "n_examples": len(predictions),
        "base_rate": base_rate,
        "accuracy_aux": accuracy,
        "K_bins": K_BINS,
        "min_bin_n": MIN_BIN_N,
        "excluded_bins": excluded_count,
        "included_bins": len(included),
        "pass_count": pass_count,
        "strong_threshold": strong_thr,
        "acceptable_threshold": acceptable_thr,
        "drift_threshold": drift_thr,
        "brier": brier,
        "brier_climatology": brier_climatology,
        "bss": bss,
        "ece": ece,
        "mce": mce,
        "outcome": outcome,
        "bins": bin_data,
    }
    with open(CALIB_SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Wrote {CALIB_SUMMARY_JSON.name}")
    print()

    # On-screen summary
    print("=" * 72)
    print("CALIBRATION OUTCOME")
    print("=" * 72)
    print()
    print(f"  Outcome: {outcome}")
    print(f"  Pass count: {pass_count} of {len(included)} included bins "
          f"({excluded_count} excluded for n < {MIN_BIN_N})")
    print(f"  Thresholds: strong={strong_thr}, acceptable={acceptable_thr}, "
          f"drift={drift_thr}")
    print()
    print("  Aggregate metrics:")
    print(f"    Base rate (toxic):  {base_rate:.4f}")
    print(f"    Accuracy (aux):     {accuracy:.4f}")
    print(f"    Brier:              {brier:.4f}")
    print(f"    Brier climat.:      {brier_climatology:.4f}")
    print(f"    BSS:                {bss:+.4f}")
    print(f"    ECE:                {ece:.4f}")
    print(f"    MCE:                {mce:.4f}")
    print()
    print("Per-bin reliability:")
    print(f"  {'bin':>4}  {'range':<13}  {'n':>5}  {'mean_pred':>10}  "
          f"{'observed':>10}  {'Wilson_lo':>10}  {'Wilson_hi':>10}  pass")
    for b in bin_data:
        rng = f"[{b['bin_lo']:.2f},{b['bin_hi']:.2f})"
        if b["excluded"] or b["n"] == 0:
            note = f"(n={b['n']}, excluded)"
            print(f"  {b['bin_index']:>4}  {rng:<13}  {b['n']:>5}  {note}")
        else:
            mark = "PASS" if b["passes"] else "fail"
            print(f"  {b['bin_index']:>4}  {rng:<13}  {b['n']:>5}  "
                  f"{b['mean_pred']:>10.4f}  {b['observed_freq']:>10.4f}  "
                  f"{b['wilson_lo']:>10.4f}  {b['wilson_hi']:>10.4f}  {mark}")
    print()
    print("CRITICAL NEXT STEPS:")
    print()
    print("  1. Commit the outputs BEFORE drafting the result document:")
    print(f"        git add case_studies/toxic_bert/{PREDICTIONS_CSV.name}")
    print(f"        git add case_studies/toxic_bert/{CALIB_SCORES_CSV.name}")
    print(f"        git add case_studies/toxic_bert/{CALIB_SUMMARY_JSON.name}")
    print('        git commit -m "Toxic-BERT v1: lock calibration outputs"')
    print()
    print("  2. Draft RESULT_TOXIC_BERT_v1_<date>.md from calibration_summary.json.")


# --- Entry point -----------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("setup",
                   help="Materialize Civil Comments subsample, pin model revision, compute hashes.")
    sub.add_parser("run",
                   help="Verify locks, run inference, compute calibration.")
    args = parser.parse_args()
    if args.mode == "setup":
        setup()
    elif args.mode == "run":
        run()


if __name__ == "__main__":
    main()