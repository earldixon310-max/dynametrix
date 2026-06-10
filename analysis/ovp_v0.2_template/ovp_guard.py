"""
ovp_guard.py - OVP v0.2 reference template: the sealed-run self-guard and chain guards.

Implements docs/standards/OVP_v0.2_TEMPLATE_HARDENING_DRAFT.md (rev7). Every guarantee is
scoped to ACCIDENT-PREVENTION (R-1): a forged tag or an edited-out guard defeats it; that
residual is the signature/human-trust layer's job, explicitly disclaimed.

Pieces (the full closure chain adopts together, sec 2.5):
  H1  assert_locked_or_refuse  - compute the sealed quantity only if this study is locked,
                                 by git OBJECT identity, FAIL-CLOSED on every git-error path.
  re-run  output_exists_or_refuse - single-execution: refuse a silent same-output re-run.
  inputs  verify_input_hashes  - right-data: expected hashes are pinned in the guarded blob.
  B2  closed_world_io          - the harness's deny-by-default input surface (allowlist).
"""
import hashlib
import os
import subprocess
import sys


class GuardRefusal(Exception):
    """Raised to REFUSE. A judge lets this propagate to a top-level handler that exits non-zero
    BEFORE the sealed quantity is ever computed."""


def _git(args, cwd):
    """Run git; never raise. Returns (rc, stdout, stderr). git absent -> rc 127 (fail-closed)."""
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", "git-binary-absent"
    except Exception as e:  # pragma: no cover - defensive; still fail-closed
        return 1, "", "git-exec-error:%r" % (e,)


def assert_locked_or_refuse(lock_tag, locked_path, self_path):
    """H1 self-guard. Returns the verified blob OID, or raises GuardRefusal (refuse).

    lock_tag, locked_path : constants PINNED in the locked script bytes (never derived from
                            __file__). locked_path is repo-relative; it selects the expected
                            blob (LOCK_TAG:locked_path) and the filter set (--path).
    self_path             : the RUNNING script's path; its bytes are hashed, so a moved-AND-
                            modified copy refuses while a byte-identical relocation passes.

    FAIL-CLOSED on every git-error path: no git binary, no .git, tag missing, blob unresolved,
    working-file unhashable, or OID mismatch -> refuse. This is the only place a guard could
    wrongly COMPUTE, so every error path must refuse.
    """
    start_dir = os.path.dirname(os.path.abspath(self_path)) or "."
    rc, repo_root, err = _git(["rev-parse", "--show-toplevel"], start_dir)
    if rc != 0 or not repo_root:
        raise GuardRefusal("REFUSE: not in a git work tree (%s)" % (err or "no .git/git",))

    # Expected: blob recorded at the PINNED path in the named tag. OID resolved DYNAMICALLY,
    # never hard-coded (hard-coding reintroduces the fixpoint circularity).
    rc, expected_oid, err = _git(["rev-parse", "--verify", "%s:%s" % (lock_tag, locked_path)], repo_root)
    if rc != 0 or not expected_oid:
        raise GuardRefusal("REFUSE: cannot resolve %s:%s (%s)" % (lock_tag, locked_path, err or "tag/path missing"))

    # Working side: hash the RUNNING file through git's filters for the pinned path
    # (--path applies clean-filter + EOL per gitattributes; filter-aware, not a raw byte hash).
    rc, working_oid, err = _git(["hash-object", "--path", locked_path, "--", os.path.abspath(self_path)], repo_root)
    if rc != 0 or not working_oid:
        raise GuardRefusal("REFUSE: cannot hash working file (%s)" % (err or "hash-object failed",))

    if working_oid != expected_oid:
        raise GuardRefusal("REFUSE: working bytes != %s blob (expected %s, got %s)"
                           % (lock_tag, expected_oid[:12], working_oid[:12]))

    # Audit log: the tag + the verified code OID. NEVER the sealed value.
    sys.stderr.write("[ovp-guard] LOCKED ok: %s:%s == %s\n" % (lock_tag, locked_path, working_oid))
    return working_oid


def output_exists_or_refuse(out_path):
    """Single-execution guard. Refuse a silent SAME-OUTPUT re-run. Scope (honest): a re-run to a
    DIFFERENT --out path survives this and falls back to single-execution discipline (R-2)."""
    if os.path.exists(out_path):
        raise GuardRefusal("REFUSE: output %s exists (single-execution; a crashed run is amended "
                           "under a NEW lock tag, not silently re-run)" % out_path)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_input_hashes(expected):
    """Right-data guard. `expected` is {path: sha256} with the hashes PINNED in the guarded blob
    (identity-covered by H1), never read from an unverified ambient file. Refuse on any mismatch."""
    for path, want in expected.items():
        if not os.path.exists(path):
            raise GuardRefusal("REFUSE: input %s absent" % path)
        got = _sha256(path)
        if got != want:
            raise GuardRefusal("REFUSE: input %s sha256 %s != pinned %s" % (path, got[:12], want[:12]))


# --- B2: the harness's deny-by-default closed-world input surface -------------------------------
_io_allow = None  # None => guard inactive; set => only these absolute real paths may be opened


def _open_audit(event, args):
    if event == "open" and _io_allow is not None:
        path = args[0]
        try:
            ap = os.path.realpath(path)
        except Exception:
            ap = str(path)
        if ap not in _io_allow:
            raise GuardRefusal("REFUSE: closed-world harness opened %r (not in the pinned fixture allowlist)" % (path,))


sys.addaudithook(_open_audit)  # installed once; gated by _io_allow


class closed_world_io:
    """Context manager for the smoke harness's DATA phase: inside it, the ONLY paths that may be
    open()ed are the pinned fixtures. Library imports happen BEFORE entering (allowlist=None).
    Absolute-path reads, $HOME, /tmp, globbed sweeps -> all refuse. Deny-by-default."""
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
