#!/usr/bin/env python3
"""
build_manifest_detector_truncation.py - materialization manifest generator for the
DETECTOR_TRUNCATION_OVP candidate study (lock 2). Run at LOCK time.

Captures: SHA-256 of the locked artifacts (pre-reg + judge_truncation.py); the INHERITED
substrate provenance (calibration-locked detector_per_example.csv hash; dataset hash; model
revision); the inherited cut points + their provenance tag; the environment; the seed.

Aborts the lock on: inherited per-example-hash mismatch; dataset-hash mismatch; or a 3-way
model-revision identity mismatch (audit model_revision.txt == manifest pin == script).
Writes materialization_manifest_detector_truncation.json for the single atomic lock commit.
"""
import hashlib
import json
import os
import platform
import re
import sys
from datetime import datetime, timezone

ARTIFACTS = ["PRE_REGISTRATION_DETECTOR_TRUNCATION_OVP.md", "judge_truncation.py"]
MASTER_SEED = "0x77C0DE"
JUDGE_SCRIPT = "judge_truncation.py"

# Inherited per-example (from the calibration lock, in this directory)
PER_EXAMPLE_CSV = "detector_per_example.csv"
PER_EXAMPLE_HASH_FILE = "detector_per_example_sha256.txt"
EXPECTED_PER_EXAMPLE_SHA256 = "24dac07828949a7e93fcc686ff3df70229c026195d3db873e688c1b401afc643"

# External substrate provenance
AUDIT_DIR = os.path.join("..", "..", "case_studies", "chatgpt_detector_roberta_v1")
DATA_CSV = os.path.join(AUDIT_DIR, "chatgpt_detector_roberta_test_set.csv")
DATA_HASH_FILE = os.path.join(AUDIT_DIR, "chatgpt_detector_roberta_test_set_sha256.txt")
MODEL_REVISION_FILE = os.path.join(AUDIT_DIR, "model_revision.txt")
MODEL_ID = "Hello-SimpleAI/chatgpt-detector-roberta"
MODEL_REVISION = "d2b342c61775d5dd0221808a79983ed3b86ffd86"

# Inherited cut points (verbatim) + provenance
TAU_LO = 0.02458901317356486
TAU_HI = 0.06829080323934116
CUT_POINT_PROVENANCE = "detector-ovp-calib-result"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def version(mod):
    try:
        return getattr(__import__(mod), "__version__", "unknown")
    except Exception as e:
        return "NOT-IMPORTABLE (" + e.__class__.__name__ + ")"


def main():
    # 1. Inherited per-example hash
    pe = sha256(PER_EXAMPLE_CSV)
    if pe != EXPECTED_PER_EXAMPLE_SHA256:
        raise SystemExit("ABORT: %s sha256 %s != pinned %s; inherited substrate is not the "
                         "calibration-locked one; do not lock." % (PER_EXAMPLE_CSV, pe, EXPECTED_PER_EXAMPLE_SHA256))
    # 2. External dataset hash
    data_sha = sha256(DATA_CSV)
    rec = open(DATA_HASH_FILE).read().strip().split()[0] if os.path.exists(DATA_HASH_FILE) else None
    if rec is not None and rec != data_sha:
        raise SystemExit("ABORT: dataset sha %s != audit record %s; do not lock." % (data_sha, rec))
    # 3. 3-way model-revision identity
    audit_rev = open(MODEL_REVISION_FILE).read().strip()
    m = re.search(r'MODEL_REVISION\s*=\s*"([0-9a-f]{40})"', open(JUDGE_SCRIPT).read())
    script_rev = m.group(1) if m else None
    if not (audit_rev == MODEL_REVISION == script_rev):
        raise SystemExit("ABORT: model revision mismatch - audit=%s, manifest=%s, script=%s; do not lock."
                         % (audit_rev, MODEL_REVISION, script_rev))
    # 4. cut-point identity vs the locked judge script (guard against transcription drift)
    mlo = re.search(r'TAU_LO\s*=\s*([0-9.]+)', open(JUDGE_SCRIPT).read())
    mhi = re.search(r'TAU_HI\s*=\s*([0-9.]+)', open(JUDGE_SCRIPT).read())
    if not (mlo and mhi and float(mlo.group(1)) == TAU_LO and float(mhi.group(1)) == TAU_HI):
        raise SystemExit("ABORT: cut-point mismatch between manifest and judge_truncation.py; do not lock.")

    manifest = {
        "framework": "AEPF DETECTOR_TRUNCATION_OVP materialization manifest",
        "study": "DETECTOR_TRUNCATION_OVP real candidate study (lock 2): does `truncated` add HDG beyond confidence",
        "governing_spec": "OVP v0.1 @ signed tag ovp-v0.1-lock",
        "lock_tag": "detector-truncation-ovp-lock",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "master_seed": MASTER_SEED,
        "candidate": "truncated", "baseline": "confidence (max softmax)",
        "inherited_cut_points": {"tau_lo": TAU_LO, "tau_hi": TAU_HI,
                                 "provenance": CUT_POINT_PROVENANCE,
                                 "identity_checked_at_lock": True},
        "substrate": {
            "type": "inherited per-example (B, y, truncated) from the calibration lock; external model+dataset pinned",
            "inherited_per_example": {"path": PER_EXAMPLE_CSV, "sha256": pe,
                                      "source": "DETECTOR_OVP_CALIB locked materialization (detector-ovp-calib-result)"},
            "dataset": {"path": DATA_CSV.replace(os.sep, "/"), "sha256": data_sha,
                        "matches_audit_record": (rec == data_sha) if rec is not None else None},
            "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "identity_checked_at_lock": True},
            "attestation": ("No model re-run: (B, y, truncated) are inherited byte-identical from the "
                            "calibration-locked detector_per_example.csv (hash-verified). truncated's HDG is "
                            "computed only by the single locked run of judge_truncation.py."),
        },
        "environment": {
            "python": sys.version.split()[0], "platform": platform.platform(),
            "numpy": version("numpy"), "scikit_learn": version("sklearn"),
        },
        "artifacts": [{"path": p, "sha256": sha256(p)} for p in ARTIFACTS],
        "note": ("The pre-registration SHA-256 is the authoritative record of all pinned parameters "
                 "(estimator, D=median form, verdict rule, inherited cut points). transformers/torch are "
                 "NOT required at lock-2 runtime (no model re-run); numpy + scikit-learn govern the verdict."),
    }
    with open("materialization_manifest_detector_truncation.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
