#!/usr/bin/env python3
"""materialize_perturbation.py - DETECTOR_PERTURBATION_OVP candidate materialization (GPU).

Runs on a CUDA machine (RTX 5080, 16 GB). Reads ONLY the derived input
`detector_perturbation_input.csv` (id, text, predicted_prob_ai) - so it CANNOT see y_correct /
is_ai_generated (pre-reg sec 8.1(a)). It never READS the outcome/ground-truth columns y_correct /
is_ai_generated as data (sec 8.1(b)); `id2label` and the prompt word "labels" are the detector's
output-class metadata / prompt text, not the OVP target.

REVISION 3 (2026-06-19): paraphraser is the UNIQUELY PINNED Qwen2.5-7B-Instruct 4-bit (bitsandbytes nf4)
@ revision a09a35458c702b33eeacc393d103063234e8bc28 - single path, NO fallback (bitsandbytes required,
revision-checked; cold-pass #1 (b) fix). temperature 0.5 + fidelity-first prompt (spend the Jaccard
headroom on cosine fidelity). GATE REDEFINED: the operative gate is per-text >= MIN_VALID valid
paraphrases (the judge excludes texts below it as substrate attrition). The set-level pass rate is
REPORTED ONLY (no threshold, no gating) - so it can never trigger a bar-recalibration loop.

For each text: K paraphrases -> re-run the LOCKED detector on each -> MiniLM cosine + token-Jaccard
quality gate -> spread (std, ddof=1, over {original prob + valid paraphrase probs}), flip_rate, text_length.
"""
import argparse
import csv
import hashlib
import json
import os
import sys

import numpy as np
import torch
from transformers import (AutoTokenizer, AutoModelForSequenceClassification, AutoModelForCausalLM)
from sentence_transformers import SentenceTransformer, util

# --- PINNED constants (pre-reg sec 2/11) --------------------------------------------------------
DERIVED_INPUT = "detector_perturbation_input.csv"
EXPECTED_DERIVED_SHA256 = "4b6fcb543994dcc4dafa056d13dc42532e661177af00d60eea0e650b5a31ced8"
OUT_PER_EXAMPLE = "detector_perturbation_per_example.csv"
OUT_PARAPHRASES = "detector_perturbation_paraphrases.csv"
OUT_QUALITY = "detector_perturbation_quality_summary.json"

DETECTOR_ID = "Hello-SimpleAI/chatgpt-detector-roberta"
DETECTOR_REVISION = "d2b342c61775d5dd0221808a79983ed3b86ffd86"
# UNIQUELY PINNED materialization path (cold-pass #1 (b) fix: no auto-detect / no 3B fallback). The
# rev-2 run that produced the committed artifact used exactly this path; it is now the single pinned
# procedure. GPU sampling is not bit-reproducible, so the COMMITTED artifact (sha in the manifest) is
# the authoritative scientific object; this pin documents provenance and fails closed on divergence.
import bitsandbytes as _bnb  # noqa: F401  --  HARD requirement; ImportError aborts (no silent fallback)
PARAPHRASER_ID = "Qwen/Qwen2.5-7B-Instruct"
PARAPHRASER_4BIT = True
PARAPHRASER_REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"
EMBED_ID = "sentence-transformers/all-MiniLM-L6-v2"

PARAPHRASE_SEED = 20260618
K = 5
TEMPERATURE = 0.5     # revision-2: lowered from 0.7 to reduce semantic drift (cosine fidelity)
TOP_P = 0.95
THETA = 0.80          # min embedding cosine to the original
DELTA = 0.30          # min token-Jaccard distance from the original
MIN_VALID = 3         # per text, of K -> the OPERATIVE gate (judge excludes texts below this)
DETECTOR_MAXLEN = 512
PARAPHRASER_MAX_INPUT = 1024
MAX_NEW_TOKENS = 640

