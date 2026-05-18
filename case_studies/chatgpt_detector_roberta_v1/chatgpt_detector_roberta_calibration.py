"""
chatgpt_detector_roberta_calibration.py

Implements the pre-registration at PRE_REGISTRATION_CHATGPT_DETECTOR_ROBERTA_v1.md.

The script implements, mechanically and without judgment calls, the methodology
specified in the pre-registration. Each non-trivial choice in the code is
traceable to a specific clause of the pre-reg.

Modes:
    setup    Materialize the RAID subsample, compute its SHA-256, query model
             and dataset revisions, resolve the AI-class index from the model's
             id2label mapping, and print all TBD values for the pre-registration.
             The detector is NOT run on the data during setup.

    run      Verify all locked artifacts match their committed hashes/revisions.
             Run inference on the subsample. Compute reliability bins, Wilson
             CIs, Brier skill score, and apply the §5 decision criteria.
             Write predictions.csv, calibration_scores.csv, and
             calibration_summary.json. Print the outcome.

Pre-registration: PRE_REGISTRATION_CHATGPT_DETECTOR_ROBERTA_v1.md (locked at
commit TBD).
"""

import argparse
import hashlib
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

# ============================================================================
# CONFIGURATION (LOCKED BY PRE-REGISTRATION)
# ============================================================================

MODEL_NAME = "Hello-SimpleAI/chatgpt-detector-roberta"
RAID_DATASET_NAME = "liamdugan/raid"

TARGET_TOTAL = 2000
TARGET_PER_CLASS = 1000
SEED = 150914
MIN_CHAR_LENGTH = 100

MAX_TOKEN_LENGTH = 512

N_BINS = 10
BIN_MIN_SAMPLES = 30

N_FLOOR = 5
STRONG_FRACTION = 0.9
ACCEPTABLE_FRACTION = 0.8
DRIFT_FLOOR_FRACTION = 0.6

CLIMATOLOGY_BASE_RATE = 0.5

AI_CLASS_TOKENS = {
    "ai", "ai-generated", "chatgpt", "gpt", "machine", "generated",
    "llm", "synthetic", "fake", "model", "bot",
}
HUMAN_CLASS_TOKENS = {
    "human", "real", "natural", "original",
}


# ============================================================================
# UTILITIES
# ============================================================================

