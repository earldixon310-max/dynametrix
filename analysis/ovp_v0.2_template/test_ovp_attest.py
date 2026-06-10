"""Execution tests for ovp_attest.py. Builds temp git repos with controlled dates, creates
annotated attestation tags (signing is a separate `git tag -v` human-trust step), verifies."""
import json, os, shutil, subprocess, tempfile, sys
import ovp_attest

def sh(args, cwd, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=e)
def at(d): return {"GIT_AUTHOR_DATE": d, "GIT_COMMITTER_DATE": d}
def init(d):
    sh(["git","init","-q"], d); sh(["git","config","user.email","t@t"], d); sh(["git","config","user.name","t"], d)
def write(d,name,content): open(os.path.join(d,name),"w").write(content)
def make_attest_tag(d, record, tag, commit):
    # annotated tag carrying the attestation JSON (a real run uses `git tag -s`)
    sh(["git","tag","-a",tag,commit,"-m",json.dumps(record,indent=2)], d)

R=[]
def check(n,c): R.append(bool(c)); print(("  PASS " if c else "  FAIL ")+n)

H = "smoke_x.py\n# synthetic-only harness\n"; J = "judge_x.py\n# sealed\n"

# A. ANCHORED: harness in the lock-tag tree -> proof-grade, verify VERIFIED
d=tempfile.mkdtemp(prefix="att_a_"); init(d)
write(d,"smoke_x.py",H); write(d,"judge_x.py",J)
sh(["git","add","smoke_x.py","judge_x.py"], d); sh(["git","commit","-qm","lock"], d, at("2026-06-01T00:00:00"))
sh(["git","tag","study-a-lock"], d)
rec=ovp_attest.build_attestation(d,"study-a-lock","smoke_x.py","2026-06-10T00:00:00Z")
make_attest_tag(d, rec, "study-a-harness-attest", "study-a-lock")
rep=ovp_attest.verify_attestation(d,"study-a-harness-attest")
check("A anchored: grade=proof-grade, anchoring VERIFIED, claim_scope VERIFIED",
      rec["anchoring"]=="anchored" and rec["grade"]=="proof-grade"
      and rep["checks"]["anchoring"].startswith("VERIFIED") and rep["checks"]["claim_scope"].startswith("VERIFIED") and rep["ok"])
shutil.rmtree(d)

# B. UNANCHORED grandfathered (harness committed AFTER lock - the realistic #4 case)
d=tempfile.mkdtemp(prefix="att_b_"); init(d)
write(d,"judge_x.py",J)
sh(["git","add","judge_x.py"], d); sh(["git","commit","-qm","lock"], d, at("2026-06-01T00:00:00"))
sh(["git","tag","study-b-lock"], d)                                   # harness NOT in lock tree
write(d,"smoke_x.py",H); sh(["git","add","smoke_x.py"], d); sh(["git","commit","-qm","records"], d, at("2026-06-05T00:00:00"))
rec=ovp_attest.build_attestation(d,"study-b-lock","smoke_x.py","2026-06-10T00:00:00Z")
make_attest_tag(d, rec, "study-b-harness-attest", "study-b-lock")
rep=ovp_attest.verify_attestation(d,"study-b-harness-attest")
check("B unanchored after-lock: grade=attestation-grade, temporal NOT-before-lock (honest weaker)",
      rec["anchoring"]=="unanchored" and rec["grade"]=="attestation-grade"
      and rec["temporal_bound"]["present_at_or_before_lock_date"] is False
      and "NOT before" in rep["checks"]["temporal_bound"] and rep["ok"])
shutil.rmtree(d)

# C. UNANCHORED but harness blob in history AT/BEFORE lock date (optional hardening HOLDS)
d=tempfile.mkdtemp(prefix="att_c_"); init(d)
write(d,"smoke_x.py",H); sh(["git","add","smoke_x.py"], d); sh(["git","commit","-qm","early-harness"], d, at("2026-05-01T00:00:00"))
sh(["git","rm","-q","smoke_x.py"], d); write(d,"judge_x.py",J); sh(["git","add","judge_x.py"], d)
sh(["git","commit","-qm","lock-without-harness"], d, at("2026-06-01T00:00:00"))
sh(["git","tag","study-c-lock"], d)                                   # harness removed before lock -> unanchored
write(d,"smoke_x.py",H)                                                # restore in working tree so build can hash it
rec=ovp_attest.build_attestation(d,"study-c-lock","smoke_x.py","2026-06-10T00:00:00Z")
make_attest_tag(d, rec, "study-c-harness-attest", "study-c-lock")
rep=ovp_attest.verify_attestation(d,"study-c-harness-attest")
check("C unanchored, temporal-bound HOLDS (blob in history at/before lock date)",
      rec["anchoring"]=="unanchored" and rec["temporal_bound"]["present_at_or_before_lock_date"] is True
      and "at/before lock date" in rep["checks"]["temporal_bound"])
shutil.rmtree(d)

# D. TAMPER: record claims anchored but blob is NOT in lock tree -> verify CONTRADICTED
d=tempfile.mkdtemp(prefix="att_d_"); init(d)
write(d,"judge_x.py",J); sh(["git","add","judge_x.py"], d); sh(["git","commit","-qm","lock"], d); sh(["git","tag","study-d-lock"], d)
write(d,"smoke_x.py",H)
rec=ovp_attest.build_attestation(d,"study-d-lock","smoke_x.py","2026-06-10T00:00:00Z")  # legit unanchored
rec["anchoring"]="anchored"; rec["grade"]="proof-grade"                                  # forge to anchored
make_attest_tag(d, rec, "study-d-harness-attest", "study-d-lock")
rep=ovp_attest.verify_attestation(d,"study-d-harness-attest")
check("D forged-anchored CONTRADICTED (blob not in lock tree)",
      rep["checks"]["anchoring"].startswith("CONTRADICTED") and not rep["ok"])
shutil.rmtree(d)

# E. TAMPER: record over-claims non_execution as verifiable -> verify CONTRADICTED
d=tempfile.mkdtemp(prefix="att_e_"); init(d)
write(d,"judge_x.py",J); write(d,"smoke_x.py",H); sh(["git","add","."], d); sh(["git","commit","-qm","lock"], d); sh(["git","tag","study-e-lock"], d)
rec=ovp_attest.build_attestation(d,"study-e-lock","smoke_x.py","2026-06-10T00:00:00Z")
rec["claim"]["non_execution"]="VERIFIABLE"                                               # forge over-claim
make_attest_tag(d, rec, "study-e-harness-attest", "study-e-lock")
rep=ovp_attest.verify_attestation(d,"study-e-harness-attest")
check("E non_execution over-claim CONTRADICTED (claim-scope guard)",
      rep["checks"]["claim_scope"].startswith("CONTRADICTED") and not rep["ok"])
shutil.rmtree(d)

print("\n%d/%d attestation checks passed" % (sum(R), len(R)))
sys.exit(0 if all(R) else 1)
