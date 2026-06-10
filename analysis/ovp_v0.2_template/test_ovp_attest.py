"""Execution tests for ovp_attest.py (rev2): tiers, claim-scope, binding cross-check, honest
source-synthetic label (no rubber-stamp), tamper detection."""
import json, os, shutil, subprocess, tempfile, sys
import ovp_attest
def sh(a,cwd,env=None):
    e=dict(os.environ); e.update(env or {}); return subprocess.run(a,cwd=cwd,capture_output=True,text=True,env=e)
def at(d): return {"GIT_AUTHOR_DATE":d,"GIT_COMMITTER_DATE":d}
def init(d): sh(["git","init","-q"],d); sh(["git","config","user.email","t@t"],d); sh(["git","config","user.name","t"],d)
def w(d,n,c): open(os.path.join(d,n),"w").write(c)
def mk_tag(d,rec,tag,commit): sh(["git","tag","-a",tag,commit,"-m",json.dumps(rec,indent=2)],d)
R=[]; 
def check(n,c): R.append(bool(c)); print(("  PASS " if c else "  FAIL ")+n)
H="smoke_x.py\n# synthetic-only harness\n"; J="judge_x.py\n# sealed\n"

# A anchored -> proof-grade, anchoring VERIFIED, claim_scope well-formed, binding VERIFIED, ok
d=tempfile.mkdtemp(prefix="att_a_"); init(d); w(d,"smoke_x.py",H); w(d,"judge_x.py",J)
sh(["git","add","smoke_x.py","judge_x.py"],d); sh(["git","commit","-qm","lock"],d,at("2026-06-01T00:00:00")); sh(["git","tag","study-a-lock"],d)
rec=ovp_attest.build_attestation(d,"study-a-lock","smoke_x.py","2026-06-10T00:00:00Z"); mk_tag(d,rec,"a-attest","study-a-lock")
rep=ovp_attest.verify_attestation(d,"a-attest")
check("A anchored: anchoring VERIFIED, binding VERIFIED, claim_scope well-formed, ok",
      rec["grade"]=="proof-grade" and rep["checks"]["anchoring"].startswith("VERIFIED")
      and rep["checks"]["binding"].startswith("VERIFIED") and rep["checks"]["claim_scope"].startswith("well-formed") and rep["ok"]); shutil.rmtree(d)

# B unanchored grandfathered (harness after lock) -> attestation-grade, temporal NOT-before, ok
d=tempfile.mkdtemp(prefix="att_b_"); init(d); w(d,"judge_x.py",J)
sh(["git","add","judge_x.py"],d); sh(["git","commit","-qm","lock"],d,at("2026-06-01T00:00:00")); sh(["git","tag","study-b-lock"],d)
w(d,"smoke_x.py",H); sh(["git","add","smoke_x.py"],d); sh(["git","commit","-qm","rec"],d,at("2026-06-05T00:00:00"))
rec=ovp_attest.build_attestation(d,"study-b-lock","smoke_x.py","2026-06-10T00:00:00Z"); mk_tag(d,rec,"b-attest","study-b-lock")
rep=ovp_attest.verify_attestation(d,"b-attest")
check("B unanchored: attestation-grade, temporal NOT-before-lock, binding VERIFIED, ok",
      rec["grade"]=="attestation-grade" and "NOT before" in rep["checks"]["temporal_bound"] and rep["checks"]["binding"].startswith("VERIFIED") and rep["ok"]); shutil.rmtree(d)

# C unanchored, temporal HOLDS
d=tempfile.mkdtemp(prefix="att_c_"); init(d)
w(d,"smoke_x.py",H); sh(["git","add","smoke_x.py"],d); sh(["git","commit","-qm","early"],d,at("2026-05-01T00:00:00"))
sh(["git","rm","-q","smoke_x.py"],d); w(d,"judge_x.py",J); sh(["git","add","judge_x.py"],d); sh(["git","commit","-qm","lock"],d,at("2026-06-01T00:00:00")); sh(["git","tag","study-c-lock"],d)
w(d,"smoke_x.py",H)
rec=ovp_attest.build_attestation(d,"study-c-lock","smoke_x.py","2026-06-10T00:00:00Z"); mk_tag(d,rec,"c-attest","study-c-lock")
rep=ovp_attest.verify_attestation(d,"c-attest")
check("C unanchored, temporal-bound HOLDS (in history at/before lock)",
      rec["temporal_bound"]["present_at_or_before_lock_date"] is True and "at/before lock date" in rep["checks"]["temporal_bound"]); shutil.rmtree(d)