def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson_interval(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def assign_to_bin(p):
    if p < 0.0 or p > 1.0:
        raise ValueError(f"probability out of range: {p}")
    if p >= 0.9:
        return 9
    return min(int(p * 10), 9)


def resolve_ai_class_index(id2label):
    if len(id2label) != 2:
        raise ValueError(
            f"Detector has {len(id2label)} output classes; expected 2 "
            f"(binary human-vs-AI). id2label = {id2label}"
        )

    label_tokens = {}
    for idx, lbl in id2label.items():
        tokens = set()
        s = str(lbl).lower().replace("-", " ").replace("_", " ")
        for tok in s.split():
            tokens.add(tok)
        label_tokens[int(idx)] = tokens

    classifications = {}
    for idx, tokens in label_tokens.items():
        is_ai = bool(tokens & AI_CLASS_TOKENS)
        is_human = bool(tokens & HUMAN_CLASS_TOKENS)
        if is_ai and is_human:
            raise ValueError(
                f"Label for class {idx} ({id2label[idx]!r}) matches both "
                f"AI and human token lists; cannot resolve unambiguously."
            )
        if not is_ai and not is_human:
            classifications[idx] = "unknown"
        elif is_ai:
            classifications[idx] = "ai"
        else:
            classifications[idx] = "human"

    ai_indices = [i for i, c in classifications.items() if c == "ai"]
    human_indices = [i for i, c in classifications.items() if c == "human"]

    if len(ai_indices) == 1 and len(human_indices) == 1:
        note = (
            f"Resolved unambiguously: class {ai_indices[0]} "
            f"({id2label[ai_indices[0]]!r}) is AI-generated; "
            f"class {human_indices[0]} ({id2label[human_indices[0]]!r}) is human."
        )
        return ai_indices[0], human_indices[0], note

    if len(ai_indices) == 1 and len(human_indices) == 0:
        other = [i for i in id2label if i != ai_indices[0]][0]
        note = (
            f"Resolved: class {ai_indices[0]} ({id2label[ai_indices[0]]!r}) "
            f"matches AI tokens; class {other} ({id2label[other]!r}) does not "
            f"match human tokens but is the only remaining class. "
            f"Accepting class {other} as human."
        )
        return ai_indices[0], other, note

    if len(human_indices) == 1 and len(ai_indices) == 0:
        other = [i for i in id2label if i != human_indices[0]][0]
        note = (
            f"Resolved: class {human_indices[0]} ({id2label[human_indices[0]]!r}) "
            f"matches human tokens; class {other} ({id2label[other]!r}) does not "
            f"match AI tokens but is the only remaining class. "
            f"Accepting class {other} as AI-generated."
        )
        return other, human_indices[0], note

    raise ValueError(
        f"id2label = {id2label} is ambiguous: cannot determine which class is "
        f"AI-generated. Add explicit labels to AI_CLASS_TOKENS or "
        f"HUMAN_CLASS_TOKENS, or re-examine the model card to determine the "
        f"correct mapping, then add the resolution to the pre-registration."
    )


# ============================================================================
# MODE: SETUP
# ============================================================================

def cmd_setup(args):
    print("=" * 72)
    print("CHATGPT-DETECTOR-ROBERTA CALIBRATION — SETUP MODE")
    print("=" * 72)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\nStep 1/5: Querying model metadata from HuggingFace Hub...")
    print(f"  Model: {MODEL_NAME}")

    from huggingface_hub import HfApi
    api = HfApi()
    model_info = api.model_info(MODEL_NAME)
    model_revision = model_info.sha
    print(f"  Pinned revision: {model_revision}")

    from transformers import AutoConfig
    config = AutoConfig.from_pretrained(MODEL_NAME, revision=model_revision)
    id2label = {int(k): str(v) for k, v in config.id2label.items()}
    print(f"  id2label: {id2label}")

    try:
        ai_idx, human_idx, resolution_note = resolve_ai_class_index(id2label)
    except ValueError as e:
        print(f"\nERROR resolving AI class index: {e}")
        sys.exit(1)

    print(f"  Resolved ai_class_index = {ai_idx}")
    print(f"  Resolved human_class_index = {human_idx}")
    print(f"  Resolution: {resolution_note}")

    print("\nStep 2/5: Querying RAID dataset revision from HuggingFace Hub...")
    try:
        dataset_info = api.dataset_info(RAID_DATASET_NAME)
        raid_revision = dataset_info.sha
        print(f"  Dataset: {RAID_DATASET_NAME}")
        print(f"  Pinned revision: {raid_revision}")
    except Exception as e:
        print(f"\nERROR querying RAID dataset: {e}")
        print(f"  Verify the dataset exists at: https://huggingface.co/datasets/{RAID_DATASET_NAME}")
        sys.exit(1)

    print("\nStep 3/5: Loading RAID dataset...")
    print("  (This may take several minutes on first download.)")

    from datasets import load_dataset
    try:
        raid = load_dataset(
            RAID_DATASET_NAME,
            revision=raid_revision,
            split="train",
            trust_remote_code=False,
        )
    except Exception as e:
        print(f"\n  Standard split-load failed: {e}")
        print("  Attempting fallback: load_dataset without split argument")
        raid_all = load_dataset(
            RAID_DATASET_NAME,
            revision=raid_revision,
            trust_remote_code=False,
        )
        first_split = list(raid_all.keys())[0]
        raid = raid_all[first_split]
        print(f"  Loaded split: {first_split}")

    print(f"  Loaded {len(raid)} rows")
    print(f"  Columns: {raid.column_names}")

    print("\nStep 4/5: Filtering to non-adversarial split + length filter...")

    cols = set(raid.column_names)

    if "generation" in cols:
        text_col = "generation"
    elif "text" in cols:
        text_col = "text"
    else:
        print(f"  ERROR: cannot find a text column in RAID schema. "
              f"Looked for 'generation' or 'text'. Found: {sorted(cols)}")
        sys.exit(1)

    if "model" in cols:
        model_col = "model"
    elif "source_model" in cols:
        model_col = "source_model"
    else:
        print(f"  ERROR: cannot find a model column in RAID schema. "
              f"Looked for 'model' or 'source_model'. Found: {sorted(cols)}")
        sys.exit(1)

    if "domain" in cols:
        domain_col = "domain"
    else:
        print(f"  ERROR: cannot find a domain column. Found: {sorted(cols)}")
        sys.exit(1)

    if "attack" in cols:
        adv_col = "attack"
        def is_non_adversarial(row):
            v = row[adv_col]
            return v is None or v == "" or str(v).lower() in ("none", "null", "no_attack")
    elif "adversarial" in cols:
        adv_col = "adversarial"
        def is_non_adversarial(row):
            return not bool(row[adv_col])
    else:
        print(f"  WARNING: no 'attack' or 'adversarial' column found. "
              f"Assuming entire dataset is non-adversarial. Verify this manually. "
              f"Columns: {sorted(cols)}")
        adv_col = None
        def is_non_adversarial(row):
            return True

    print(f"  Schema resolution:")
    print(f"    text_col   = {text_col}")
    print(f"    model_col  = {model_col}")
    print(f"    domain_col = {domain_col}")
    print(f"    adv_col    = {adv_col}")

    print("\n  Iterating dataset to filter (this can take a moment for large RAID)...")
    rows = []
    for i, row in enumerate(raid):
        if not is_non_adversarial(row):
            continue
        text = row[text_col]
        if text is None:
            continue
        if len(text) < MIN_CHAR_LENGTH:
            continue
        rows.append({
            "raid_index": i,
            "text": text,
            "model": str(row[model_col]).lower() if row[model_col] is not None else "",
            "domain": str(row[domain_col]) if row[domain_col] is not None else "",
        })

    print(f"  After filter: {len(rows)} rows remain")
    if len(rows) < TARGET_TOTAL * 2:
        print(f"  WARNING: only {len(rows)} rows survived filtering; "
              f"may not have enough for a {TARGET_TOTAL}-example subsample.")

    human_rows = [r for r in rows if r["model"] == "human"]
    ai_rows = [r for r in rows if r["model"] != "human"]
    print(f"  Human rows: {len(human_rows)}")
    print(f"  AI rows:    {len(ai_rows)}")

    if len(human_rows) < TARGET_PER_CLASS:
        print(f"  ERROR: insufficient human rows ({len(human_rows)} < {TARGET_PER_CLASS})")
        sys.exit(1)
    if len(ai_rows) < TARGET_PER_CLASS:
        print(f"  ERROR: insufficient AI rows ({len(ai_rows)} < {TARGET_PER_CLASS})")
        sys.exit(1)

    rng = random.Random(SEED)

    def stratified_sample(pool, n_target, key_fn):
        buckets = defaultdict(list)
        for r in pool:
            buckets[key_fn(r)].append(r)

        keys = sorted(buckets.keys())
        n_keys = len(keys)
        per_key = n_target // n_keys

        for k in keys:
            rng.shuffle(buckets[k])

        selected = []
        leftover = []
        for k in keys:
            take = min(per_key, len(buckets[k]))
            selected.extend(buckets[k][:take])
            leftover.extend(buckets[k][take:])

        rng.shuffle(leftover)
        deficit = n_target - len(selected)
        if deficit > 0:
            selected.extend(leftover[:deficit])

        if len(selected) > n_target:
            rng.shuffle(selected)
            selected = selected[:n_target]

        return selected

    print("\n  Stratifying human side by domain...")
    human_sample = stratified_sample(
        human_rows, TARGET_PER_CLASS, lambda r: r["domain"]
    )
    human_domain_breakdown = defaultdict(int)
    for r in human_sample:
        human_domain_breakdown[r["domain"]] += 1
    print(f"    Human sample: {len(human_sample)}")
    print(f"    Domain breakdown: {dict(human_domain_breakdown)}")

    print("\n  Stratifying AI side by (model, domain)...")
    ai_sample = stratified_sample(
        ai_rows, TARGET_PER_CLASS, lambda r: (r["model"], r["domain"])
    )
    ai_model_breakdown = defaultdict(int)
    ai_domain_breakdown = defaultdict(int)
    for r in ai_sample:
        ai_model_breakdown[r["model"]] += 1
        ai_domain_breakdown[r["domain"]] += 1
    print(f"    AI sample: {len(ai_sample)}")
    print(f"    AI model breakdown: {dict(ai_model_breakdown)}")
    print(f"    AI domain breakdown: {dict(ai_domain_breakdown)}")

    subsample = []
    for r in human_sample:
        subsample.append({
            "id": f"H{len(subsample):05d}",
            "text": r["text"],
            "is_ai_generated": 0,
            "source_domain": r["domain"],
            "source_model": "",
        })
    for r in ai_sample:
        subsample.append({
            "id": f"A{len(subsample):05d}",
            "text": r["text"],
            "is_ai_generated": 1,
            "source_domain": r["domain"],
            "source_model": r["model"],
        })

    rng.shuffle(subsample)

    df = pd.DataFrame(subsample)
    csv_path = out_dir / "chatgpt_detector_roberta_test_set.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n  Wrote {csv_path} ({len(df)} rows)")

    print("\nStep 5/5: Computing hashes and writing provenance files...")
    data_sha = sha256_of_file(csv_path)
    (out_dir / "chatgpt_detector_roberta_test_set_sha256.txt").write_text(data_sha + "\n")
    (out_dir / "model_revision.txt").write_text(model_revision + "\n")
    (out_dir / "raid_revision.txt").write_text(raid_revision + "\n")
    (out_dir / "ai_class_index.txt").write_text(str(ai_idx) + "\n")
    (out_dir / "id2label.json").write_text(json.dumps(id2label, indent=2) + "\n")

    print("\n" + "=" * 72)
    print("SETUP COMPLETE")
    print("=" * 72)
    print(f"  Test set rows:        {len(df)}")
    print(f"  Test set SHA-256:     {data_sha}")
    print(f"  Model revision:       {model_revision}")
    print(f"  RAID revision:        {raid_revision}")
    print(f"  ai_class_index:       {ai_idx}")
    print(f"  id2label:             {id2label}")
    print()
    print("FILL THESE VALUES INTO PRE_REGISTRATION_CHATGPT_DETECTOR_ROBERTA_v1.md §9:")
    print(f"  Pinned model revision:        {model_revision}")
    print(f"  Pinned RAID dataset revision: {raid_revision}")
    print(f"  Resolved ai_class_index:      {ai_idx}")
    print(f"  Test data SHA-256:            {data_sha}")


