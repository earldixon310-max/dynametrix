#!/usr/bin/env python3
"""filter_derived_input.py - DETECTOR_PERTURBATION_OVP, materialization step 0 (no-peeking barrier).

Builds the DERIVED input the materialization reads, containing ONLY (id, text, predicted_prob_ai).
The materialization script never sees y_correct/is_ai_generated/pred/B_confidence because the file
it reads does not contain them (pre-reg sec 8.1(a)). This is the structural half of no-peeking; the
source-level ban on y/label references (sec 8.1(b)) is the other half, checkable by grep.

Deterministic + pure (sorted by id, fixed column order, no index): re-running produces identical
bytes, so the derived-input sha256 is stable and pinned in the manifest.

Reads ONLY:
  - the inherited calibration per-example  -> (id, predicted_prob_ai)   [explicitly NOT the label cols]
  - the RAID test-set CSV                  -> (id, text)                [explicitly NOT is_ai_generated]
"""
import csv
import hashlib
import os
import sys

INHERITED_PER_EXAMPLE = os.path.join("..", "detector_truncation_ovp", "detector_per_example.csv")
EXPECTED_INHERITED_SHA256 = "24dac07828949a7e93fcc686ff3df70229c026195d3db873e688c1b401afc643"
RAID_TEXT_CSV = os.path.join("..", "..", "case_studies", "chatgpt_detector_roberta_v1",
                             "chatgpt_detector_roberta_test_set.csv")
OUT = "detector_perturbation_input.csv"
ALLOWED_OUT_COLUMNS = ["id", "text", "predicted_prob_ai"]   # the ONLY columns that may exist downstream


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    actual = sha256_file(INHERITED_PER_EXAMPLE)
    if actual != EXPECTED_INHERITED_SHA256:
        sys.exit("ABORT: inherited per-example sha256 %s != pinned %s." % (actual, EXPECTED_INHERITED_SHA256))

    # inherited: select ONLY id + predicted_prob_ai (label columns are never read into memory)
    prob_by_id = {}
    with open(INHERITED_PER_EXAMPLE, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            prob_by_id[row["id"]] = row["predicted_prob_ai"]
    need = set(prob_by_id)

    # RAID: select ONLY id + text for the inherited id set (is_ai_generated is never read)
    text_by_id = {}
    with open(RAID_TEXT_CSV, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            if row["id"] in need:
                text_by_id[row["id"]] = row["text"]

    missing = need - set(text_by_id)
    if missing:
        sys.exit("ABORT: %d inherited ids not found in the RAID text CSV (e.g. %s)."
                 % (len(missing), next(iter(missing))))

    rows = [{"id": i, "text": text_by_id[i], "predicted_prob_ai": prob_by_id[i]} for i in sorted(need)]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALLOWED_OUT_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    out_sha = sha256_file(OUT)
    sys.stderr.write("[derive] wrote %s  rows=%d  columns=%s\n" % (OUT, len(rows), ALLOWED_OUT_COLUMNS))
    sys.stderr.write("[derive] derived-input sha256 = %s  (pin in the manifest)\n" % out_sha)


if __name__ == "__main__":
    main()