# D forged anchored -> CONTRADICTED
d=tempfile.mkdtemp(prefix="att_d_"); init(d); w(d,"judge_x.py",J); sh(["git","add","judge_x.py"],d); sh(["git","commit","-qm","lock"],d); sh(["git","tag","study-d-lock"],d); w(d,"smoke_x.py",H)
rec=ovp_attest.build_attestation(d,"study-d-lock","smoke_x.py","2026-06-10T00:00:00Z"); rec["anchoring"]="anchored"; rec["grade"]="proof-grade"; mk_tag(d,rec,"d-attest","study-d-lock")
rep=ovp_attest.verify_attestation(d,"d-attest")
check("D forged-anchored CONTRADICTED", rep["checks"]["anchoring"].startswith("CONTRADICTED") and not rep["ok"]); shutil.rmtree(d)

# E non_execution over-claim -> CONTRADICTED
d=tempfile.mkdtemp(prefix="att_e_"); init(d); w(d,"judge_x.py",J); w(d,"smoke_x.py",H); sh(["git","add","."],d); sh(["git","commit","-qm","lock"],d); sh(["git","tag","study-e-lock"],d)
rec=ovp_attest.build_attestation(d,"study-e-lock","smoke_x.py","2026-06-10T00:00:00Z"); rec["claim"]["non_execution"]="VERIFIABLE"; mk_tag(d,rec,"e-attest","study-e-lock")
rep=ovp_attest.verify_attestation(d,"e-attest")
check("E non_execution over-claim CONTRADICTED", rep["checks"]["claim_scope"].startswith("CONTRADICTED") and not rep["ok"]); shutil.rmtree(d)

# F binding tamper: record sha256 != actual blob -> CONTRADICTED (rev2 finding-3 cross-check)
d=tempfile.mkdtemp(prefix="att_f_"); init(d); w(d,"judge_x.py",J); w(d,"smoke_x.py",H); sh(["git","add","."],d); sh(["git","commit","-qm","lock"],d); sh(["git","tag","study-f-lock"],d)
rec=ovp_attest.build_attestation(d,"study-f-lock","smoke_x.py","2026-06-10T00:00:00Z"); rec["harness_sha256"]="0"*64; mk_tag(d,rec,"f-attest","study-f-lock")
rep=ovp_attest.verify_attestation(d,"f-attest")
check("F binding tamper (sha256 != blob) CONTRADICTED", rep["checks"]["binding"].startswith("CONTRADICTED") and not rep["ok"]); shutil.rmtree(d)

# G the reader's probe: a candidate-READING harness is NOT rubber-stamped as synthetic (honest label)
d=tempfile.mkdtemp(prefix="att_g_"); init(d)
w(d,"smoke_x.py",'open("/secret/candidate_labels.npz","rb")\n'); w(d,"judge_x.py",J); sh(["git","add","."],d); sh(["git","commit","-qm","lock"],d); sh(["git","tag","study-g-lock"],d)
rec=ovp_attest.build_attestation(d,"study-g-lock","smoke_x.py","2026-06-10T00:00:00Z"); mk_tag(d,rec,"g-attest","study-g-lock")
rep=ovp_attest.verify_attestation(d,"g-attest")
honest = ("NOT machine-confirmed" in rep["checks"]["source_synthetic"]) and ("VERIFIED" not in rep["checks"]["source_synthetic"])
check("G candidate-reading harness: source_synthetic label HONEST (not rubber-stamped 'VERIFIED')", honest); shutil.rmtree(d)

# H forged grade on HONEST anchoring: unanchored record mislabeled proof-grade -> grade CONTRADICTED (reader #2)
d=tempfile.mkdtemp(prefix="att_h_"); init(d); w(d,"judge_x.py",J); sh(["git","add","judge_x.py"],d); sh(["git","commit","-qm","lock"],d); sh(["git","tag","study-h-lock"],d); w(d,"smoke_x.py",H)
rec=ovp_attest.build_attestation(d,"study-h-lock","smoke_x.py","2026-06-10T00:00:00Z")  # legit unanchored/attestation-grade
rec["grade"]="proof-grade"  # forge the grade while leaving anchoring honestly 'unanchored'
mk_tag(d,rec,"h-attest","study-h-lock"); rep=ovp_attest.verify_attestation(d,"h-attest")
check("H forged grade (unanchored mislabeled proof-grade) CONTRADICTED", rep["checks"]["grade"].startswith("CONTRADICTED") and not rep["ok"]); shutil.rmtree(d)

print("\n%d/%d attestation checks passed"%(sum(R),len(R))); sys.exit(0 if all(R) else 1)
