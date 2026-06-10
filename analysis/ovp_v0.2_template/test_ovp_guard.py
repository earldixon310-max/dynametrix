"""Execution tests for ovp_guard.py (rev2). Each builds a real temp git repo."""
import os, shutil, socket, subprocess, sys, tempfile, hashlib
import ovp_guard
from ovp_guard import assert_locked_or_refuse, GuardRefusal, output_exists_or_refuse, \
    verify_input_hashes, closed_world_io

JUDGE="judge_x.py"; TAG="study-x-lock"
SRC=b"# judge_x.py\nLOCK_TAG='study-x-lock'\nLOCKED_PATH='judge_x.py'\nprint('sealed')\n"

def sh(a,cwd,**k): return subprocess.run(a,cwd=cwd,capture_output=True,text=True,**k)
def make_repo(content=SRC, tag=True, attrs=None, autocrlf=None):
    d=tempfile.mkdtemp(prefix="ovp_repo_"); sh(["git","init","-q"],d)
    sh(["git","config","user.email","t@t"],d); sh(["git","config","user.name","t"],d)
    if autocrlf is not None: sh(["git","config","core.autocrlf",autocrlf],d)
    if attrs is not None: open(os.path.join(d,".gitattributes"),"w").write(attrs); sh(["git","add",".gitattributes"],d)
    p=os.path.join(d,JUDGE); open(p,"wb").write(content); sh(["git","add",JUDGE],d); sh(["git","commit","-qm","lock"],d)
    if tag: sh(["git","tag",TAG],d)
    return d,p
def ss(p): return {JUDGE: p}                       # single-file sealed_sources for judge-only tests
def refuses(fn,*a,**k):
    try: fn(*a,**k); return False
    except GuardRefusal: return True
R=[]
def check(n,c): R.append(bool(c)); print(("  PASS " if c else "  FAIL ")+n)

# 1 locked+identical PASSES (fixpoint)
d,p=make_repo(); oid=assert_locked_or_refuse(TAG,ss(p),p); check("1 locked+identical PASSES", isinstance(oid,str) and len(oid)==40); shutil.rmtree(d)
# 2 no-tag REFUSES
d,p=make_repo(tag=False); check("2 no-tag REFUSES", refuses(assert_locked_or_refuse,TAG,ss(p),p)); shutil.rmtree(d)
# 3 modified-working REFUSES
d,p=make_repo(); open(p,"ab").write(b"# x\n"); check("3 modified-working REFUSES", refuses(assert_locked_or_refuse,TAG,ss(p),p)); shutil.rmtree(d)
# 4 no-.git REFUSES
d=tempfile.mkdtemp(); p=os.path.join(d,JUDGE); open(p,"wb").write(SRC); check("4 no-.git REFUSES (fail-closed)", refuses(assert_locked_or_refuse,TAG,ss(p),p)); shutil.rmtree(d)
# 5 git-binary-absent REFUSES
d,p=make_repo(); _pp=os.environ.get("PATH",""); empty=tempfile.mkdtemp(); os.environ["PATH"]=empty
try: r=refuses(assert_locked_or_refuse,TAG,ss(p),p)
finally: os.environ["PATH"]=_pp
check("5 git-binary-absent REFUSES (fail-closed)", r); shutil.rmtree(d); shutil.rmtree(empty)
# 6 autocrlf: filter-aware PASSES, and raw (no-filter) oid DIFFERS from the blob (now ASSERTED)
d,p=make_repo(autocrlf="true"); open(p,"wb").write(SRC.replace(b"\n",b"\r\n"))
blob_oid=sh(["git","rev-parse","%s:%s"%(TAG,JUDGE)],d).stdout.strip()
raw_oid=sh(["git","hash-object","--no-filters","--",p],d).stdout.strip()
passes=isinstance(assert_locked_or_refuse(TAG,ss(p),p),str) if not refuses(assert_locked_or_refuse,TAG,ss(p),p) else False
check("6 autocrlf: filter-aware PASSES AND raw-hash DIFFERS (raw would false-refuse)", passes and raw_oid!=blob_oid and raw_oid and blob_oid); shutil.rmtree(d)
# 7 -text pin PASSES
d,p=make_repo(attrs="judge_x.py -text\n"); check("7 -text-pinned PASSES", isinstance(assert_locked_or_refuse(TAG,ss(p),p),str)); shutil.rmtree(d)
# 8 moved-identical PASSES, moved-modified REFUSES
d,p=make_repo(); moved=os.path.join(os.path.dirname(p),"moved.py"); shutil.copyfile(p,moved)
ok_m=isinstance(assert_locked_or_refuse(TAG,{JUDGE:moved},moved),str); open(moved,"ab").write(b"#evil\n")
check("8 moved-identical PASSES; moved-modified REFUSES", ok_m and refuses(assert_locked_or_refuse,TAG,{JUDGE:moved},moved)); shutil.rmtree(d)
# 9 output-exists
d=tempfile.mkdtemp(); o=os.path.join(d,"r.json"); ok1=not refuses(output_exists_or_refuse,o); open(o,"w").write("{}")
check("9 output-exists: first PERMITS, re-run REFUSES", ok1 and refuses(output_exists_or_refuse,o)); shutil.rmtree(d)
# 10 input-hash match/mismatch
d=tempfile.mkdtemp(); fx=os.path.join(d,"B.npy"); open(fx,"wb").write(b"\x01\x02data"); good=hashlib.sha256(open(fx,'rb').read()).hexdigest()
check("10 input-hash: match PERMITS, mismatch REFUSES", (not refuses(verify_input_hashes,{fx:good})) and refuses(verify_input_hashes,{fx:"0"*64})); shutil.rmtree(d)
# 11 closed-world: fixture OK, absolute-path open REFUSES
d=tempfile.mkdtemp(); fx=os.path.join(d,"s.npy"); open(fx,"wb").write(b"syn"); fok=False; ablk=False
with closed_world_io(fx):
    try: open(fx,"rb").read(); fok=True
    except GuardRefusal: pass
    try: open("/etc/hostname","rb").read()
    except GuardRefusal: ablk=True
