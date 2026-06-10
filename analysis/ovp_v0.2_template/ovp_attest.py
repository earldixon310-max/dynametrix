"""
ovp_attest.py - OVP v0.2 reference: signed additive harness attestation (spec sec 3), rev4.

rev3 derived `grade` from re-derived anchoring (not the record). rev4 (cold-pass-A reader #3)
applies the same "re-derive, never trust" rule to the TEMPORAL bound: verify_attestation re-runs
the git history check rather than echoing record["temporal_bound"]. Additive, zero re-tagging;
accident-prevention scope (R-1); signature authenticity is the separate `git tag -v` step.
"""
import hashlib
import json
import os
import subprocess


def _git(args, cwd):
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", "git-binary-absent"


def _git_blob_sha256(oid, cwd):
    """sha256 of the ACTUAL blob bytes at `oid` (binary-safe), or None if unretrievable."""
    try:
        p = subprocess.run(["git", "cat-file", "blob", oid], cwd=cwd, capture_output=True)
        return hashlib.sha256(p.stdout).hexdigest() if p.returncode == 0 else None
    except Exception:
        return None


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def _compute_temporal(repo_root, harness_oid, lock_date):
    """Is the harness blob present in history at/before lock_date? Used by BOTH build and verify,
    so verify re-derives rather than trusting the record (rev4)."""
    t = {"checked": True, "present_at_or_before_lock_date": False, "earliest_seen": None, "lock_date": lock_date}
    rc, dates, _ = _git(["log", "--all", "--find-object", harness_oid, "--format=%cI"], repo_root)
    seen = [d for d in dates.splitlines() if d.strip()]
    if seen:
        t["earliest_seen"] = min(seen)
        t["present_at_or_before_lock_date"] = (min(seen) <= lock_date)
    return t


def build_attestation(repo_root, study_lock_tag, harness_path, attested_utc):
    rc, lock_commit, err = _git(["rev-parse", "%s^{commit}" % study_lock_tag], repo_root)
    if rc != 0:
        raise ValueError("cannot resolve %s (%s)" % (study_lock_tag, err))
    _, lock_date, _ = _git(["show", "-s", "--format=%cI", lock_commit], repo_root)
    abs_harness = os.path.join(repo_root, harness_path)
    _, harness_oid, _ = _git(["hash-object", "--path", harness_path, "--", abs_harness], repo_root)
    harness_sha256 = _sha256(abs_harness)
    rc, tree_oid, _ = _git(["rev-parse", "--verify", "%s:%s" % (study_lock_tag, harness_path)], repo_root)
    anchored = (rc == 0 and tree_oid == harness_oid)
    temporal = None if anchored else _compute_temporal(repo_root, harness_oid, lock_date)
    return {
        "kind": "ovp-harness-attestation", "study_lock_tag": study_lock_tag, "study_lock_commit": lock_commit,
        "harness_path": harness_path, "harness_git_oid": harness_oid, "harness_sha256": harness_sha256,
        "claim": {"source_synthetic": "VERIFIABLE", "non_execution": "ATTESTED-ONLY (not provable by any signature)"},
        "anchoring": "anchored" if anchored else "unanchored",
        "grade": "proof-grade" if anchored else "attestation-grade",
        "anchoring_basis": ("harness blob present in the signed lock-commit tree" if anchored
                            else "operator dated post-hoc identification (NOT in original locked set)"),
        "retroactive": not anchored, "temporal_bound": temporal,
        "attested_by": "operator", "attested_utc": attested_utc,
        "disclaimer": ("Authenticates who asserts and when; does NOT prove historical execution. "
                       "Unanchored => attestation-grade, explicitly weaker than contemporaneous lock-inclusion."),
    }


def emit_sign_command(record):
    """The operator runs this to create the additive SIGNED tag (zero re-tagging of the study)."""
    payload = json.dumps(record, indent=2)
    tag = record["study_lock_tag"].replace("-lock", "") + "-harness-attest"
    return tag, ("git tag -s %s %s -F - <<'MSG'\n%s\nMSG" % (tag, record["study_lock_commit"], payload))


