"""
ovp_guard.py - OVP v0.2 reference template: sealed-run self-guard + chain guards (rev2).

rev2 closes cold-pass-A finding 1 (demonstrated fail-open): H1 now verifies EVERY source file on
the sealed compute path - the judge, the shared compute-core, and the guard module itself - not
just the judge's blob. An accidental post-lock edit to any of them now refuses. This satisfies
the spec's sec 1 self-containment-OR-cover-every-import rule by the *cover* branch.

Accident-prevention scope (R-1): a forged tag, a deleted guard, or a SHA-1 collision defeat it.
"""
import hashlib
import os
import subprocess
import sys


class GuardRefusal(Exception):
    """Raised to REFUSE, BEFORE the sealed quantity is ever computed."""


def _git(args, cwd):
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", "git-binary-absent"
    except Exception as e:  # defensive; still fail-closed
        return 1, "", "git-exec-error:%r" % (e,)


def assert_locked_or_refuse(lock_tag, sealed_sources, self_path):
    """H1 self-guard. Returns the judge's verified OID, or raises GuardRefusal.

    lock_tag       : constant PINNED in the locked judge bytes (never derived from __file__).
    sealed_sources : dict {repo_relative_path: absolute_file_to_hash} covering EVERY source file
                     on the sealed compute path - the judge, the shared compute-core, the guard,
                     and any other locked module imported before/at sealed compute. Pin this
                     explicitly in the judge (a lint can assert it covers all sealed-path imports).
                     The repo-relative path selects the expected blob + filter; the absolute path
                     (e.g. module.__file__) is the actually-loaded bytes hashed - so a modified
                     copy refuses while a byte-identical relocation passes.
    self_path      : the running judge's path (used to discover the repo root).

    FAIL-CLOSED on every git-error path. Refuses unless ALL sealed sources match.

    Bootstrap note (cold-pass-A reader #2): ovp_guard.py is itself in sealed_sources and verifies
    its own ON-DISK bytes, but it is already imported (running) when it does so. An ACCIDENTAL edit
    is still caught - the running code hashes the edited on-disk file and sees the mismatch. A
    DELIBERATE edit that disables the check is R-1 tamper, out of model. Empty-OID and path-absent
    git results both fall to the `not expected_oid` / `rc != 0` refuse branches above.
    """
    if not sealed_sources:
        raise GuardRefusal("REFUSE: empty sealed_sources (the judge must enumerate its sealed-path files)")
    start_dir = os.path.dirname(os.path.abspath(self_path)) or "."
    rc, repo_root, err = _git(["rev-parse", "--show-toplevel"], start_dir)
    if rc != 0 or not repo_root:
        raise GuardRefusal("REFUSE: not in a git work tree (%s)" % (err or "no .git/git",))

    judge_oid = None
    for rel_path, abs_file in sorted(sealed_sources.items()):
        rc, expected_oid, err = _git(["rev-parse", "--verify", "%s:%s" % (lock_tag, rel_path)], repo_root)
        if rc != 0 or not expected_oid:
            raise GuardRefusal("REFUSE: cannot resolve %s:%s (%s)" % (lock_tag, rel_path, err or "tag/path missing"))
        rc, working_oid, err = _git(["hash-object", "--path", rel_path, "--", os.path.abspath(abs_file)], repo_root)
        if rc != 0 or not working_oid:
            raise GuardRefusal("REFUSE: cannot hash %s (%s)" % (rel_path, err or "hash-object failed",))
        if working_oid != expected_oid:
            raise GuardRefusal("REFUSE: %s bytes != %s blob (expected %s, got %s)"
                               % (rel_path, lock_tag, expected_oid[:12], working_oid[:12]))
        sys.stderr.write("[ovp-guard] verified %s:%s == %s\n" % (lock_tag, rel_path, working_oid))
        try:
            is_judge = os.path.exists(abs_file) and os.path.samefile(abs_file, self_path)
        except OSError:
            is_judge = False
        if is_judge:
            judge_oid = working_oid
    sys.stderr.write("[ovp-guard] LOCKED ok: all %d sealed-path sources verified\n" % len(sealed_sources))
    return judge_oid


def output_exists_or_refuse(out_path):
    """Single-execution: refuse a silent SAME-OUTPUT re-run (a different --out falls back to the
    single-execution rule; a crashed run is amended under a NEW lock tag)."""
    if os.path.exists(out_path):
        raise GuardRefusal("REFUSE: output %s exists (single-execution; amend under a NEW lock tag)" % out_path)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_input_hashes(expected, allow_empty=False):
    """Right-data guard. `expected` = {path: sha256}, hashes PINNED in the guarded blob. rev2:
    refuses an EMPTY expected-set unless allow_empty=True, so a study that forgets to populate it
    fails closed instead of silently skipping the check (cold-pass-A secondary finding)."""
    if not expected and not allow_empty:
        raise GuardRefusal("REFUSE: empty input-hash set (populate EXPECTED_INPUT_SHA256 or pass allow_empty=True)")
    for path, want in expected.items():
        if not os.path.exists(path):
            raise GuardRefusal("REFUSE: input %s absent" % path)
        got = _sha256(path)
        if got != want:
            raise GuardRefusal("REFUSE: input %s sha256 %s != pinned %s" % (path, got[:12], want[:12]))


# --- B2: the harness's deny-by-default closed-world surface (rev2: IO-closed, not just open) ----
# rev2 widens the audit coverage past `open`: directory enumeration, network, subprocess, and exec
# are denied outright during the data phase (a synthetic generator does none of them). C-level
# libc IO in an arbitrary extension remains unprovable by construction (R-1 reference-suite
# assertion); numpy's own readers DO raise the `open` event and are covered.
_io_allow = None  # None => inactive; set => only these absolute real paths may be opened
# DENYLIST of spawn/network/enumeration audit events. NOTE (cold-pass-A reader #4): a denylist
# can never be exhaustive (the spec says so) - os.system was a demonstrated hole, now closed, but
# the GUARANTEE is the `open` allowlist below; spawn/network denial is best-effort defense-in-depth,
# and the real closure for spawn/network exfiltration is the operator's external sandbox (no-network,
# restricted process) for the canonical run.
_DENY_EVENTS = ("os.listdir", "os.scandir", "socket.connect", "socket.getaddrinfo",
                "subprocess.Popen", "os.exec", "os.posix_spawn", "os.posix_spawnp",
                "os.system", "os.popen", "os.spawnv", "shutil.copyfile")


def _audit(event, args):
    if _io_allow is None:
        return
    if event == "open":
        try:
            ap = os.path.realpath(args[0])
        except Exception:
            ap = str(args[0])
        if ap not in _io_allow:
            raise GuardRefusal("REFUSE: closed-world harness opened %r (not in the pinned allowlist)" % (args[0],))
    elif event in _DENY_EVENTS:
        raise GuardRefusal("REFUSE: closed-world harness used %s (denied in the data phase)" % event)


sys.addaudithook(_audit)


class closed_world_io:
    """Context manager for the harness DATA phase. Inside: the ONLY paths open()-able are the
    pinned fixtures, and enumeration/network/subprocess/exec are denied. Libraries must be WARMED
    before entering (lazy imports open .pyc files). Deny-by-default. Note: process-global, not
    thread-local - concurrent code during the block is also restricted (safe)."""
    def __init__(self, *fixture_paths):
        self.allow = frozenset(os.path.realpath(p) for p in fixture_paths)

    def __enter__(self):
        global _io_allow
        _io_allow = self.allow
        return self

    def __exit__(self, *exc):
        global _io_allow
        _io_allow = None
        return False
