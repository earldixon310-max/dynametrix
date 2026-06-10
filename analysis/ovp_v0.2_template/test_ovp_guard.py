"""Dependency-light execution tests for ovp_guard.py. Each builds a real temp git repo and
asserts the guard's behavior. Run: python3 test_ovp_guard.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import hashlib

import ovp_guard
from ovp_guard import assert_locked_or_refuse, GuardRefusal, output_exists_or_refuse, \
    verify_input_hashes, closed_world_io

JUDGE = "judge_x.py"
TAG = "study-x-lock"
SRC = b"# judge_x.py\nLOCK_TAG='study-x-lock'\nLOCKED_PATH='judge_x.py'\nprint('sealed-compute')\n"


def sh(args, cwd, **kw):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kw)


def make_repo(content=SRC, tag=True, attrs=None, autocrlf=None):
    d = tempfile.mkdtemp(prefix="ovp_repo_")
    sh(["git", "init", "-q"], d)
    sh(["git", "config", "user.email", "t@t"], d); sh(["git", "config", "user.name", "t"], d)
    if autocrlf is not None:
        sh(["git", "config", "core.autocrlf", autocrlf], d)
    if attrs is not None:
        open(os.path.join(d, ".gitattributes"), "w").write(attrs)
        sh(["git", "add", ".gitattributes"], d)
    p = os.path.join(d, JUDGE)
    open(p, "wb").write(content)
    sh(["git", "add", JUDGE], d)
    sh(["git", "commit", "-qm", "lock"], d)
    if tag:
        sh(["git", "tag", TAG], d)
    return d, p


def refuses(fn, *a, **k):
    try:
        fn(*a, **k)
        return False
    except GuardRefusal:
        return True


RESULTS = []
def check(name, cond):
    RESULTS.append((name, bool(cond)))
    print(("  PASS " if cond else "  FAIL ") + name)


# 1. locked + byte-identical -> computes (returns OID); fixpoint: tag named in bytes, OID resolved dynamically
d, p = make_repo()
oid = assert_locked_or_refuse(TAG, JUDGE, p)
check("1 locked+identical PASSES (fixpoint closed)", isinstance(oid, str) and len(oid) == 40)
shutil.rmtree(d)

# 2. no tag (pre-lock) -> refuse
d, p = make_repo(tag=False)
check("2 no-tag (pre-lock) REFUSES", refuses(assert_locked_or_refuse, TAG, JUDGE, p))
shutil.rmtree(d)

# 3. tag exists but working bytes modified after lock -> refuse
d, p = make_repo()
open(p, "ab").write(b"# tampered\n")
check("3 modified-working REFUSES", refuses(assert_locked_or_refuse, TAG, JUDGE, p))
shutil.rmtree(d)

# 4. not a git work tree -> refuse (fail-closed)
d = tempfile.mkdtemp(prefix="ovp_nogit_"); p = os.path.join(d, JUDGE); open(p, "wb").write(SRC)
check("4 no-.git REFUSES (fail-closed)", refuses(assert_locked_or_refuse, TAG, JUDGE, p))
shutil.rmtree(d)

# 5. git binary absent -> refuse (fail-closed). Simulate via PATH with no git.
d, p = make_repo()
_path = os.environ.get("PATH", "")
empty = tempfile.mkdtemp(prefix="ovp_nopath_")
os.environ["PATH"] = empty
try:
    r = refuses(assert_locked_or_refuse, TAG, JUDGE, p)
finally:
    os.environ["PATH"] = _path
check("5 git-binary-absent REFUSES (fail-closed)", r)
shutil.rmtree(d); shutil.rmtree(empty)

# 6. autocrlf=true, blob is LF, working tree CRLF: filter-aware hash-object MATCHES (raw byte hash would NOT)
d, p = make_repo(autocrlf="true")
open(p, "wb").write(SRC.replace(b"\n", b"\r\n"))  # working tree CRLF
raw_differs = hashlib.sha1(b"blob %d\0" % len(open(p,'rb').read()) + open(p,'rb').read()).hexdigest()  # not the blob
passes = False
try:
    assert_locked_or_refuse(TAG, JUDGE, p); passes = True
except GuardRefusal:
    passes = False
check("6 autocrlf CRLF-worktree PASSES via filter-aware compare", passes)
shutil.rmtree(d)

# 7. -text pin in locked .gitattributes -> deterministic identity, passes
d, p = make_repo(attrs="judge_x.py -text\n")
check("7 -text-pinned path PASSES (deterministic)", isinstance(assert_locked_or_refuse(TAG, JUDGE, p), str))
shutil.rmtree(d)

# 8. moved-but-byte-identical copy PASSES; moved-AND-modified copy REFUSES
d, p = make_repo()
moved = os.path.join(os.path.dirname(p), "moved_copy.py"); shutil.copyfile(p, moved)
ok_moved = isinstance(assert_locked_or_refuse(TAG, JUDGE, moved), str)  # self_path=moved, hashes its bytes; identical -> ok
open(moved, "ab").write(b"# evil\n")
ref_moved_mod = refuses(assert_locked_or_refuse, TAG, JUDGE, moved)
check("8 moved-identical PASSES; moved-modified REFUSES (hash running bytes)", ok_moved and ref_moved_mod)
shutil.rmtree(d)

# 9. output-exists single-execution guard
d = tempfile.mkdtemp(prefix="ovp_out_"); outp = os.path.join(d, "r.json")
ok_first = not refuses(output_exists_or_refuse, outp)  # absent -> permits
open(outp, "w").write("{}")
ref_second = refuses(output_exists_or_refuse, outp)    # present -> refuse
check("9 output-exists: first PERMITS, re-run REFUSES", ok_first and ref_second)
shutil.rmtree(d)

# 10. runtime input-hash check (identity-covered: hashes pinned by caller)
d = tempfile.mkdtemp(prefix="ovp_in_"); fx = os.path.join(d, "B.npy"); open(fx, "wb").write(b"\x01\x02\x03data")
good = hashlib.sha256(open(fx,'rb').read()).hexdigest()
ok_match = not refuses(verify_input_hashes, {fx: good})
ref_bad = refuses(verify_input_hashes, {fx: "0"*64})
check("10 input-hash: match PERMITS, mismatch REFUSES", ok_match and ref_bad)
shutil.rmtree(d)

# 11. closed-world harness IO: fixture OK; absolute-path read REFUSES
d = tempfile.mkdtemp(prefix="ovp_cw_"); fx = os.path.join(d, "synth.npy"); open(fx, "wb").write(b"synthetic")
fixture_ok = False; abspath_blocked = False
with closed_world_io(fx):
    try:
        open(fx, "rb").read(); fixture_ok = True
    except GuardRefusal:
        fixture_ok = False
    try:
        open("/etc/hostname", "rb").read()      # absolute-path peek attempt
        abspath_blocked = False
    except GuardRefusal:
        abspath_blocked = True
# guard inactive again outside the block:
_ = open("/etc/hostname", "rb").read() if os.path.exists("/etc/hostname") else b""
check("11 closed-world: fixture OK, absolute-path read REFUSES", fixture_ok and abspath_blocked)
shutil.rmtree(d)

# 12. hostile info/attributes is OUTSIDE the locked set (accident-model boundary, R-1).
# Demonstrate the boundary: a filter injected via .git/info/attributes is not covered by the
# locked .gitattributes -> documents that "-text closes it under the accident model, not by construction".
d, p = make_repo(attrs="judge_x.py -text\n")
open(os.path.join(d, ".git", "info", "attributes"), "w").write("judge_x.py text=auto\n")
# locked .gitattributes is in the tree (auditable); info/attributes is not tracked:
tracked = sh(["git", "ls-files"], d).stdout.split()
boundary = (".gitattributes" in tracked) and (".git/info/attributes" not in tracked)
check("12 boundary: locked .gitattributes tracked, info/attributes out-of-set (R-1 tamper)", boundary)
shutil.rmtree(d)

print("\n%d/%d checks passed" % (sum(1 for _, c in RESULTS if c), len(RESULTS)))
sys.exit(0 if all(c for _, c in RESULTS) else 1)