# Pinned VERBATIM (its sha256 is recorded in the manifest); {text} is the only substitution.
PARAPHRASE_SYSTEM = "You are a careful paraphraser."
PARAPHRASE_USER = (
    "Rewrite the text below in different words while preserving its meaning exactly. Change the "
    "vocabulary and sentence structure, but do not alter, add, or omit any information, and keep the "
    "same facts, tone, and intent. Output only the rewritten text, with no preamble, labels, or "
    "quotation marks.\n\nText:\n{text}"
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def token_jaccard_distance(a, b):
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa and not sb:
        return 0.0
    union = len(sa | sb)
    return 1.0 - (len(sa & sb) / union if union else 1.0)


def resolve_ai_index(config):
    id2label = {int(k): v for k, v in config.id2label.items()}
    for idx, lab in id2label.items():
        if any(t in lab.lower() for t in ("chatgpt", "ai", "machine", "fake", "generated")):
            return idx, id2label
    raise SystemExit("ABORT: cannot unambiguously resolve the AI-generated class from id2label=%r" % id2label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    actual = sha256_file(DERIVED_INPUT)
    if actual != EXPECTED_DERIVED_SHA256:
        sys.exit("ABORT: %s sha256 %s != pinned %s (re-run filter_derived_input.py)." % (DERIVED_INPUT, actual, EXPECTED_DERIVED_SHA256))

    ids, texts, orig_probs = [], [], []
    with open(DERIVED_INPUT, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ids.append(row["id"]); texts.append(row["text"]); orig_probs.append(float(row["predicted_prob_ai"]))
    n = len(ids)
    sys.stderr.write("[mat] %d texts from the derived input (id, text, predicted_prob_ai only)\n" % n)

    # --- models ---
    det_tok = AutoTokenizer.from_pretrained(DETECTOR_ID, revision=DETECTOR_REVISION)
    det = AutoModelForSequenceClassification.from_pretrained(DETECTOR_ID, revision=DETECTOR_REVISION).to(args.device).eval()
    ai_idx, id2label = resolve_ai_index(det.config)
    embedder = SentenceTransformer(EMBED_ID, device=args.device)
    qtok = AutoTokenizer.from_pretrained(PARAPHRASER_ID, revision=PARAPHRASER_REVISION)
    if qtok.pad_token_id is None:
        qtok.pad_token = qtok.eos_token
    from transformers import BitsAndBytesConfig
    bnb_cfg = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                 bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    qmodel = AutoModelForCausalLM.from_pretrained(
        PARAPHRASER_ID, revision=PARAPHRASER_REVISION, quantization_config=bnb_cfg, device_map={"": args.device}).eval()
    _resolved = getattr(qmodel.config, "_commit_hash", None)
    if _resolved and _resolved != PARAPHRASER_REVISION:
        sys.exit("ABORT: resolved paraphraser revision %s != pinned %s." % (_resolved, PARAPHRASER_REVISION))
    sys.stderr.write("[mat] paraphraser = %s (bnb-nf4-4bit @ %s), temp=%.2f\n" % (PARAPHRASER_ID, PARAPHRASER_REVISION, TEMPERATURE))

    def detector_prob(t):
        enc = det_tok(t, return_tensors="pt", truncation=True, max_length=DETECTOR_MAXLEN).to(args.device)
        with torch.no_grad():
            return float(torch.softmax(det(**enc).logits, dim=-1)[0, ai_idx].cpu())

    def paraphrase(text):
        prompt = qtok.apply_chat_template(
            [{"role": "system", "content": PARAPHRASE_SYSTEM},
             {"role": "user", "content": PARAPHRASE_USER.format(text=text)}],
            tokenize=False, add_generation_prompt=True)
        enc = qtok(prompt, return_tensors="pt", truncation=True, max_length=PARAPHRASER_MAX_INPUT).to(args.device)
        torch.manual_seed(PARAPHRASE_SEED)
        with torch.no_grad():
            out = qmodel.generate(**enc, do_sample=True, temperature=TEMPERATURE, top_p=TOP_P,
                                  num_return_sequences=K, max_new_tokens=MAX_NEW_TOKENS, pad_token_id=qtok.pad_token_id)
        gen = out[:, enc["input_ids"].shape[1]:]
        return [qtok.decode(g, skip_special_tokens=True).strip() for g in gen]

    per_rows, para_rows = [], []
    total_paras = 0; total_valid = 0; n_flagged = 0
    for i in range(n):
        paras = paraphrase(texts[i])[:K]
        orig_emb = embedder.encode(texts[i], convert_to_tensor=True, normalize_embeddings=True)
        orig_pred = 1 if orig_probs[i] >= 0.5 else 0
        valid_probs, valid_preds, cosines, jaccs = [], [], [], []
        for j, p in enumerate(paras):
            total_paras += 1
            cos = float(util.cos_sim(orig_emb, embedder.encode(p, convert_to_tensor=True, normalize_embeddings=True))[0, 0])
            jd = token_jaccard_distance(texts[i], p)
            prob = detector_prob(p)
            valid = (cos >= THETA) and (jd >= DELTA)
            if valid:
                total_valid += 1
                valid_probs.append(prob); valid_preds.append(1 if prob >= 0.5 else 0)
                cosines.append(cos); jaccs.append(jd)
            para_rows.append({"id": ids[i], "para_index": j, "paraphrase": p,
                              "para_prob_ai": prob, "cosine": cos, "jaccard_dist": jd, "valid": int(valid)})
        n_valid = len(valid_probs)
        if n_valid < MIN_VALID:
            n_flagged += 1
        spread_vals = np.array([orig_probs[i]] + valid_probs, float)
        spread = float(np.std(spread_vals, ddof=1)) if len(spread_vals) >= 2 else float("nan")
        flip = float(np.mean([pp != orig_pred for pp in valid_preds])) if valid_preds else float("nan")
        per_rows.append({"id": ids[i], "perturbation_spread": spread, "flip_rate": flip,
                         "text_length": len(texts[i]), "n_valid": n_valid,
                         "mean_cosine": float(np.mean(cosines)) if cosines else float("nan"),
                         "mean_jaccard_dist": float(np.mean(jaccs)) if jaccs else float("nan")})
        if (i + 1) % 100 == 0:
            sys.stderr.write("[mat] %d/%d  set-level(info)=%.4f  texts<%d-valid so far=%d\n"
                             % (i + 1, n, total_valid / max(total_paras, 1), MIN_VALID, n_flagged))

    with open(OUT_PER_EXAMPLE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "perturbation_spread", "flip_rate", "text_length",
                                          "n_valid", "mean_cosine", "mean_jaccard_dist"])
        w.writeheader(); [w.writerow(r) for r in per_rows]
    with open(OUT_PARAPHRASES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "para_index", "paraphrase", "para_prob_ai", "cosine", "jaccard_dist", "valid"])
        w.writeheader(); [w.writerow(r) for r in para_rows]

    set_pass = total_valid / total_paras if total_paras else 0.0
    summary = {"n_texts": n, "K": K, "total_paraphrases": total_paras, "total_valid": total_valid,
               "set_level_pass_fraction": set_pass, "set_level_is_informational": True,   # NO gating
               "min_valid_operative_gate": MIN_VALID,
               "n_texts_included_ge_min_valid": int(n - n_flagged),
               "n_texts_excluded_substrate_attrition": n_flagged,
               "substrate_attrition_fraction": float(n_flagged / n),
               "theta_cosine": THETA, "delta_jaccard": DELTA,
               "detector_id": DETECTOR_ID, "detector_revision": DETECTOR_REVISION, "ai_class_index": ai_idx,
               "paraphraser_id": PARAPHRASER_ID, "paraphraser_4bit": PARAPHRASER_4BIT, "paraphraser_engine": "transformers",
               "paraphraser_resolved_revision": getattr(qmodel.config, "_commit_hash", PARAPHRASER_REVISION),
               "embed_id": EMBED_ID, "paraphrase_seed": PARAPHRASE_SEED,
               "temperature": TEMPERATURE, "top_p": TOP_P, "max_new_tokens": MAX_NEW_TOKENS,
               "paraphraser_max_input": PARAPHRASER_MAX_INPUT,
               "prompt_system_sha256": hashlib.sha256(PARAPHRASE_SYSTEM.encode()).hexdigest(),
               "prompt_user_sha256": hashlib.sha256(PARAPHRASE_USER.encode()).hexdigest()}
    json.dump(summary, open(OUT_QUALITY, "w", encoding="utf-8"), indent=2)

    sys.stderr.write("[mat] wrote %s (sha %s)\n" % (OUT_PER_EXAMPLE, sha256_file(OUT_PER_EXAMPLE)))
    sys.stderr.write("[mat] set-level pass=%.4f (INFORMATIONAL, no threshold) | operative per-text gate: "
                     "%d/%d texts have >=%d valid; %d excluded as substrate attrition (%.1f%%)\n"
                     % (set_pass, n - n_flagged, n, MIN_VALID, n_flagged, 100.0 * n_flagged / n))


if __name__ == "__main__":
    main()
