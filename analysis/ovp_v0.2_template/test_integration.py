"""End-to-end integration (rev2): smoke pre-lock; judge across the lock; and the reproduced
cold-pass-A finding-1 probe - a post-lock edit to the shared core now REFUSES (was D=999.0)."""
import os, shutil, subprocess, tempfile, sys
def sh(a,cwd): return subprocess.run(a,cwd=cwd,capture_output=True,text=True)
R=[]; 
def check(n,c): R.append(bool(c)); print(("  PASS " if c else "  FAIL ")+n)
HERE=os.path.dirname(os.path.abspath(__file__))

JUDGE_SRC=(
"import os,sys,json\n"
"import numpy as np, numpy.random\n"
"import ovp_guard, compute_core\n"
"LOCK_TAG='study-y-lock'; LOCKED_PATH='judge_y.py'; OUT='out.json'\n"
"SEALED_SOURCES={LOCKED_PATH:os.path.abspath(__file__),'compute_core.py':os.path.abspath(compute_core.__file__),'ovp_guard.py':os.path.abspath(ovp_guard.__file__)}\n"
"def main():\n"
"    try:\n"
"        ovp_guard.assert_locked_or_refuse(LOCK_TAG, SEALED_SOURCES, os.path.abspath(__file__))\n"
"        ovp_guard.output_exists_or_refuse(OUT)\n"
"    except ovp_guard.GuardRefusal as e:\n"
"        sys.stderr.write(str(e)+'\\n'); sys.exit(2)\n"
"    rng=np.random.default_rng(7); n=200\n"
"    y=(rng.random(n)<0.5).astype(int); B=rng.random(n); C=np.clip(B+0.3*(y-0.5),0,1)\n"
"    D=compute_core.compute_sealed(B,y,C,seed=1)\n"
"    json.dump({'D':D}, open(OUT,'w')); sys.stderr.write('[judge] wrote\\n')\n"
"main()\n")

# 15. smoke harness runs pre-lock, exit 0, no .json
d=tempfile.mkdtemp(prefix="it_smoke_")
for f in ("ovp_guard.py","compute_core.py","smoke_template.py"): shutil.copy(os.path.join(HERE,f),d)
r=sh(["python3","smoke_template.py"],d)
check("15 smoke pre-lock: exit 0, '[smoke] OK', no .json", r.returncode==0 and "[smoke] OK" in r.stderr and not any(x.endswith(".json") for x in os.listdir(d)))
shutil.rmtree(d)

# 16+17. concrete judge across the lock, then post-lock CORE edit must REFUSE
d=tempfile.mkdtemp(prefix="it_judge_")
for f in ("ovp_guard.py","compute_core.py"): shutil.copy(os.path.join(HERE,f),d)
open(os.path.join(d,"judge_y.py"),"w").write(JUDGE_SRC)
sh(["git","init","-q"],d); sh(["git","config","user.email","t@t"],d); sh(["git","config","user.name","t"],d)
sh(["git","add","ovp_guard.py","compute_core.py","judge_y.py"],d); sh(["git","commit","-qm","lock"],d)
r_pre=sh(["python3","judge_y.py"],d)                                   # no tag -> refuse
pre_ok=r_pre.returncode==2 and not os.path.exists(os.path.join(d,"out.json"))
sh(["git","tag","study-y-lock"],d)                                     # LOCK
r_post=sh(["python3","judge_y.py"],d)                                  # computes
post_ok=r_post.returncode==0 and os.path.exists(os.path.join(d,"out.json"))
check("16 judge: pre-lock REFUSES, post-lock COMPUTES", pre_ok and post_ok)
# 17. reproduce finding 1: edit the SHARED CORE after lock -> must refuse (was a silent wrong-compute)
os.remove(os.path.join(d,"out.json"))
with open(os.path.join(d,"compute_core.py"),"a") as f: f.write("\ndef compute_sealed(*a,**k):\n    return 999.0\n")
r_tamper=sh(["python3","judge_y.py"],d)
check("17 post-lock CORE edit REFUSES (finding-1 closed: no out, exit 2)",
      r_tamper.returncode==2 and not os.path.exists(os.path.join(d,"out.json")) and "REFUSE" in r_tamper.stderr)
shutil.rmtree(d)

print("\n%d/%d integration checks passed"%(sum(R),len(R))); sys.exit(0 if all(R) else 1)
