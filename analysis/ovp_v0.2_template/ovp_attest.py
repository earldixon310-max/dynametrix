"""
ovp_attest.py - OVP v0.2 reference: signed additive harness attestation (spec sec 3).

Adds retroactive auditability for a study's smoke harness WITHOUT re-tagging the locked study
(immutability preserved per the rc-v1/ersaf/ct-v1 no-re-sign precedent). It is a NEW signed
object (an annotated, signed git tag) that REFERENCES the study's lock commit by hash and carries
a structured record. The operator signs it (`git tag -s`), which authenticates WHO asserts and
WHEN - not the historical fact of execution.

Two MANDATORY schema distinctions (sec 3):
  claim scope : source_synthetic = VERIFIABLE (read the blob) ; non_execution = ATTESTED-ONLY
                (a historical negative no signature can establish). The record NEVER claims
                non_execution as verifiable.
  anchoring   : anchored/proof-grade   = the harness blob is in the study's signed lock-commit
                                         tree (new v0.2 studies, 5-file locked set);
                unanchored/attestation-grade = grandfathered #1-#4, the harness was NOT in the
                                         original locked set; bound only by the operator's dated
                                         post-hoc identification. Optional temporal hardening:
                                         is the harness blob present in history at/before lock date?
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


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def build_attestation(repo_root, study_lock_tag, harness_path, attested_utc):
    """Construct the structured attestation record. `harness_path` is repo-relative."""
    rc, lock_commit, err = _git(["rev-parse", "%s^{commit}" % study_lock_tag], repo_root)
    if rc != 0:
        raise ValueError("cannot resolve %s (%s)" % (study_lock_tag, err))
    _, lock_date, _ = _git(["show", "-s", "--format=%cI", lock_commit], repo_root)

    abs_harness = os.path.join(repo_root, harness_path)
    _, harness_oid, _ = _git(["hash-object", "--path", harness_path, "--", abs_harness], repo_root)
    harness_sha256 = _sha256(abs_harness)

    # anchored iff the harness blob is in the study's lock-tag tree at harness_path
    rc, tree_oid, _ = _git(["rev-parse", "--verify", "%s:%s" % (study_lock_tag, harness_path)], repo_root)
    anchored = (rc == 0 and tree_oid == harness_oid)

    # temporal bound (unanchored hardening): is this blob present in history at/before lock date?
    temporal = {"checked": True, "present_at_or_before_lock_date": False, "earliest_seen": None, "lock_date": lock_date}
    rc, dates, _ = _git(["log", "--all", "--find-object", harness_oid, "--format=%cI"], repo_root)
    seen = [d for d in dates.splitlines() if d.strip()]
    if seen:
        temporal["earliest_seen"] = min(seen)
        temporal["present_at_or_before_lock_date"] = (min(seen) <= lock_date)

    return {
        "kind": "ovp-harness-attestation",
        "study_lock_tag": study_lock_tag,
        "study_lock_commit": lock_commit,
        "harness_path": harness_path,
        "harness_git_oid": harness_oid,
        "harness_sha256": harness_sha256,
        "claim": {"source_synthetic": "VERIFIABLE", "non_execution": "ATTESTED-ONLY (not provable by any signature)"},
        "anchoring": "anchored" if anchored else "unanchored",
        "grade": "proof-grade" if anchored else "attestation-grade",
        "anchoring_basis": ("harness blob present in the signed lock-commit tree"
                            if anchored else "operator dated post-hoc identification (NOT in original locked set)"),
        "retroactive": not anchored,
        "temporal_bound": (None if anchored else temporal),
        "attested_by": "operator",
        "attested_utc": attested_utc,
        "disclaimer": ("Authenticates who asserts and when; does NOT prove historical execution. "
                       "Unanchored => attestation-grade, explicitly weaker than contemporaneous lock-inclusion."),
    }


def emit_sign_command(record):
    """The operator runs this to create the additive SIGNED tag (zero re-tagging of the study)."""
    payload = json.dumps(record, indent=2)
    tag = record["study_lock_tag"].replace("-lock", "") + "-harness-attest"
    return tag, ("git tag -s %s %s -F - <<'MSG'\n%s\nMSG" % (tag, record["study_lock_commit"], payload))


def verify_attestation(repo_root, attest_tag):
    """Re-derive the verifiable claims from the repo; report VERIFIED / ATTESTED-ONLY / CONTRADICTED.
    (Signature authenticity is a separate `git tag -v` step - the human-trust layer.)"""
    rc, body, err = _git(["for-each-ref", "--format=%(contents)", "refs/tags/%s" % attest_tag], repo_root)
    if rc != 0 or not body:
        return {"ok": False, "error": "cannot read attestation tag %s (%s)" % (attest_tag, err)}
    start = body.find("{")
    record = json.loads(body[start:body.rfind("}") + 1])

    report = {"attest_tag": attest_tag, "study_lock_tag": record["study_lock_tag"], "checks": {}}
    # 1. anchoring claim re-derivation
    rc, tree_oid, _ = _git(["rev-parse", "--verify", "%s:%s" % (record["study_lock_tag"], record["harness_path"])], repo_root)
    in_lock_tree = (rc == 0 and tree_oid == record["harness_git_oid"])
    if record["anchoring"] == "anchored":
        report["checks"]["anchoring"] = "VERIFIED (blob in lock tree)" if in_lock_tree else "CONTRADICTED (claims anchored but blob NOT in lock tree)"
    else:
        report["checks"]["anchoring"] = "consistent: unanchored, blob not in original lock tree" if not in_lock_tree \
            else "NOTE: labeled unanchored but blob is in lock tree (could be upgraded to anchored)"
    # 2. claim scope: must not assert non_execution as verifiable
    report["checks"]["claim_scope"] = ("VERIFIED (source_synthetic only; non_execution attested-only)"
                                       if record["claim"]["non_execution"].startswith("ATTESTED")
                                       else "CONTRADICTED (over-claims non_execution)")
    # 3. temporal bound (unanchored)
    if record["anchoring"] == "unanchored" and record.get("temporal_bound"):
        tb = record["temporal_bound"]
        report["checks"]["temporal_bound"] = ("harness in history at/before lock date" if tb["present_at_or_before_lock_date"]
                                              else "NOT before lock date (earliest seen: %s; lock: %s) - weaker" % (tb["earliest_seen"], tb["lock_date"]))
    report["grade"] = record["grade"]
    report["ok"] = report["checks"]["anchoring"].startswith(("VERIFIED", "consistent")) and report["checks"]["claim_scope"].startswith("VERIFIED")
    return report