# ============================================================================
# MODE: RUN
# ============================================================================

def cmd_run(args):
    print("=" * 72)
    print("CHATGPT-DETECTOR-ROBERTA CALIBRATION — RUN MODE")
    print("=" * 72)

    out_dir = Path(args.output_dir)
    csv_path = out_dir / "chatgpt_detector_roberta_test_set.csv"
    sha_path = out_dir / "chatgpt_detector_roberta_test_set_sha256.txt"
    model_rev_path = out_dir / "model_revision.txt"
    raid_rev_path = out_dir / "raid_revision.txt"
    ai_idx_path = out_dir / "ai_class_index.txt"

    print("\nStep 1/4: Verifying locked artifacts...")
    for p in (csv_path, sha_path, model_rev_path, raid_rev_path, ai_idx_path):
        if not p.exists():
            print(f"  ERROR: {p} not found. Run 'setup' first.")
            sys.exit(1)

    locked_sha = sha_path.read_text().strip()
    actual_sha = sha256_of_file(csv_path)
    if actual_sha != locked_sha:
        print(f"  ERROR: test data SHA mismatch.")
        print(f"    Expected: {locked_sha}")
        print(f"    Actual:   {actual_sha}")
        sys.exit(1)
    print(f"  Test data SHA verified: {locked_sha[:16]}...")

    locked_model_rev = model_rev_path.read_text().strip()
    locked_raid_rev = raid_rev_path.read_text().strip()
    locked_ai_idx = int(ai_idx_path.read_text().strip())
    print(f"  Pinned model revision:        {locked_model_rev}")
    print(f"  Pinned RAID revision:         {locked_raid_rev}")
    print(f"  Pinned ai_class_index:        {locked_ai_idx}")

    print("\nStep 2/4: Re-verifying model revision and id2label...")
    from huggingface_hub import HfApi
    from transformers import AutoConfig, AutoTokenizer, AutoModelForSequenceClassification

    api = HfApi()
    current_model_rev = api.model_info(MODEL_NAME).sha
    if current_model_rev != locked_model_rev:
        print(f"  NOTE: current HF Hub revision ({current_model_rev}) differs from "
              f"locked ({locked_model_rev}). Will load locked revision explicitly.")

    config = AutoConfig.from_pretrained(MODEL_NAME, revision=locked_model_rev)
    id2label = {int(k): str(v) for k, v in config.id2label.items()}
    ai_idx, human_idx, _ = resolve_ai_class_index(id2label)
    if ai_idx != locked_ai_idx:
        print(f"  ERROR: re-resolved ai_class_index ({ai_idx}) does not match "
              f"locked value ({locked_ai_idx}). Refuse to proceed.")
        sys.exit(1)
    print(f"  id2label and ai_class_index verified.")

    print("\nStep 3/4: Loading model and running inference...")
    print(f"  Loading {MODEL_NAME} at revision {locked_model_rev}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, revision=locked_model_rev)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, revision=locked_model_rev
    )
    model.eval()

    import torch

    df = pd.read_csv(csv_path)
    n = len(df)
    print(f"  Test set: {n} examples")

    predictions = []
    import time
    t0 = time.time()
    with torch.no_grad():
        for i, row in df.iterrows():
            text = str(row["text"])
            enc = tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=MAX_TOKEN_LENGTH,
                padding=False,
            )
            full_enc = tokenizer(text, truncation=False, padding=False)
            truncated = len(full_enc["input_ids"]) > MAX_TOKEN_LENGTH

            logits = model(**enc).logits[0]
            probs = torch.softmax(logits, dim=-1)
            p_ai = float(probs[locked_ai_idx])

            predictions.append({
                "id": row["id"],
                "is_ai_generated": int(row["is_ai_generated"]),
                "source_domain": row["source_domain"],
                "source_model": row.get("source_model", ""),
                "predicted_prob_ai": p_ai,
                "truncated": int(truncated),
            })

            if (i + 1) % 50 == 0 or (i + 1) == n:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed
                eta = (n - i - 1) / rate if rate > 0 else 0
                print(f"    [{i+1:4d}/{n}] {rate:.1f} ex/s  ETA {eta:.0f}s")

    pred_df = pd.DataFrame(predictions)
    pred_path = out_dir / "predictions.csv"
    pred_df.to_csv(pred_path, index=False)
    print(f"\n  Wrote {pred_path}")
    truncated_frac = float(pred_df["truncated"].mean())
    print(f"  Truncated fraction: {truncated_frac:.3f}")

    print("\nStep 4/4: Computing calibration metrics and applying §5 decision criteria...")

    probs = pred_df["predicted_prob_ai"].values
    y = pred_df["is_ai_generated"].values.astype(int)

    base_rate = float(y.mean())

    brier = float(np.mean((probs - y) ** 2))
    brier_clim = float(np.mean((CLIMATOLOGY_BASE_RATE - y) ** 2))
    bss = float(1.0 - brier / brier_clim) if brier_clim > 0 else float("nan")

    predicted_class = (probs >= 0.5).astype(int)
    accuracy = float(np.mean(predicted_class == y))

    bins_info = []
    bin_assign = np.array([assign_to_bin(p) for p in probs])

    passed = 0
    included = 0
    weighted_abs_err = 0.0
    max_abs_err = 0.0

    for i in range(N_BINS):
        m = bin_assign == i
        n_bin = int(m.sum())
        if i < 9:
            lo_edge = i * 0.1
            hi_edge = (i + 1) * 0.1
            range_str = f"[{lo_edge:.2f},{hi_edge:.2f})"
        else:
            range_str = "[0.90,1.00]"

        info = {"bin": i, "range": range_str, "n": n_bin}

        if n_bin == 0:
            info["excluded"] = True
            info["reason"] = "empty"
            bins_info.append(info)
            continue

        mp = float(probs[m].mean())
        k = int(y[m].sum())
        of = float(k / n_bin)
        abs_err = abs(mp - of)
        weighted_abs_err += (n_bin / len(probs)) * abs_err

        if n_bin < BIN_MIN_SAMPLES:
            info["excluded"] = True
            info["reason"] = f"n < {BIN_MIN_SAMPLES}"
            info["mean_pred"] = mp
            info["observed_freq"] = of
            bins_info.append(info)
            continue

        included += 1
        lo, hi = wilson_interval(k, n_bin)
        passes = bool(lo <= mp <= hi)
        if passes:
            passed += 1
        if abs_err > max_abs_err:
            max_abs_err = abs_err

        info.update({
            "mean_pred": mp,
            "observed_freq": of,
            "wilson_lo": float(lo),
            "wilson_hi": float(hi),
            "passes": passes,
        })
        bins_info.append(info)

    ece = float(weighted_abs_err)
    mce = float(max_abs_err)

    if included < N_FLOOR:
        outcome = "INSUFFICIENT BIN COVERAGE"
        outcome_note = (
            f"Only {included} of {N_BINS} bins have n >= {BIN_MIN_SAMPLES}; "
            f"the §5.1 floor is {N_FLOOR}. No calibration verdict recorded."
        )
    else:
        strong_thresh = math.ceil(STRONG_FRACTION * included)
        accept_thresh = math.ceil(ACCEPTABLE_FRACTION * included)
        drift_thresh = math.ceil(DRIFT_FLOOR_FRACTION * included)

        if bss <= 0:
            outcome = "NOT CALIBRATED"
            outcome_note = (
                f"BSS = {bss:+.4f} <= 0 against 0.5-base-rate climatology. "
                f"Per §5.2, BSS <= 0 produces NOT CALIBRATED regardless of "
                f"bin pass count (K = {passed} of N = {included})."
            )
        elif passed >= strong_thresh:
            outcome = "CALIBRATED (strong)"
            outcome_note = (
                f"K = {passed} of N = {included} bins pass; "
                f"strong threshold ceil({STRONG_FRACTION} * {included}) = {strong_thresh}. "
                f"BSS = {bss:+.4f} > 0."
            )
        elif passed >= accept_thresh:
            outcome = "CALIBRATED (acceptable)"
            outcome_note = (
                f"K = {passed} of N = {included} bins pass; "
                f"acceptable threshold ceil({ACCEPTABLE_FRACTION} * {included}) = {accept_thresh}. "
                f"BSS = {bss:+.4f} > 0."
            )
        elif passed >= drift_thresh:
            outcome = "CALIBRATION DRIFT DETECTED"
            outcome_note = (
                f"K = {passed} of N = {included} bins pass; "
                f"drift floor ceil({DRIFT_FLOOR_FRACTION} * {included}) = {drift_thresh}. "
                f"BSS = {bss:+.4f} > 0."
            )
        else:
            outcome = "NOT CALIBRATED"
            outcome_note = (
                f"K = {passed} of N = {included} bins pass; below drift floor "
                f"ceil({DRIFT_FLOOR_FRACTION} * {included}) = {drift_thresh}."
            )

    summary = {
        "model_name": MODEL_NAME,
        "model_revision": locked_model_rev,
        "raid_revision": locked_raid_rev,
        "ai_class_index": locked_ai_idx,
        "id2label": id2label,
        "n_examples": int(n),
        "base_rate": base_rate,
        "climatology_base_rate": CLIMATOLOGY_BASE_RATE,
        "truncated_fraction": truncated_frac,
        "accuracy_at_0.5": accuracy,
        "brier": brier,
        "brier_climatology": brier_clim,
        "bss": bss,
        "ece": ece,
        "mce": mce,
        "n_bins_total": N_BINS,
        "n_bins_included": included,
        "n_bins_passed": passed,
        "outcome": outcome,
        "outcome_note": outcome_note,
        "bins": bins_info,
    }

    summary_path = out_dir / "calibration_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")

    bins_csv_path = out_dir / "calibration_scores.csv"
    bins_df = pd.DataFrame(bins_info)
    bins_df.to_csv(bins_csv_path, index=False)

    print(f"  Wrote {summary_path}")
    print(f"  Wrote {bins_csv_path}")

    print("\n" + "=" * 72)
    print("CALIBRATION OUTCOME")
    print("=" * 72)
    print(f"  Outcome:           {outcome}")
    print(f"  Note:              {outcome_note}")
    print()
    print(f"  Aggregate metrics:")
    print(f"    Base rate:       {base_rate:.4f}")
    print(f"    Accuracy (aux):  {accuracy:.4f}")
    print(f"    Brier:           {brier:.4f}")
    print(f"    Brier climat.:   {brier_clim:.4f}")
    print(f"    BSS:             {bss:+.4f}")
    print(f"    ECE:             {ece:.4f}")
    print(f"    MCE:             {mce:.4f}")
    print(f"    Truncated frac:  {truncated_frac:.3f}")
    print()
    print(f"  Bin coverage: {included} of {N_BINS} bins included (n >= {BIN_MIN_SAMPLES})")
    print(f"  Bins passing Wilson criterion: {passed} of {included}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    p = argparse.ArgumentParser(
        description="Calibration audit of Hello-SimpleAI/chatgpt-detector-roberta on RAID."
    )
    p.add_argument("--output-dir", default=".", help="Output directory (default: current)")
    sub = p.add_subparsers(dest="mode")
    sub.add_parser("setup", help="Pull RAID subsample, compute hashes, resolve ai_class_index")
    sub.add_parser("run", help="Verify locks, run inference, compute calibration metrics")
    args = p.parse_args()

    if args.mode == "setup":
        cmd_setup(args)
    elif args.mode == "run":
        cmd_run(args)
    else:
        p.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()