def verify_attestation(repo_root, attest_tag):
    """Re-derive EVERY checkable claim from the repo - binding, anchoring, grade, AND temporal -
    never trusting the record's self-description. Signature authenticity is `git tag -v`."""
    rc, body, err = _git(["for-each-ref", "--format=%(contents)", "refs/tags/%s" % attest_tag], repo_root)
    if rc != 0 or not body:
        return {"ok": False, "error": "cannot read attestation tag %s (%s)" % (attest_tag, err)}
    record = json.loads(body[body.find("{"):body.rfind("}") + 1])
    report = {"attest_tag": attest_tag, "study_lock_tag": record["study_lock_tag"], "checks": {}}

    # binding: recorded sha256 == actual blob bytes
    actual = _git_blob_sha256(record["harness_git_oid"], repo_root)
    binding_ok = (actual is not None and actual == record["harness_sha256"])
    report["checks"]["binding"] = ("VERIFIED (recorded sha256 == actual blob bytes)" if binding_ok
                                   else "CONTRADICTED/UNVERIFIABLE (sha256 != blob, or blob absent)")

    # anchoring re-derived
    rc, tree_oid, _ = _git(["rev-parse", "--verify", "%s:%s" % (record["study_lock_tag"], record["harness_path"])], repo_root)
    in_lock_tree = (rc == 0 and tree_oid == record["harness_git_oid"])
    if record["anchoring"] == "anchored":
        report["checks"]["anchoring"] = "VERIFIED (blob in lock tree)" if in_lock_tree else "CONTRADICTED (claims anchored but blob NOT in lock tree)"
    else:
        report["checks"]["anchoring"] = ("consistent: unanchored, blob not in original lock tree" if not in_lock_tree
                                         else "NOTE: labeled unanchored but blob is in lock tree")

    # claim scope
    report["checks"]["claim_scope"] = ("well-formed (non_execution attested-only, not verifiable)"
                                       if record["claim"]["non_execution"].startswith("ATTESTED")
                                       else "CONTRADICTED (over-claims non_execution as verifiable)")
    report["checks"]["source_synthetic"] = ("binding-checked; SYNTHETIC-NESS is read-the-blob, NOT machine-confirmed"
                                            if binding_ok else "binding FAILED - do not trust the source-synthetic claim")

    # grade DERIVED from anchoring (rev3)
    derived_grade = "proof-grade" if in_lock_tree else "attestation-grade"
    grade_ok = (record.get("grade") == derived_grade)
    report["checks"]["grade"] = ("VERIFIED (matches derived tier)" if grade_ok
                                 else "CONTRADICTED (record grade %r != derived %r)" % (record.get("grade"), derived_grade))
    report["grade"] = derived_grade

    # temporal RE-DERIVED, not trusted (rev4)
    temporal_ok = True
    if record["anchoring"] == "unanchored":
        rc, lc, _ = _git(["rev-parse", "%s^{commit}" % record["study_lock_tag"]], repo_root)
        _, ld, _ = _git(["show", "-s", "--format=%cI", lc], repo_root)
        red = _compute_temporal(repo_root, record["harness_git_oid"], ld)
        claimed = (record.get("temporal_bound") or {}).get("present_at_or_before_lock_date")
        if claimed is not None and claimed != red["present_at_or_before_lock_date"]:
            report["checks"]["temporal_bound"] = "CONTRADICTED (record claims %s, re-derived %s)" % (claimed, red["present_at_or_before_lock_date"])
            temporal_ok = False
        else:
            report["checks"]["temporal_bound"] = ("re-derived: harness in history at/before lock date"
                                                  if red["present_at_or_before_lock_date"]
                                                  else "re-derived: NOT before lock date (earliest %s; lock %s) - weaker" % (red["earliest_seen"], ld))

    report["ok"] = (binding_ok and grade_ok and temporal_ok
                    and report["checks"]["anchoring"].startswith(("VERIFIED", "consistent"))
                    and report["checks"]["claim_scope"].startswith("well-formed"))
    return report
