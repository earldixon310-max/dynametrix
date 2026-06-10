"""End-to-end integration: smoke harness pre-lock, and a concrete judge across the lock boundary."""
import os, shutil, subprocess, tempfile, sys

def sh(args, cwd): return subprocess.run(args, cwd=cwd, capture_output=True, text=True)
R=[]
def check(n,c): R.append(c); print(("  PASS " if c else "  FAIL ")+n)

HERE=os.path.dirname(os.path.abspath(__file__))

# 13. smoke harness runs pre-lock, exit 0, writes no results-shaped (.json) output
d=tempfile.mkdtemp(prefix="ovp_smoke_")
for f in ("ovp_guard.py","compute_core.py","smoke_template.py"): shutil.copy(os.path.join(HERE,f), d)
r=sh(["python3","smoke_template.py"], d)
check("13 smoke pre-lock: exit 0, '[smoke] OK', no .json written",
      r.returncode==0 and "[smoke] OK" in r.stderr and not any(x.endswith(".json") for x in os.listdir(d)))
shutil.rmtree(d)

# 14. concrete judge: REFUSES pre-lock, COMPUTES once the named tag exists (end-to-end positive path)
d=tempfile.mkdtemp(prefix="ovp_judge_")
for f in ("ovp_guard.py","compute_core.py"): shutil.copy(os.path.join(HERE,f), d)
open(os.path.join(d,"judge_y.py"),"w").write(
"import os,sys,json\n"
"import numpy as np, numpy.random\n"
"import ovp_guard, compute_core\n"
"LOCK_TAG='study-y-lock'; LOCKED_PATH='judge_y.py'; OUT='out.json'\n"
"def main():\n"
"    try:\n"
"        ovp_guard.assert_locked_or_refuse(LOCK_TAG, LOCKED_PATH, os.path.abspath(__file__))\n"
"        ovp_guard.output_exists_or_refuse(OUT)\n"
"    except ovp_guard.GuardRefusal as e:\n"
"        sys.stderr.write(str(e)+'\\n'); sys.exit(2)\n"
"    rng=np.random.default_rng(7); n=200\n"
"    y=(rng.random(n)<0.5).astype(int); B=rng.random(n); C=np.clip(B+0.3*(y-0.5),0,1)\n"
"    D=compute_core.compute_sealed(B,y,C,seed=1)\n"
"    json.dump({'D':D}, open(OUT,'w')); sys.stderr.write('[judge] wrote\\n')\n"
"main()\n")
sh(["git","init","-q"], d); sh(["git","config","user.email","t@t"], d); sh(["git","config","user.name","t"], d)
sh(["git","add","ovp_guard.py","compute_core.py","judge_y.py"], d); sh(["git","commit","-qm","lock"], d)
r_pre=sh(["python3","judge_y.py"], d)                    # no tag yet -> refuse
pre_ok = r_pre.returncode==2 and not os.path.exists(os.path.join(d,"out.json"))
sh(["git","tag","study-y-lock"], d)                       # LOCK
r_post=sh(["python3","judge_y.py"], d)                    # now computes
post_ok = r_post.returncode==0 and os.path.exists(os.path.join(d,"out.json"))
check("14 judge end-to-end: pre-lock REFUSES(exit2,no out), post-lock COMPUTES(exit0,out written)", pre_ok and post_ok)
shutil.rmtree(d)

print("\n%d/%d integration checks passed" % (sum(R), len(R)))
sys.exit(0 if all(R) else 1)
