"""End-to-end integration (rev4): smoke pre-lock; the FULL closure chain in one judge across the
lock; and post-lock tamper of each sealed input must REFUSE (core, .gitattributes, input data)."""
import os, shutil, subprocess, tempfile, sys, hashlib
def sh(a,cwd): return subprocess.run(a,cwd=cwd,capture_output=True,text=True)
R=[]; 
def check(n,c): R.append(bool(c)); print(("  PASS " if c else "  FAIL ")+n)
HERE=os.path.dirname(os.path.abspath(__file__))

JUDGE_SRC=(
"import os,sys,json\n"
"import numpy as np, numpy.random\n"
"import ovp_guard, compute_core\n"
"LOCK_TAG='study-y-lock'; LOCKED_PATH='judge_y.py'; OUT='out.json'; INPUT='Bdata.bin'\n"
"SEALED_SOURCES={LOCKED_PATH:os.path.abspath(__file__),'compute_core.py':os.path.abspath(compute_core.__file__),'ovp_guard.py':os.path.abspath(ovp_guard.__file__),'.gitattributes':os.path.join(os.path.dirname(os.path.abspath(__file__)),'.gitattributes')}\n"
"EXPECTED_INPUT={INPUT:'__SHA__'}\n"
"def sealed_loader():\n"
"    open(INPUT,'rb').read()\n"
"    rng=np.random.default_rng(7); n=200; y=(rng.random(n)<0.5).astype(int); B=rng.random(n); C=np.clip(B+0.3*(y-0.5),0,1); return B,y,C\n"
"def main():\n"
"    try:\n"
"        ovp_guard.assert_locked_or_refuse(LOCK_TAG, SEALED_SOURCES, os.path.abspath(__file__))\n"
"        ovp_guard.output_exists_or_refuse(OUT)\n"
"        ovp_guard.verify_input_hashes(EXPECTED_INPUT)\n"
"    except ovp_guard.GuardRefusal as e:\n"
"        sys.stderr.write(str(e)+'\\n'); sys.exit(2)\n"
"    B,y,C=sealed_loader(); D=compute_core.compute_sealed(B,y,C,seed=1)\n"
"    json.dump({'D':D}, open(OUT,'w')); sys.stderr.write('[judge] wrote\\n')\n"
"main()\n")

# 15 smoke pre-lock
d=tempfile.mkdtemp(prefix="it_smoke_")
for f in ("ovp_guard.py","compute_core.py","smoke_template.py"): shutil.copy(os.path.join(HERE,f),d)
r=sh(["python3","smoke_template.py"],d)
check("15 smoke pre-lock: exit 0, no .json", r.returncode==0 and "[smoke] OK" in r.stderr and not any(x.endswith(".json") for x in os.listdir(d))); shutil.rmtree(d)

# build a locked study with the FULL sealed set: guard+core+.gitattributes+input+judge
d=tempfile.mkdtemp(prefix="it_full_")
for f in ("ovp_guard.py","compute_core.py"): shutil.copy(os.path.join(HERE,f),d)
open(os.path.join(d,".gitattributes"),"w").write("judge_y.py -text\ncompute_core.py -text\novp_guard.py -text\n")
open(os.path.join(d,"Bdata.bin"),"wb").write(b"\x01\x02\x03synthetic-input-bytes")
sha=hashlib.sha256(open(os.path.join(d,"Bdata.bin"),"rb").read()).hexdigest()
open(os.path.join(d,"judge_y.py"),"w").write(JUDGE_SRC.replace("__SHA__",sha))
sh(["git","init","-q"],d); sh(["git","config","user.email","t@t"],d); sh(["git","config","user.name","t"],d)
sh(["git","add","ovp_guard.py","compute_core.py",".gitattributes","Bdata.bin","judge_y.py"],d); sh(["git","commit","-qm","lock"],d)
def run(): return sh(["python3","judge_y.py"],d)
def reset_out():
    o=os.path.join(d,"out.json"); 
    if os.path.exists(o): os.remove(o)
r_pre=run(); pre_ok=r_pre.returncode==2 and not os.path.exists(os.path.join(d,"out.json"))
sh(["git","tag","study-y-lock"],d)
r_post=run(); post_ok=r_post.returncode==0 and os.path.exists(os.path.join(d,"out.json"))
check("16 FULL chain (H1x4 + output-exists + input-hash): pre-lock REFUSES, post-lock COMPUTES", pre_ok and post_ok)
# 17 post-lock core edit REFUSES
reset_out(); open(os.path.join(d,"compute_core.py"),"a").write("\ndef compute_sealed(*a,**k):\n    return 999.0\n")
r=run(); check("17 post-lock CORE edit REFUSES", r.returncode==2 and "REFUSE" in r.stderr and not os.path.exists(os.path.join(d,"out.json")))
sh(["git","checkout","--","compute_core.py"],d)   # restore
# 18 post-lock .gitattributes edit REFUSES (reader #3 blocker 2)
reset_out(); open(os.path.join(d,".gitattributes"),"a").write("*.bin binary\n")
r=run(); check("18 post-lock .gitattributes edit REFUSES (now in SEALED_SOURCES)", r.returncode==2 and "REFUSE" in r.stderr and not os.path.exists(os.path.join(d,"out.json")))
sh(["git","checkout","--",".gitattributes"],d)
# 19 post-lock INPUT tamper REFUSES (input-hash link of the chain)
reset_out(); open(os.path.join(d,"Bdata.bin"),"wb").write(b"SWAPPED-candidate-bytes")
r=run(); check("19 post-lock INPUT tamper REFUSES (input-hash)", r.returncode==2 and "REFUSE" in r.stderr and not os.path.exists(os.path.join(d,"out.json")))
# 20 post-lock edit of the GUARD MODULE itself REFUSES (H1 covers ovp_guard.py)
reset_out(); open(os.path.join(d,"ovp_guard.py"),"a").write("\n# accidental post-lock edit\n")
r=run(); check("20 post-lock ovp_guard.py edit REFUSES", r.returncode==2 and not os.path.exists(os.path.join(d,"out.json")))
sh(["git","checkout","--","ovp_guard.py"],d)
# 21 post-lock edit of the JUDGE itself REFUSES (H1 covers the judge file)
reset_out(); open(os.path.join(d,"judge_y.py"),"a").write("\n# accidental post-lock edit\n")
r=run(); check("21 post-lock judge_y.py edit REFUSES", r.returncode==2 and not os.path.exists(os.path.join(d,"out.json")))
sh(["git","checkout","--","judge_y.py"],d)
shutil.rmtree(d)

print("\n%d/%d integration checks passed"%(sum(R),len(R))); sys.exit(0 if all(R) else 1)
