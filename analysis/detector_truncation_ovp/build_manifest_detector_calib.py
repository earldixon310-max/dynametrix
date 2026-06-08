#!/usr/bin/env python3
"""
build_manifest_detector_calib.py - materialization manifest generator for the
DETECTOR_OVP_CALIB cut-point calibration sub-study (lock 1 of the detector arc).

Run at LOCK time, on the machine that will execute the locked study, to capture:
  - SHA-256 of the locked artifacts (this study's pre-reg + calibrate_detector_cutpoints.py)
  - the EXTERNAL substrate provenance: the pinned RAID test subsample (path + SHA-256,
    cross-checked against the audit's recorded hash) and the pinned RoBERTa model id +
    revision (cross-checked 3 ways: audit model_revision.txt == manifest pin == script)
  - the execution environment (python, numpy, scikit-learn, transformers, torch)
  - the master seed (0xD37EC7)

Aborts the lock on a dataset-hash mismatch or a model-revision identity mismatch.

The per-example file `detector_per_example.csv` (B, y, truncated) is an OUTPUT of the
single locked run, hashed by the run, not a lock input. Writes
materialization_manifest_detector_calib.json, committed in the single atomic lock commit
alongside the pre-registration and calibrate_detector_cutpoints.py.
"""
import hashlib
import json
import os
import platform
import re
import sys
from datetime import datetime, timezone

ARTIFACTS = [
    "PRE_REGISTRATION_DETECTOR_OVP_CALIB.md",
    "calibrate_detector_cutpoints.py",
]
MASTER_SEED = "0xD37EC7"

AUDIT_DIR = os.path.join("..", "..", "case_studies", "chatgpt_detector_roberta_v1")
DATA_CSV = os.path.join(AUDIT_DIR, "chatgpt_detector_roberta_test_set.csv")
DATA_HASH_FILE = os.path.join(AUDIT_DIR, "chatgpt_detector_roberta_test_set_sha256.txt")
MODEL_REVISION_FILE = os.path.join(AUDIT_DIR, "model_revision.txt")
MODEL_ID = "Hello-SimpleAI/chatgpt-detector-roberta"
MODEL_REVISION = "d2b342c61775d5dd0221808a79983ed3b86ffd86"
CALIB_SCRIPT = "calibrate_detector_cutpoints.py"


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
    data_sha = sha256(DATA_CSV)
    recorded = open(DATA_HASH_FILE).read().strip().split()[0] if os.path.exists(DATA_HASH_FILE) else None
    if recorded is not None and recorded != data_sha:
        raise SystemExit(
            "ABORT: %s SHA-256 (%s) != audit record (%s); substrate not byte-identical "
            "to the pinned ChatGPT-detector audit data; do not lock." % (DATA_CSV, data_sha, recorded)
        )

    # 3-way model-revision identity: audit model_revision.txt == manifest pin == script constant.
    audit_rev = open(MODEL_REVISION_FILE).read().strip()
    m = re.search(r'MODEL_REVISION\s*=\s*"([0-9a-f]{40})"', open(CALIB_SCRIPT).read())
    script_rev = m.group(1) if m else None
    if not (audit_rev == MODEL_REVISION == script_rev):
        raise SystemExit(
            "ABORT: model revision mismatch - audit model_revision.txt=%s, manifest pin=%s, "
            "script MODEL_REVISION=%s. All three must be identical; do not lock."
            % (audit_rev, MODEL_REVISION, script_rev)
        )

    manifest = {
        "framework": "AEPF DETECTOR_OVP_CALIB materialization manifest",
        "study": "DETECTOR_OVP_CALIB cut-point calibration (lock 1 of the detector-truncation two-lock arc)",
        "governing_spec": "OVP v0.1 @ signed tag ovp-v0.1-lock",
        "lock_tag": "detector-ovp-calib-lock",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "master_seed": MASTER_SEED,
        "substrate": {
            "type": "external dataset + external model (real); empirically eligible (noise-null P95 > 0)",
            "dataset": {
                "path": DATA_CSV.replace(os.sep, "/"),
                "sha256": data_sha,
                "recorded_sha256": recorded,
                "matches_audit_record": (recorded == data_sha) if recorded is not None else None,
                "source": "ChatGPT-detector RoBERTa audit RAID subsample (case_studies/chatgpt_detector_roberta_v1)",
            },
            "model": {
                "id": MODEL_ID,
                "revision": MODEL_REVISION,
                "ai_class_index": 1,
                "max_length": 512,
                "identity_checked_at_lock": True,   # audit model_revision.txt == manifest == script, asserted above
                "source": "identical to the ChatGPT-detector audit (model_revision.txt)",
                "inference": "deterministic (no sampling); cross-checked against the audit predictions.csv at run time",
            },
            "attestation": (
                "B=max-softmax-confidence, y=correctness, and truncated (full-token-len>512) are "
                "materialized by running the pinned model (id+revision above) once over the pinned, "
                "hash-verified RAID test subsample, with a determinism cross-check against the audit "
                "predictions.csv. truncated is the lock-2 candidate (stored, not used in calibration). "
                "detector_per_example.csv is an output of the single locked run, hashed by the run."
            ),
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": version("numpy"),
            "scikit_learn": version("sklearn"),
            "transformers": version("transformers"),
            "torch": version("torch"),
        },
        "artifacts": [{"path": p, "sha256": sha256(p)} for p in ARTIFACTS],
        "note": (
            "The pre-registration SHA-256 above is the authoritative record of all pinned "
            "parameters (incl. the standardized estimator and the eps_null=delta check-3 tolerance); "
            "this manifest does not restate them. scikit-learn, transformers, and torch versions are "
            "recorded because the pinned estimator and model inference can vary numerically across versions."
        ),
    }
    with open("materialization_manifest_detector_calib.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
