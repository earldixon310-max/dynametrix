#!/usr/bin/env python3
"""
build_manifest.py - materialization manifest generator for the OVP_POSCONTROL_v1
cut-point calibration study (AEPF materialization discipline).

Run at LOCK time, on the machine that will execute the locked study, to capture:
  - SHA-256 of the locked artifacts (pre-registration + analysis script)
  - the execution environment (python, numpy, scikit-learn versions)
  - the pinned master seed and a synthetic-data attestation

Writes materialization_manifest.json, committed in the single atomic lock commit
alongside the pre-registration and calibrate_cutpoints.py.

This study uses NO external dataset or model: all data are generated
deterministically from master_seed = 0xCA11B by the locked calibrate_cutpoints.py.
The manifest therefore records a synthetic-data attestation rather than
dataset/model content fingerprints. The pre-registration's SHA-256 is the
authoritative record of every pinned parameter (grids, N, R_cal, cut-point rules,
estimator); the manifest does not duplicate them.

Note: run this on the authoritative machine after the pre-reg has cleared its two
cold passes and is final - it hashes the bytes as they stand on disk.
"""
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone

ARTIFACTS = [
    "PRE_REGISTRATION_OVP_POSCONTROL_v1_CALIB.md",
    "calibrate_cutpoints.py",
]
MASTER_SEED = "0xCA11B"


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
    manifest = {
        "framework": "AEPF OVP_POSCONTROL_v1 calibration materialization manifest",
        "study": "OVP_POSCONTROL_v1 cut-point calibration",
        "governing_spec": "OVP v0.1 @ signed tag ovp-v0.1-lock",
        "lock_tag": "ovp-poscontrol-v1-calib-lock",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "master_seed": MASTER_SEED,
        "data": {
            "type": "synthetic",
            "external_dataset": None,
            "external_model": None,
            "attestation": (
                "All data are generated deterministically from master_seed=0xCA11B "
                "by the locked calibrate_cutpoints.py; no external dataset or model "
                "is used. Reproducibility follows from the seed plus the pinned "
                "environment below."
            ),
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": version("numpy"),
            "scikit_learn": version("sklearn"),
        },
        "artifacts": [{"path": p, "sha256": sha256(p)} for p in ARTIFACTS],
        "note": (
            "The pre-registration SHA-256 above is the authoritative record of all "
            "pinned parameters; this manifest does not restate them. scikit-learn's "
            "version is recorded (not just required) because the pinned estimator's "
            "numerical behavior can vary across versions."
        ),
    }
    with open("materialization_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
