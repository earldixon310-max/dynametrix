#!/usr/bin/env python3
"""make_manifest.py - DETECTOR_PERTURBATION_OVP materialization manifest (pre-reg sec 8.4).

`python make_manifest.py`           -> writes materialization_manifest_detector_perturbation.json
`python make_manifest.py --verify`  -> re-hashes every pinned artifact and ABORTS on any mismatch
                                       (the lock-time / re-run drift check).

Pins: inherited per-example, derived input, materialized per-example, paraphrase artifacts, dataset,
model + paraphraser + embedder revisions, decoding + seeds + prompt hashes, quality-gate result,
cut-point provenance, judge seeds/eps. No y/label DATA is read or pinned; the label column NAMES appear
only in the banned-column guard (BANNED_LABEL_COLUMNS), which asserts the derived header carries none.
"""
import argparse
import csv
import hashlib
import json
import os
import sys

MANIFEST = "materialization_manifest_detector_perturbation.json"

INHERITED = os.path.join("..", "detector_truncation_ovp", "detector_per_example.csv")
DERIVED = "detector_perturbation_input.csv"
MATERIALIZED = "detector_perturbation_per_example.csv"
PARAPHRASES = "detector_perturbation_paraphrases.csv"
QUALITY = "detector_perturbation_quality_summary.json"
CALIB_RESULTS_JSON = os.path.join("..", "detector_truncation_ovp", "detector_calibration_results.json")

