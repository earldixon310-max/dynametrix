"""
materialize_desi_dr1_bao.py — DESI DR1 BAO data materialization converter

Reads the per-tracer BAO measurement files from a local clone of
`CobayaSampler/bao_data` (pinned by commit SHA at lock time) and produces the
canonical `desi_dr1_bao.csv` + `desi_dr1_bao_cov.npy` consumed by
ersaf_analysis.py's load_desi_dr1_bao().

Provenance chain (path C per pre-reg §3.1 amendment):

  CobayaSampler/bao_data @ <commit SHA>  ←  primary source-of-truth
                  │
                  ▼
  This converter reads per-tracer `_mean.txt` + `_cov.txt` files
                  │
                  ▼
  Each loaded value is cross-verified against TABLE_1_REFERENCE below
  (the literal published values from DESI 2024 III Table 1 and DESI
  2024 IV Table) within its per-value tolerance.
                  │
                  ▼
  Output: desi_dr1_bao.csv (12 rows) + desi_dr1_bao_cov.npy (12×12)

Three audit surfaces are placed on the data acquisition step:
  1. The converter logic (this file).
  2. The TABLE_1_REFERENCE dict (verifiable against paper PDFs).
  3. The tolerance choice per value (half-unit on the last published decimal).

The comprehensive review (Task #96) will verify all three independently.

OPERATOR VERIFICATION REQUIRED BEFORE LOCK COMMIT:
  The TABLE_1_REFERENCE values below are best-recall starting values.
  Open the published PDFs and verify each value matches Table 1 exactly.
  Replace any discrepancies before running this converter for the lock.

  - DESI 2024 III: https://arxiv.org/abs/2404.03000  (Table 1)
  - DESI 2024 IV:  https://arxiv.org/abs/2404.03001  (Table 1 or equivalent)
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# TABLE_1_REFERENCE — published values + per-value tolerances + source citations
# =============================================================================
#
# Each entry is keyed by (bin_label, observable_type) and carries:
#   value:     the published central value (D_M/r_d, D_H/r_d, or D_V/r_d)
#   tolerance: half-unit on the last reported decimal of the published value
#   source:    paper + table reference
#
# This dict is the lock-time commitment to "the twelve observables published
# in DR1." The converter asserts each value loaded from CobayaSampler/bao_data
# matches this dict within tolerance before writing the materialized CSV.
#
# OPERATOR: verify each value against the cited paper Table before lock.

TABLE_1_REFERENCE = {
    # --- DESI 2024 III (galaxy/quasar BAO, arXiv:2404.03000) ---
    ("BGS",      "DV_over_rd"): {
        "value": 7.93, "tolerance": 0.005, "z_eff": 0.295,
        "source": "DESI 2024 III Table 1 (arXiv:2404.03000)",
    },
    ("LRG1",     "DM_over_rd"): {
        "value": 13.62, "tolerance": 0.005, "z_eff": 0.510,
        "source": "DESI 2024 III Table 1 (arXiv:2404.03000)",
    },
    ("LRG1",     "DH_over_rd"): {
        "value": 20.98, "tolerance": 0.005, "z_eff": 0.510,
        "source": "DESI 2024 III Table 1 (arXiv:2404.03000)",
    },
    ("LRG2",     "DM_over_rd"): {
        "value": 16.85, "tolerance": 0.005, "z_eff": 0.706,
        "source": "DESI 2024 III Table 1 (arXiv:2404.03000)",
    },
    ("LRG2",     "DH_over_rd"): {
        "value": 20.08, "tolerance": 0.005, "z_eff": 0.706,
        "source": "DESI 2024 III Table 1 (arXiv:2404.03000)",
    },
    ("LRG3+ELG1", "DM_over_rd"): {
        "value": 21.71, "tolerance": 0.005, "z_eff": 0.930,
        "source": "DESI 2024 III Table 1 (arXiv:2404.03000)",
    },
    ("LRG3+ELG1", "DH_over_rd"): {
        "value": 17.88, "tolerance": 0.005, "z_eff": 0.930,
        "source": "DESI 2024 III Table 1 (arXiv:2404.03000)",
    },
    ("ELG2",     "DM_over_rd"): {
        "value": 27.79, "tolerance": 0.005, "z_eff": 1.317,
        "source": "DESI 2024 III Table 1 (arXiv:2404.03000)",
    },
    ("ELG2",     "DH_over_rd"): {
        "value": 13.82, "tolerance": 0.005, "z_eff": 1.317,
        "source": "DESI 2024 III Table 1 (arXiv:2404.03000)",
    },
    ("QSO",      "DV_over_rd"): {
        "value": 26.07, "tolerance": 0.005, "z_eff": 1.491,
        "source": "DESI 2024 III Table 1 (arXiv:2404.03000)",
    },
    # --- DESI 2024 IV (Lyα forest BAO, arXiv:2404.03001) ---
    ("Lya",      "DM_over_rd"): {
        "value": 39.71, "tolerance": 0.005, "z_eff": 2.330,
        "source": "DESI 2024 IV Table 1 (arXiv:2404.03001)",
    },
    ("Lya",      "DH_over_rd"): {
        "value": 8.52,  "tolerance": 0.005, "z_eff": 2.330,
        "source": "DESI 2024 IV Table 1 (arXiv:2404.03001)",
    },
}

# Bin ordering for the output CSV (drives row order in both .csv and .npy)
BIN_ORDER = [
    (1, "BGS",       0.295, ["DV_over_rd"]),
    (2, "LRG1",      0.510, ["DM_over_rd", "DH_over_rd"]),
    (3, "LRG2",      0.706, ["DM_over_rd", "DH_over_rd"]),
    (4, "LRG3+ELG1", 0.930, ["DM_over_rd", "DH_over_rd"]),
    (5, "ELG2",      1.317, ["DM_over_rd", "DH_over_rd"]),
    (6, "QSO",       1.491, ["DV_over_rd"]),
    (7, "Lya",       2.330, ["DM_over_rd", "DH_over_rd"]),
]

# CobayaSampler/bao_data per-bin file conventions. The exact filenames depend
# on the upstream repo's naming scheme at the pinned commit; these are the
# canonical patterns at the time of writing. Operator: adjust if the upstream
# repo has renamed files at the pinned commit.
COBAYA_FILE_PATTERNS = {
    "BGS":       {"mean": "desi_2024_gaussian_bao_BGS_BRIGHT-21.5_GCcomb_z0.1-0.4_mean.txt",
                  "cov":  "desi_2024_gaussian_bao_BGS_BRIGHT-21.5_GCcomb_z0.1-0.4_cov.txt"},
    "LRG1":      {"mean": "desi_2024_gaussian_bao_LRG_GCcomb_z0.4-0.6_mean.txt",
                  "cov":  "desi_2024_gaussian_bao_LRG_GCcomb_z0.4-0.6_cov.txt"},
    "LRG2":      {"mean": "desi_2024_gaussian_bao_LRG_GCcomb_z0.6-0.8_mean.txt",
                  "cov":  "desi_2024_gaussian_bao_LRG_GCcomb_z0.6-0.8_cov.txt"},
    "LRG3+ELG1": {"mean": "desi_2024_gaussian_bao_LRG+ELG_LOPnotqso_GCcomb_z0.8-1.1_mean.txt",
                  "cov":  "desi_2024_gaussian_bao_LRG+ELG_LOPnotqso_GCcomb_z0.8-1.1_cov.txt"},
    "ELG2":      {"mean": "desi_2024_gaussian_bao_ELG_LOPnotqso_GCcomb_z1.1-1.6_mean.txt",
                  "cov":  "desi_2024_gaussian_bao_ELG_LOPnotqso_GCcomb_z1.1-1.6_cov.txt"},
    "QSO":       {"mean": "desi_2024_gaussian_bao_QSO_GCcomb_z0.8-2.1_mean.txt",
                  "cov":  "desi_2024_gaussian_bao_QSO_GCcomb_z0.8-2.1_cov.txt"},
    "Lya":       {"mean": "desi_2024_gaussian_bao_Lya_GCcomb_mean.txt",
                  "cov":  "desi_2024_gaussian_bao_Lya_GCcomb_cov.txt"},
}


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cobaya_bin(source_dir, bin_label, expected_observables):
    """Load one CobayaSampler/bao_data bin's mean and covariance files.

    Mean file format (3 whitespace-separated columns per row):
        z, value, observable_type_string
    where observable_type_string uses CobayaSampler's `_over_rs` naming
    convention (e.g., "DM_over_rs", "DH_over_rs", "DV_over_rs").

    This loader normalizes `_over_rs` to `_over_rd` at the converter boundary
    so the rest of the ERSAF pipeline (predict_desi_bao, CSV column values)
    sees the `_over_rd` convention consistently. `r_s` and `r_d` refer to
    the same physical quantity (sound horizon at the drag epoch) under
    standard DESI BAO convention; the difference is purely notational.

    Cov file format: square ASCII matrix matching the mean file's row count
    and row order. A 1-row mean file may have a scalar cov file (which this
    loader wraps into a 1×1 matrix).

    File order is preserved through to the converter output — the .npy
    covariance row/column ordering matches the CSV row order, which matches
    the mean file's row order. BIN_ORDER's `expected_observables` is used
    as a set-equality validation check rather than to reorder rows.

    Returns:
        z_eff:        shared effective redshift for this bin
        values:       ndarray of measurement values in file order
        cov_block:    ndarray covariance for this bin's observables (file order)
        loaded_order: list of observable_type strings (normalized to _over_rd)
                      in the order the file presents them
    """
    pattern = COBAYA_FILE_PATTERNS[bin_label]
    mean_path = Path(source_dir) / pattern["mean"]
    cov_path = Path(source_dir) / pattern["cov"]

    if not mean_path.exists():
        raise FileNotFoundError(
            f"Missing mean file for bin {bin_label}: {mean_path}. "
            f"Verify CobayaSampler/bao_data is cloned at the pinned commit and "
            f"the filename convention matches that commit."
        )
    if not cov_path.exists():
        raise FileNotFoundError(
            f"Missing cov file for bin {bin_label}: {cov_path}."
        )

    # Parse 3-column mean file by hand (numpy.loadtxt can't handle the
    # mixed numeric+string columns cleanly).
    z_vals = []
    values = []
    loaded_order = []
    with open(mean_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 3:
                raise ValueError(
                    f"Bin {bin_label} mean file {mean_path} has a row with "
                    f"fewer than 3 fields: {line!r}. Expected (z, value, observable_type)."
                )
            z_vals.append(float(parts[0]))
            values.append(float(parts[1]))
            # Normalize CobayaSampler's `_over_rs` to ERSAF's `_over_rd` convention.
            obs_type_raw = parts[2]
            obs_type_normalized = obs_type_raw.replace("_over_rs", "_over_rd")
            loaded_order.append(obs_type_normalized)

    if len(z_vals) == 0:
        raise ValueError(f"Bin {bin_label} mean file {mean_path} has no data rows.")

    z_vals_arr = np.array(z_vals)
    values_arr = np.array(values)

    # Validate per-bin z_eff is consistent across rows.
    if not np.allclose(z_vals_arr, z_vals_arr[0], atol=1e-6):
        raise ValueError(
            f"Bin {bin_label} mean file has inconsistent z values: {z_vals_arr}. "
            "Each bin's observables should share a single z_eff."
        )
    z_eff = float(z_vals_arr[0])

    # Verify the loaded observable types match what BIN_ORDER expects
    # (as a set — file order is authoritative for within-bin row ordering).
    expected_set = set(expected_observables)
    loaded_set = set(loaded_order)
    if loaded_set != expected_set:
        raise ValueError(
            f"Bin {bin_label}: mean file has observables {loaded_order}, "
            f"BIN_ORDER expects {list(expected_observables)}. "
            f"Either the source file structure has changed or BIN_ORDER is wrong."
        )

    # Load covariance. May be a scalar (1-row bins) or square matrix.
    cov_block = np.loadtxt(cov_path)
    if cov_block.ndim == 0:
        cov_block = np.array([[float(cov_block)]])
    elif cov_block.ndim == 1:
        # 1D array from a single-line cov file: treat as scalar variance for a 1-row bin.
        if len(cov_block) == 1:
            cov_block = np.array([[float(cov_block[0])]])
        else:
            # Otherwise it's likely a diagonal stored 1D
            cov_block = np.diag(cov_block)

    if cov_block.shape[0] != cov_block.shape[1]:
        raise ValueError(
            f"Bin {bin_label} cov file is not square: shape {cov_block.shape}."
        )
    if cov_block.shape[0] != len(values_arr):
        raise ValueError(
            f"Bin {bin_label}: mean file has {len(values_arr)} rows but cov file is "
            f"{cov_block.shape[0]}×{cov_block.shape[0]}. Inconsistent."
        )

    return z_eff, values_arr, cov_block, loaded_order


def cross_verify_against_table_1(bin_label, observable_type, value):
    """Assert loaded value matches TABLE_1_REFERENCE within published tolerance."""
    key = (bin_label, observable_type)
    if key not in TABLE_1_REFERENCE:
        raise ValueError(
            f"No TABLE_1_REFERENCE entry for ({bin_label!r}, {observable_type!r}). "
            "Either the bin/observable is not part of the locked 12-observable set "
            "or the reference dict is missing an entry."
        )
    ref = TABLE_1_REFERENCE[key]
    diff = abs(value - ref["value"])
    if diff > ref["tolerance"]:
        raise AssertionError(
            f"Verification FAILED for ({bin_label}, {observable_type}): "
            f"loaded value {value!r} differs from {ref['source']} value "
            f"{ref['value']!r} by {diff:.6f}, exceeds tolerance ±{ref['tolerance']}. "
            "Either the CobayaSampler/bao_data source has changed, the TABLE_1_REFERENCE "
            "dict has a typo, or the tolerance is too tight."
        )
    return diff


def main():
    parser = argparse.ArgumentParser(
        description="DESI DR1 BAO materialization converter (CobayaSampler/bao_data → CSV + .npy)."
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Path to a local clone of CobayaSampler/bao_data (at the pinned commit).",
    )
    parser.add_argument(
        "--output-dir",
        default="analysis/ersaf/data/desi_dr1",
        help="Output directory for desi_dr1_bao.csv + desi_dr1_bao_cov.npy.",
    )
    parser.add_argument(
        "--source-commit",
        default=None,
        help="CobayaSampler/bao_data commit SHA at which the source files are pinned "
             "(recorded in the lock manifest; not enforced by this script).",
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("DESI DR1 BAO materialization — CobayaSampler/bao_data → CSV + .npy")
    print("=" * 72)
    print(f"Source: {source_dir}")
    if args.source_commit:
        print(f"Pinned commit: {args.source_commit}")
    else:
        print("WARNING: --source-commit not provided. Record the SHA in the lock manifest manually.")
    print(f"Output: {output_dir}")
    print()

    # Load each bin and assemble the data vector + block-diagonal covariance
    rows = []
    cov_blocks = []
    source_file_hashes = {}
    total_obs = 0

    for bin_id, bin_label, expected_z, expected_observables in BIN_ORDER:
        print(f"Bin {bin_id} ({bin_label}, z_eff≈{expected_z}):")
        z_eff, values, cov_block, loaded_order = load_cobaya_bin(
            source_dir, bin_label, expected_observables,
        )
        if abs(z_eff - expected_z) > 0.01:
            raise ValueError(
                f"Bin {bin_label}: source z_eff={z_eff} differs from BIN_ORDER "
                f"z_eff={expected_z} by more than 0.01. Verify source file alignment."
            )

        # Record file hashes
        for tag in ("mean", "cov"):
            file_path = source_dir / COBAYA_FILE_PATTERNS[bin_label][tag]
            source_file_hashes[f"{bin_label}_{tag}"] = sha256_of_file(file_path)

        # Cross-verify each loaded value against TABLE_1_REFERENCE
        for j, obs_type in enumerate(loaded_order):
            diff = cross_verify_against_table_1(bin_label, obs_type, values[j])
            err_diag = float(np.sqrt(cov_block[j, j]))
            print(f"  {obs_type:>12s}: value={values[j]:.4f}, err={err_diag:.4f} "
                  f"(Δ vs Table 1 = {diff:.6f}, OK)")
            rows.append({
                "bin_id": bin_id,
                "bin_label": bin_label,
                "z": z_eff,
                "observable_type": obs_type,
                "value": float(values[j]),
                "error": err_diag,
            })

        cov_blocks.append(cov_block)
        total_obs += len(values)

    if total_obs != 12:
        raise RuntimeError(
            f"Expected 12 total observables across all bins; got {total_obs}. "
            "Verify BIN_ORDER and source files."
        )

    # Assemble block-diagonal 12×12 covariance preserving each bin's internal
    # correlations (notably the LRG+ELG joint bin's non-diagonal 2×2 sub-block).
    cov_full = np.zeros((12, 12))
    offset = 0
    for block in cov_blocks:
        n = block.shape[0]
        cov_full[offset:offset + n, offset:offset + n] = block
        offset += n

    df = pd.DataFrame(rows)

    # Sanity: published sqrt(diag(cov)) should match the per-row error column to machine precision
    rel_diff = np.abs(np.sqrt(np.diag(cov_full)) - df["error"].to_numpy()) / df["error"].to_numpy()
    if np.any(rel_diff > 1e-9):
        raise RuntimeError(
            "Internal inconsistency: sqrt(diag(cov)) != df['error'] after assembly. "
            "This is a bug in the converter, not a source-data issue."
        )

    # Write outputs
    csv_path = output_dir / "desi_dr1_bao.csv"
    cov_path = output_dir / "desi_dr1_bao_cov.npy"
    df.to_csv(csv_path, index=False, float_format="%.10g")
    np.save(cov_path, cov_full)

    print()
    print("Outputs written:")
    print(f"  {csv_path}")
    print(f"  {cov_path}")

    # SHA-256s of outputs and inputs
    out_hashes = {
        "desi_dr1_bao.csv": sha256_of_file(csv_path),
        "desi_dr1_bao_cov.npy": sha256_of_file(cov_path),
    }

    print()
    print("Materialization manifest:")
    manifest = {
        "source": {
            "repository": "CobayaSampler/bao_data",
            "commit_sha": args.source_commit or "TBD (record before lock commit)",
            "source_dir_at_runtime": str(source_dir),
            "per_file_sha256": source_file_hashes,
        },
        "outputs": {
            "csv_sha256": out_hashes["desi_dr1_bao.csv"],
            "npy_sha256": out_hashes["desi_dr1_bao_cov.npy"],
        },
        "verification_anchor": {
            "n_entries": len(TABLE_1_REFERENCE),
            "sources_cited": sorted({v["source"] for v in TABLE_1_REFERENCE.values()}),
            "all_passed": True,
        },
        "n_bins": len(BIN_ORDER),
        "n_observables": total_obs,
    }
    print(json.dumps(manifest, indent=2))

    manifest_path = output_dir / "materialization_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest written: {manifest_path}")


if __name__ == "__main__":
    main()