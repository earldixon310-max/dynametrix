#!/usr/bin/env python3
"""
build_manifest_poscontrol.py - materialization manifest generator for the
OVP_POSCONTROL_v1 positive control (AEPF materialization discipline).

Run at LOCK time, on the machine that will execute the locked study, to capture:
  - SHA-256 of the locked artifacts (positive-control pre-reg + validate_ovp.py)
  - the execution environment (python, numpy, scikit-learn versions)
  - the master seed and a synthetic-data attestation
  - the inherited calibration provenance (the frozen cut points come from the
    locked calibration result, tag ovp-poscontrol-v1-calib-result)

Writes materialization_manifest_poscontrol.json, committed in the single atomic
lock commit alongside the pre-registration and validate_ovp.py.

This study uses NO external dataset or model: all data are generated
deterministically from master_seed = 0xFACADE by the locked validate_ovp.py.
The frozen cut points (tau_lo, tau_hi, Arm1 sigma_C, Arm3 sigma3) are inherited
from the calibration result and hardcoded in validate_ovp.py with a startup
cross-check against calibration_results.json. The pre-registration's SHA-256 is
the authoritative record of every pinned parameter; this manifest does not
restate them.

Run on the authoritative machine after the pre-reg has cleared its two cold
passes and is final - it hashes the bytes as they stand on disk.
"""
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone

ARTIFACTS = [
    "PRE_REGISTRATION_OVP_POSCONTROL_v1.md",
    "validate_ovp.py",
]
MASTER_SEED = "0xFACADE"


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
        "framework": "AEPF OVP_POSCONTROL_v1 positive-control materialization manifest",
        "study": "OVP_POSCONTROL_v1 positive control (self-validation gate)",
        "governing_spec": "OVP v0.1 @ signed tag ovp-v0.1-lock",
        "lock_tag": "ovp-poscontrol-v1-lock",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "master_seed": MASTER_SEED,
        "inherited_cut_points": {
            "source_tag": "ovp-poscontrol-v1-calib-result",
            "tau_lo": 0.0008520905552347899,
            "tau_hi": 0.016157622564950937,
            "arm1_sigma_C": 2.0,
            "arm3_sigma3": 4.0,
            "note": "Hardcoded in validate_ovp.py and cross-checked against the "
                    "locked calibration_results.json at startup.",
        },
        "data": {
            "type": "synthetic",
            "external_dataset": None,
            "external_model": None,
            "attestation": (
                "All data are generated deterministically from master_seed=0xFACADE "
                "by the locked validate_ovp.py; no external dataset or model is used. "
                "Reproducibility follows from the seed plus the pinned environment below."
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
            "version is recorded because the pinned estimator's numerical behavior "
            "can vary across versions."
        ),
    }
    with open("materialization_manifest_poscontrol.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