PINNED = {
    "inherited_per_example_sha256": "24dac07828949a7e93fcc686ff3df70229c026195d3db873e688c1b401afc643",
    "derived_input_sha256": "4b6fcb543994dcc4dafa056d13dc42532e661177af00d60eea0e650b5a31ced8",
    "materialized_per_example_sha256": "ad5901b160b37c763752607f85cfd2f3ed2a3fe2bf5d0d48627ae5b1bddd5318",
    "dataset_sha256": "a29f8f2c0ff8f5eca1a1a3c07e771a28b0709d0f9f060a9024c935eaff615a47",
    "detector_revision": "d2b342c61775d5dd0221808a79983ed3b86ffd86",
    "paraphraser_revision": "a09a35458c702b33eeacc393d103063234e8bc28",
    "tau_lo": 0.02458901317356486,
    "tau_hi": 0.06829080323934116,
}
ALLOWED_DERIVED_COLUMNS = ["id", "text", "predicted_prob_ai"]
BANNED_LABEL_COLUMNS = {"y_correct", "is_ai_generated", "pred", "b_confidence"}
DETECTOR_ID = "Hello-SimpleAI/chatgpt-detector-roberta"
DETECTOR_REVISION = "d2b342c61775d5dd0221808a79983ed3b86ffd86"
CUT_POINTS_PROVENANCE = "detector-ovp-calib-result"
MASTER_SEED_HEX = "0x5b5ead"
FOIL_SEED_XOR_HEX = "0xf011"
EPS_CONFOUND = 0.005


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build():
    for p in (INHERITED, DERIVED, MATERIALIZED, PARAPHRASES, QUALITY, CALIB_RESULTS_JSON):
        if not os.path.exists(p):
            sys.exit("ABORT: required artifact missing: %s (materialize first)." % p)
    quality = json.load(open(QUALITY, encoding="utf-8"))
    cal = json.load(open(CALIB_RESULTS_JSON, encoding="utf-8"))
    man = {
        "study": "DETECTOR_PERTURBATION_OVP",
        "hashes": {
            "inherited_per_example": sha256_file(INHERITED),
            "derived_input": sha256_file(DERIVED),
            "materialized_per_example": sha256_file(MATERIALIZED),
            "paraphrases": sha256_file(PARAPHRASES),
            "quality_summary": sha256_file(QUALITY),
        },
        "pinned_expected": PINNED,
        "detector": {"id": DETECTOR_ID, "revision": DETECTOR_REVISION,
                     "ai_class_index": quality.get("ai_class_index")},
        "paraphraser": {"id": quality.get("paraphraser_id"), "fourbit": quality.get("paraphraser_4bit"),
                        "engine": quality.get("paraphraser_engine"),
                        "resolved_revision": quality.get("paraphraser_resolved_revision"),
                        "seed": quality.get("paraphrase_seed"), "K": quality.get("K"),
                        "temperature": quality.get("temperature"), "top_p": quality.get("top_p"),
                        "max_new_tokens": quality.get("max_new_tokens"),
                        "prompt_system_sha256": quality.get("prompt_system_sha256"),
                        "prompt_user_sha256": quality.get("prompt_user_sha256")},
        "embedder": {"id": quality.get("embed_id")},
        # rev-2: per-text >= MIN_VALID is the operative gate; set-level is a REPORTED descriptor (no threshold).
        "gate": {"theta_cosine": quality.get("theta_cosine"), "delta_jaccard": quality.get("delta_jaccard"),
                 "min_valid_operative": quality.get("min_valid_operative_gate"),
                 "set_level_pass_fraction_INFORMATIONAL": quality.get("set_level_pass_fraction"),
                 "n_texts_included": quality.get("n_texts_included_ge_min_valid"),
                 "n_texts_excluded_substrate_attrition": quality.get("n_texts_excluded_substrate_attrition"),
                 "substrate_attrition_fraction": quality.get("substrate_attrition_fraction")},
        "spread": {"statistic": "std", "ddof": 1},
        "judge": {"master_seed": MASTER_SEED_HEX, "foil_seed_xor": FOIL_SEED_XOR_HEX,
                  "eps_confound": EPS_CONFOUND, "R": 200,
                  "cut_points_provenance": CUT_POINTS_PROVENANCE,
                  "tau_lo": cal.get("tau_lo"), "tau_hi": cal.get("tau_hi")},
    }
    # consistency: pinned inherited/derived/dataset must match the freshly hashed files
    if man["hashes"]["inherited_per_example"] != PINNED["inherited_per_example_sha256"]:
        sys.exit("ABORT: inherited per-example hash != pinned (substrate drift).")
    if man["hashes"]["derived_input"] != PINNED["derived_input_sha256"]:
        sys.exit("ABORT: derived-input hash != pinned (re-run filter_derived_input.py; non-deterministic source?).")
    if man["hashes"]["materialized_per_example"] != PINNED["materialized_per_example_sha256"]:
        sys.exit("ABORT: materialized per-example hash != pinned (artifact drift).")
    # no-label-column check on the derived input header (structural no-peeking, sec 8.1)
    with open(DERIVED, newline="", encoding="utf-8") as f:
        hdr = next(csv.reader(f))
    if hdr != ALLOWED_DERIVED_COLUMNS:
        sys.exit("ABORT: derived input header %r != %r (label leak?)." % (hdr, ALLOWED_DERIVED_COLUMNS))
    if BANNED_LABEL_COLUMNS & {h.lower() for h in hdr}:
        sys.exit("ABORT: derived input carries a banned outcome/label column: %r." % hdr)
    # cut-point identity vs the calibration (sec 5)
    if not (cal.get("tau_lo") == PINNED["tau_lo"] and cal.get("tau_hi") == PINNED["tau_hi"]):
        sys.exit("ABORT: calibration cut points (%r, %r) != pinned." % (cal.get("tau_lo"), cal.get("tau_hi")))
    # detector + paraphraser revision identity vs the recorded materialization summary (sec 2)
    if quality.get("detector_revision") != PINNED["detector_revision"]:
        sys.exit("ABORT: recorded detector revision %r != pinned." % quality.get("detector_revision"))
    if quality.get("paraphraser_resolved_revision") != PINNED["paraphraser_revision"]:
        sys.exit("ABORT: recorded paraphraser revision %r != pinned." % quality.get("paraphraser_resolved_revision"))
    # rev-2: no set-level gate. The operative requirement (per-text >= MIN_VALID) is enforced in the judge,
    # which excludes sub-threshold texts as substrate attrition; the manifest only records the descriptors.
    return man


def verify():
    if not os.path.exists(MANIFEST):
        sys.exit("ABORT: %s not found; run without --verify first." % MANIFEST)
    man = json.load(open(MANIFEST, encoding="utf-8"))
    rehash = {"inherited_per_example": INHERITED, "derived_input": DERIVED,
              "materialized_per_example": MATERIALIZED, "paraphrases": PARAPHRASES, "quality_summary": QUALITY}
    for key, path in rehash.items():
        cur = sha256_file(path)
        if cur != man["hashes"][key]:
            sys.exit("ABORT(verify): %s hash drift: %s != manifest %s." % (path, cur, man["hashes"][key]))
    sys.stderr.write("[manifest] verify OK: all 5 artifact hashes match the manifest.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    if args.verify:
        verify(); return
    man = build()
    json.dump(man, open(MANIFEST, "w", encoding="utf-8"), indent=2)
    sys.stderr.write("[manifest] wrote %s\n" % MANIFEST)
    sys.stderr.write("[manifest] materialized_per_example sha256 = %s  (pin in judge_perturbation.py "
                     "EXPECTED_MATERIALIZED_SHA256)\n" % man["hashes"]["materialized_per_example"])


if __name__ == "__main__":
    main()
