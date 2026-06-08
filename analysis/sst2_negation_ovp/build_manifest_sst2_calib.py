#!/usr/bin/env python3
"""
build_manifest_sst2_calib.py - materialization manifest generator for the
SST2_OVP_CALIB cut-point calibration sub-study (lock 1 of the two-lock arc).

Run at LOCK time, on the machine that will execute the locked study, to capture:
  - SHA-256 of the locked artifacts (this study's pre-reg + calibrate_sst2_cutpoints.py)
  - the EXTERNAL substrate provenance: the pinned SST-2 validation CSV (path + SHA-256,
    cross-checked against the audit's sst2_validation_sha256.txt) and the pinned
    DistilBERT-SST2 model id + revision SHA (identical to the DistilBERT-SST2 audit)
  - the execution environment (python, numpy, scikit-learn, transformers, torch)
  - the master seed (0x55712)

Unlike the OVP_POSCONTROL_v1 manifests, this study consumes a real dataset and a
real model, so the manifest fingerprints them instead of carrying a synthetic-data
attestation. The per-example file `sst2_per_example.csv` is an OUTPUT of the single
locked run (produced from the pinned model), not a lock input; its hash is recorded
by the run, not here.

Writes materialization_manifest_sst2_calib.json, committed in the single atomic lock
commit alongside the pre-registration and calibrate_sst2_cutpoints.py.

Run on the authoritative machine after the pre-reg has cleared its two cold passes
and is final - it hashes the bytes as they stand on disk.
"""
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone

ARTIFACTS = [
    "PRE_REGISTRATION_SST2_OVP_CALIB.md",
    "calibrate_sst2_cutpoints.py",
]
MASTER_SEED = "0x55712"

# External substrate (pinned; identical to the DistilBERT-SST2 calibration audit)
DATA_CSV = os.path.join("..", "..", "case_studies", "distilbert_sst2", "sst2_validation.csv")
DATA_HASH_FILE = os.path.join("..", "..", "case_studies", "distilbert_sst2", "sst2_validation_sha256.txt")
MODEL_ID = "distilbert-base-uncased-finetuned-sst-2-english"
MODEL_REVISION = "714eb0fa89d2f80546fda750413ed43d93601a13"


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


MODEL_REVISION_FILE = os.path.join("..", "..", "case_studies", "distilbert_sst2", "model_revision.txt")


def main():
    data_sha = sha256(DATA_CSV)
    recorded = None
    if os.path.exists(DATA_HASH_FILE):
        recorded = open(DATA_HASH_FILE).read().strip().split()[0]
    data_match = (recorded == data_sha) if recorded is not None else None
    if data_match is False:
        raise SystemExit(
            "ABORT: sst2_validation.csv SHA-256 (%s) does not match the audit's "
            "recorded hash (%s). The substrate is not byte-identical to the pinned "
            "DistilBERT-SST2 audit data; do not lock." % (data_sha, recorded)
        )

    # Lock-time revision identity check: audit's model_revision.txt == this manifest's
    # pin == the locked script's MODEL_REVISION constant. Abort the lock on any mismatch.
    import re
    audit_rev = open(MODEL_REVISION_FILE).read().strip()
    script_src = open("calibrate_sst2_cutpoints.py").read()
    m = re.search(r'MODEL_REVISION\s*=\s*"([0-9a-f]{40})"', script_src)
    script_rev = m.group(1) if m else None
    if not (audit_rev == MODEL_REVISION == script_rev):
        raise SystemExit(
            "ABORT: model revision mismatch - audit model_revision.txt=%s, manifest "
            "pin=%s, script MODEL_REVISION=%s. All three must be identical; do not "
            "lock." % (audit_rev, MODEL_REVISION, script_rev)
        )

    manifest = {
        "framework": "AEPF SST2_OVP_CALIB materialization manifest",
        "study": "SST2_OVP_CALIB cut-point calibration (lock 1 of the two-lock real-candidate arc)",
        "governing_spec": "OVP v0.1 @ signed tag ovp-v0.1-lock",
        "lock_tag": "sst2-ovp-calib-lock",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "master_seed": MASTER_SEED,
        "substrate": {
            "type": "external dataset + external model (real)",
            "dataset": {
                "path": DATA_CSV.replace(os.sep, "/"),
                "sha256": data_sha,
                "recorded_sha256": recorded,
                "matches_audit_record": data_match,
                "source": "DistilBERT-SST2 calibration audit (case_studies/distilbert_sst2)",
            },
            "model": {
                "id": MODEL_ID,
                "revision": MODEL_REVISION,
                "identity_checked_at_lock": True,  # audit model_revision.txt == manifest == script, asserted above
                "source": "identical to the DistilBERT-SST2 audit (model_revision.txt / "
                          "calibration_summary.json)",
                "inference": "deterministic (no sampling); per-example outputs reproducible",
            },
            "attestation": (
                "B=max-softmax-confidence and y=correctness are materialized by running "
                "the pinned model (id+revision above) once over the pinned, hash-verified "
                "dataset. negation_count is NOT computed here (it is the lock-2 candidate). "
                "sst2_per_example.csv is an output of the single locked run, hashed by the run."
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
            "parameters; this manifest does not restate them. scikit-learn, transformers, "
            "and torch versions are recorded because the pinned estimator and model "
            "inference can vary numerically across versions."
        ),
    }
    with open("materialization_manifest_sst2_calib.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
