#!/usr/bin/env python3
"""
build_manifest_detector_predclass.py - materialization manifest generator for
DETECTOR_PREDCLASS_OVP (OVP real candidate #4). Run at LOCK time.

Aborts the lock on: inherited per-example-hash mismatch; dataset-hash mismatch; 3-way
model-revision identity mismatch; or cut-point-identity mismatch (script TAU vs frozen
calibration result). Writes materialization_manifest_detector_predclass.json.

Everything (B, y, pred) is inherited; NO new materialization.
"""
import hashlib
import json
import os
import platform
import re
import sys
from datetime import datetime, timezone

ARTIFACTS = ["PRE_REGISTRATION_DETECTOR_PREDCLASS_OVP.md", "judge_predclass.py"]
MASTER_SEED = "0xC1A55D"
JUDGE_SCRIPT = "judge_predclass.py"

INHERITED_PER_EXAMPLE = os.path.join("..", "detector_truncation_ovp", "detector_per_example.csv")
EXPECTED_PER_EXAMPLE_SHA256 = "24dac07828949a7e93fcc686ff3df70229c026195d3db873e688c1b401afc643"
CALIB_RESULTS_JSON = os.path.join("..", "detector_truncation_ovp", "detector_calibration_results.json")

AUDIT_DIR = os.path.join("..", "..", "case_studies", "chatgpt_detector_roberta_v1")
DATA_CSV = os.path.join(AUDIT_DIR, "chatgpt_detector_roberta_test_set.csv")
DATA_HASH_FILE = os.path.join(AUDIT_DIR, "chatgpt_detector_roberta_test_set_sha256.txt")
MODEL_REVISION_FILE = os.path.join(AUDIT_DIR, "model_revision.txt")
MODEL_ID = "Hello-SimpleAI/chatgpt-detector-roberta"
MODEL_REVISION = "d2b342c61775d5dd0221808a79983ed3b86ffd86"

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
    pe = sha256(INHERITED_PER_EXAMPLE)
    if pe != EXPECTED_PER_EXAMPLE_SHA256:
        raise SystemExit("ABORT: inherited %s sha %s != pinned %s; do not lock." % (INHERITED_PER_EXAMPLE, pe, EXPECTED_PER_EXAMPLE_SHA256))
    data_sha = sha256(DATA_CSV)
    rec = open(DATA_HASH_FILE).read().strip().split()[0] if os.path.exists(DATA_HASH_FILE) else None
    if rec is not None and rec != data_sha:
        raise SystemExit("ABORT: dataset sha %s != audit record %s; do not lock." % (data_sha, rec))
    audit_rev = open(MODEL_REVISION_FILE).read().strip()
    src = open(JUDGE_SCRIPT).read()
    m = re.search(r'MODEL_REVISION\s*=\s*"([0-9a-f]{40})"', src)
    script_rev = m.group(1) if m else None
    if not (audit_rev == MODEL_REVISION == script_rev):
        raise SystemExit("ABORT: model revision mismatch - audit=%s, manifest=%s, script=%s; do not lock."
                         % (audit_rev, MODEL_REVISION, script_rev))
    mlo = re.search(r'TAU_LO\s*=\s*([0-9.]+)', src)
    mhi = re.search(r'TAU_HI\s*=\s*([0-9.]+)', src)
    if not (mlo and mhi and float(mlo.group(1)) == TAU_LO and float(mhi.group(1)) == TAU_HI):
        raise SystemExit("ABORT: cut-point mismatch between manifest and judge_predclass.py; do not lock.")
    cal = json.load(open(CALIB_RESULTS_JSON))
    if not (cal.get("tau_lo") == TAU_LO and cal.get("tau_hi") == TAU_HI):
        raise SystemExit("ABORT: manifest cut points != calibration result %s; do not lock." % CALIB_RESULTS_JSON)

    manifest = {
        "framework": "AEPF DETECTOR_PREDCLASS_OVP materialization manifest",
        "study": "DETECTOR_PREDCLASS_OVP real candidate study (#4): does pred add HDG beyond folded confidence (first under the Descriptor Justification Layer)",
        "governing_spec": "OVP v0.1 @ signed tag ovp-v0.1-lock",
        "lock_tag": "detector-predclass-ovp-lock",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "master_seed": MASTER_SEED, "foil_seed_xor": "0xF011",
        "candidate": "pred", "baseline": "confidence (folded max(p,1-p))",
        "descriptor_justification_layer": "v0.2 seed; first prospective use (mechanism disclosure + dual interpretation lock + permuted-pred surface foil)",
        "inherited_cut_points": {"tau_lo": TAU_LO, "tau_hi": TAU_HI, "provenance": CUT_POINT_PROVENANCE,
                                 "identity_checked_at_lock": True},
        "substrate": {
            "type": "ALL of B,y,pred inherited from the calibration lock; NO new materialization; external model+dataset pinned for provenance",
            "inherited_per_example": {"path": INHERITED_PER_EXAMPLE.replace(os.sep, "/"), "sha256": pe,
                                      "source": "DETECTOR_OVP_CALIB locked materialization (detector-ovp-calib-result)"},
            "dataset": {"path": DATA_CSV.replace(os.sep, "/"), "sha256": data_sha,
                        "matches_audit_record": (rec == data_sha) if rec is not None else None},
            "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "identity_checked_at_lock": True},
            "attestation": ("B,y,pred are inherited byte-identical from the calibration-locked per-example "
                            "(hash-verified). No tokenizer, no model inference, no new materialization. pred's HDG "
                            "(and the permuted-pred foil's) are computed only by the single locked run."),
        },
        "environment": {
            "python": sys.version.split()[0], "platform": platform.platform(),
            "numpy": version("numpy"), "scikit_learn": version("sklearn"),
        },
        "artifacts": [{"path": p, "sha256": sha256(p)} for p in ARTIFACTS],
        "note": ("The pre-registration SHA-256 is the authoritative record of all pinned parameters incl. the "
                 "permuted-pred foil construction. transformers/torch NOT required (no materialization)."),
    }
    with open("materialization_manifest_detector_predclass.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
