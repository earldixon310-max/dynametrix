"""
build_manifest.py — resolve the TBD pins and compute the §11 materialization
manifest for RC_v1.

Run on the target hardware (Profile B) at lock time, after the decision to lock
and before the atomic lock commit (covers §15 steps 1–2). It does NOT run any
model inference and does NOT consume the single-execution budget.

Two phases:

  1. Resolve pinned revisions (the §15 step-1 TBDs):
       - cais/mmlu (dataset) repo commit SHA
       - Qwen/Qwen2.5-7B-Instruct-AWQ (model) repo commit SHA
       - sentence-transformers/all-MiniLM-L6-v2 (embedding) repo commit SHA
       - installed vLLM version
     plus a content fingerprint built from each repo's file listing (LFS sha256
     where available), so each pin is content-level rather than a moving ref.

  2. Compute the deterministic qid lists (main 3×100 and calibration 50) using
     the SAME load_mmlu_items the analysis uses, hash them, hash the analysis
     script, and write materialization_manifest.json (§11).

By default this is a DRY RUN: it resolves everything, writes the manifest, and
prints the values that WOULD be pinned into PRE_REGISTRATION_RC_v1.md — but does
not touch the pre-registration. Pass --apply to perform the section-scoped,
uniqueness-guarded TBD substitutions in the pre-registration (a .bak backup is
written first; every anchor is verified to occur exactly once in its scope before
any write, and the run aborts without writing if any anchor is missing/ambiguous).

The git lock-commit SHA (top-of-document "Lock-commit SHA: TBD") and the
calibration_constants / calibration_distributions hashes are intentionally left
for their own later steps (§15 steps 5–7); this script does not fill them.

Usage:
    python build_manifest.py                 # dry run: write manifest, print pins
    python build_manifest.py --apply         # also pin TBDs into the pre-reg
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import List, Tuple

HERE = Path(__file__).resolve().parent
PREREG = HERE / "PRE_REGISTRATION_RC_v1.md"
SCRIPT = HERE / "rc_v1_analysis.py"
MANIFEST = HERE / "materialization_manifest.json"

DATASET_REPO = "cais/mmlu"

# Pull the exact constants + loader the analysis uses, so the manifest records
# the identical selection. rc_v1_analysis imports nothing heavy at module scope.
from rc_v1_analysis import (  # noqa: E402
    MASTER_SEED, MODEL_REPO, EMBED_REPO,
    MAIN_SUBJECTS, QUERIES_PER_SUBJECT, CALIBRATION_SUBJECT, CALIBRATION_N,
    load_mmlu_items, sha256_file,
)


# -------------------------------------------------------------------------
# Phase 1: resolve HF revisions + content fingerprints
# -------------------------------------------------------------------------

def _file_hash(sibling) -> str:
    """Best available content hash for one repo file: LFS sha256 > git blob id > size."""
    lfs = getattr(sibling, "lfs", None)
    if lfs:
        h = lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)
        if h:
            return f"lfs:{h}"
    bid = getattr(sibling, "blob_id", None) or getattr(sibling, "oid", None)
    if bid:
        return f"git:{bid}"
    return f"size:{getattr(sibling, 'size', 0)}"


def resolve_repo(repo_id: str, repo_type: str) -> dict:
    """Return {repo, type, revision_sha, content_fingerprint, n_files} for an HF repo
    at the current HEAD of `main`, without downloading file contents."""
    from huggingface_hub import HfApi
    api = HfApi()
    info = api.repo_info(repo_id=repo_id, repo_type=repo_type,
                         revision="main", files_metadata=True)
    siblings = sorted(info.siblings, key=lambda s: s.rfilename)
    listing = "\n".join(f"{s.rfilename} {_file_hash(s)}" for s in siblings)
    fingerprint = hashlib.sha256(listing.encode("utf-8")).hexdigest()
    return {
        "repo": repo_id,
        "type": repo_type,
        "revision_sha": info.sha,
        "content_fingerprint": fingerprint,
        "n_files": len(siblings),
    }


def vllm_version() -> str:
    try:
        import vllm
        v = getattr(vllm, "__version__", None)
        if v:
            return str(v)
    except Exception:
        pass
    try:
        from importlib.metadata import version
        return str(version("vllm"))
    except Exception:
        return "UNRESOLVED (vLLM not importable in this environment)"


# -------------------------------------------------------------------------
# Phase 2: deterministic qid lists + script hash
# -------------------------------------------------------------------------

def qid_list(pairs: List[Tuple[str, int]]) -> Tuple[List[dict], str]:
    """Load items for each (subject, n) and return ([{subject,qid}], sha256 of the qid sequence)."""
    rows: List[dict] = []
    for subject, n in pairs:
        for it in load_mmlu_items(subject, n):
            rows.append({"subject": subject, "qid": it["qid"]})
    digest = hashlib.sha256("\n".join(r["qid"] for r in rows).encode("utf-8")).hexdigest()
    return rows, digest


# -------------------------------------------------------------------------
# Phase 3 (optional): pin TBDs into the pre-registration
# -------------------------------------------------------------------------

def _sub_unique(text: str, find: str, repl: str, label: str) -> str:
    c = text.count(find)
    if c != 1:
        raise SystemExit(f"[abort] anchor for '{label}' occurs {c} times (need exactly 1): {find!r}")
    return text.replace(find, repl, 1)


def _sub_in_scope(text: str, start: str, end: str, find: str, repl: str, label: str) -> str:
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"[abort] scope start not found for '{label}': {start!r}")
    j = text.find(end, i + len(start))
    if j < 0:
        raise SystemExit(f"[abort] scope end not found for '{label}': {end!r}")
    seg = text[i:j]
    c = seg.count(find)
    if c != 1:
        raise SystemExit(f"[abort] anchor for '{label}' occurs {c} times in scope (need 1): {find!r}")
    return text[:i] + seg.replace(find, repl, 1) + text[j:]


def pin_document(vals: dict) -> None:
    text = PREREG.read_text(encoding="utf-8")
    ds, mdl, emb, ver = (vals["dataset"]["revision_sha"], vals["model"]["revision_sha"],
                         vals["embedding"]["revision_sha"], vals["vllm_version"])

    # §2.1 dataset revision (unique label)
    text = _sub_unique(text, "**Pinned dataset revision:** TBD",
                       f"**Pinned dataset revision:** `{ds}`", "§2.1 dataset revision")
    # §2.2 model revision (the "Pinned revision SHA: TBD" line shared with §2.4 — scope it)
    text = _sub_in_scope(text, "### 2.2 Model", "### 2.3 Compute profile",
                         "**Pinned revision SHA:** TBD (filled at lock-commit)",
                         f"**Pinned revision SHA:** `{mdl}`", "§2.2 model revision")
    # §2.4 embedding revision
    text = _sub_in_scope(text, "### 2.4 Embedding model", "### 2.5 Base prompt template",
                         "**Pinned revision SHA:** TBD (filled at lock-commit)",
                         f"**Pinned revision SHA:** `{emb}`", "§2.4 embedding revision")
    # §2.3 vLLM version
    text = _sub_unique(text, "pinned version recorded at lock-commit",
                       f"pinned version `{ver}`", "§2.3 vLLM version")
    # §10 five-line lock references
    text = _sub_unique(text, "at pinned dataset revision (TBD)",
                       f"at pinned dataset revision (`{ds}`)", "§10 dataset revision")
    text = _sub_unique(text, "at HF revision (TBD)",
                       f"at HF revision (`{mdl}`)", "§10 model revision")
    text = _sub_unique(text, "all-MiniLM-L6-v2 (revision TBD)",
                       f"all-MiniLM-L6-v2 (revision `{emb}`)", "§10 embedding revision")

    PREREG.with_suffix(".md.bak").write_text(PREREG.read_text(encoding="utf-8"), encoding="utf-8")
    PREREG.write_text(text, encoding="utf-8")
    print(f"[apply] pinned revisions into {PREREG.name} (backup: {PREREG.name}.bak)")


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="pin resolved revisions into the pre-registration (default: dry run)")
    args = ap.parse_args()

    print("[1/3] resolving HF revisions (no downloads)...")
    dataset = resolve_repo(DATASET_REPO, "dataset")
    model = resolve_repo(MODEL_REPO, "model")
    embedding = resolve_repo(EMBED_REPO, "model")
    ver = vllm_version()

    print("[2/3] computing deterministic qid lists (loads dataset; no inference)...")
    main_pairs = [(s, QUERIES_PER_SUBJECT) for s in MAIN_SUBJECTS]
    main_rows, main_digest = qid_list(main_pairs)
    cal_rows, cal_digest = qid_list([(CALIBRATION_SUBJECT, CALIBRATION_N)])

    print("[3/3] hashing analysis script + assembling manifest...")
    manifest = {
        "framework": "AEPF RC_v1 materialization manifest (§11)",
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "master_seed": hex(MASTER_SEED),
        "vllm_version": ver,
        "dataset": dataset,
        "model": model,
        "embedding": embedding,
        "analysis_script": {"path": SCRIPT.name, "sha256": sha256_file(SCRIPT)},
        "main_eval": {
            "subjects": MAIN_SUBJECTS,
            "queries_per_subject": QUERIES_PER_SUBJECT,
            "n_queries": len(main_rows),
            "qid_sequence_sha256": main_digest,
            "qids": main_rows,
        },
        "calibration": {
            "subject": CALIBRATION_SUBJECT,
            "n": CALIBRATION_N,
            "qid_sequence_sha256": cal_digest,
            "qids": cal_rows,
        },
        "deferred": ("git lock-commit SHA and calibration_constants.json / "
                     "calibration_distributions.npz hashes are recorded in their own "
                     "later steps (§15 steps 5–7), not by this script"),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nwrote {MANIFEST.name}  (manifest SHA-256: {sha256_file(MANIFEST)})")

    print("\n===== VALUES TO PIN (§15 step 1) =====")
    print(f"  cais/mmlu dataset revision : {dataset['revision_sha']}")
    print(f"  Qwen2.5-7B-Instruct-AWQ    : {model['revision_sha']}")
    print(f"  all-MiniLM-L6-v2           : {embedding['revision_sha']}")
    print(f"  vLLM version               : {ver}")
    print(f"  main qid-sequence SHA-256  : {main_digest}")
    print(f"  calibration qid SHA-256    : {cal_digest}")
    print("======================================")

    if args.apply:
        pin_document(manifest)
    else:
        print("\n(dry run — pre-registration not modified; re-run with --apply to pin the TBDs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