check("11 closed-world: fixture OK, abspath open REFUSES", fok and ablk); shutil.rmtree(d)
# 12 boundary: locked .gitattributes tracked, info/attributes out-of-set
d,p=make_repo(attrs="judge_x.py -text\n"); open(os.path.join(d,".git","info","attributes"),"w").write("judge_x.py text=auto\n")
tr=sh(["git","ls-files"],d).stdout.split(); check("12 boundary: .gitattributes tracked, info/attributes out-of-set", ".gitattributes" in tr and ".git/info/attributes" not in tr); shutil.rmtree(d)
# 13 empty input-hash set REFUSES (rev2 fail-closed)
check("13 empty input-hash set REFUSES (fail-closed)", refuses(verify_input_hashes,{}))
# 14 widened closed-world: directory enumeration AND network REFUSE (rev2, cold-pass-A finding 2)
d=tempfile.mkdtemp(); fx=os.path.join(d,"s.npy"); open(fx,"wb").write(b"syn"); ls_blk=False; net_blk=False
with closed_world_io(fx):
    try: os.listdir(d)
    except GuardRefusal: ls_blk=True
    try: socket.socket().connect(("127.0.0.1",9))
    except GuardRefusal: net_blk=True
    except OSError: net_blk=False   # if it got past the hook to a real connect error, that's a leak
check("14 widened closed-world: listdir REFUSES and socket REFUSES", ls_blk and net_blk); shutil.rmtree(d)

# 15 widened closed-world: subprocess REFUSES (backs the README subprocess/exec claim)
import subprocess as _sp
d=tempfile.mkdtemp(); fx=os.path.join(d,"s.npy"); open(fx,"wb").write(b"syn"); sp_blk=False
with closed_world_io(fx):
    try: _sp.Popen(["true"])
    except GuardRefusal: sp_blk=True
    except Exception: sp_blk=False
check("15 widened closed-world: subprocess REFUSES", sp_blk); shutil.rmtree(d)
# 16 tag exists but LOCKED_PATH absent from the tagged tree -> REFUSE (distinct from moved-file)
d,p=make_repo(); absent=os.path.join(os.path.dirname(p),"not_in_tree.py"); open(absent,"wb").write(SRC)
check("16 path-absent-from-tagged-tree REFUSES", refuses(assert_locked_or_refuse,TAG,{"not_in_tree.py":absent},p)); shutil.rmtree(d)

# 17 widened closed-world: os.system REFUSES (cold-pass-A reader #4 demonstrated exploit, now closed)
d=tempfile.mkdtemp(); fx=os.path.join(d,"s.npy"); open(fx,"wb").write(b"syn"); sys_blk=False; out=os.path.join(d,"x")
with closed_world_io(fx):
    try: os.system("echo leak > %s" % out)
    except GuardRefusal: sys_blk=True
leaked = os.path.exists(out)
check("17 widened closed-world: os.system REFUSES (no child exfiltration)", sys_blk and not leaked); shutil.rmtree(d)

print("\n%d/%d checks passed"%(sum(R),len(R))); sys.exit(0 if all(R) else 1)
