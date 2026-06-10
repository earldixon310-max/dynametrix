# OVP v0.2 — Template Hardening (DRAFT rev5 — post cold-pass-3a/3b)

**Status:** DRAFT. rev3 drew two independent cold reads that converged on the same B1/B2/B3 fixes (3a → rev4) and surfaced further implementation leaves (3b → rev5). Architecture affirmed stable since rev2; defects are localizing into implementation leaves. Program-evolution discipline: rev5 re-routes **two fresh** cold passes on the new bytes. v0.1 and the locked detector arc unchanged.

**Scope.** Two structure-*adding* judge/lock seeds that **adopt together** (§2.5 — really a *triple* with B2's deny-by-default): **Seed 1 — sealed-run self-guard (H1)**, **Seed 2 — smoke-harness lock-inclusion (T-2)**. Split out: re-route-depth taxonomy (own thread). Deferred: Layer formalization, Class-C, sourcing (§5).

**Architecture (stable).** Factor every judge into **(sealed-loader, synthetic-loader, shared compute-core)**. The two loaders are **distinct**; only the core is shared. H1 gates the *sealed-loader* path; the harness drives the *synthetic-loader* + shared core on synthetic data. This factoring is the spine of both seeds.

---

## 1. Seed 1 — Sealed-run self-guard

**Requirement.** A judge **refuses to compute the sealed quantity unless its study is locked**, verified by git object identity. The guard gates the real-candidate load + sealed compute; the shared core stays exercisable by the harness (§1c).

**Mechanism (rev5):**
- `LOCK_TAG` and `LOCKED_PATH` are **constant literals pinned in the locked script bytes** (never derived from `__file__`). The expected blob OID is **fetched dynamically** from `LOCK_TAG:LOCKED_PATH` — **never hard-coded** into the script (hard-coding the OID reintroduces the circularity the fixpoint avoids; state this prohibition so it isn't "optimized" back in).
- The guard is the **first executable statement reachable**, before the candidate is loaded and before any import that performs data IO. The sealed value must never exist on the refuse path (closes `--out`/stdout/pipe/log/traceback/partial-state by construction).
- Compute **iff** `LOCK_TAG` resolves **and** the working file is git-object-identical to `git rev-parse LOCK_TAG:LOCKED_PATH`, via a **filter-aware** comparison (`git hash-object --path=LOCKED_PATH -- <self>` or `git diff --quiet LOCK_TAG -- LOCKED_PATH`). **Never** a raw byte hash.

**Normalization must be pinned, or it runs the wrong way (cold-pass-3b).** Filter-aware comparison neutralizes autocrlf and round-trip clean filters, but a **lossy / non-idempotent** filter breaks it *both* ways — a non-idempotent filter false-refuses; a **lossy** filter (stripping whitespace, keyword expansion) can clean two *different* working files to the *same* blob → **wrong-compute on non-locked bytes**. Close it by pinning the judge and harness paths **filter-free** (`-text`, no `filter`) in a **`.gitattributes` that is itself in the locked set** — a **fifth locked artifact**. With `-text` the blob is the raw bytes, the comparison is unambiguous, and the lossy-filter collision is impossible.

**Fail CLOSED on every git-error path (gating).** Tag missing, `.git` absent (tarball/CI), `git` binary absent, `__file__` absent (`python -c`, zipapp), any command non-zero/exception ⇒ **refuse**. A required test enumerates each → refuse. Fail-*open* here inverts the guard precisely where an idle invocation is most likely. **No non-git override:** every sealed run (canonical *and* technical-failure amendment — which is itself a new lock) occurs in the git-available locked checkout; an override would reopen the accident door.

**Coverage and boundaries (precise — so nothing is over-read):**
- **Self-containment.** The guard verifies **one** blob, so the sealed computation must be **wholly self-contained in the guarded file** (no project-local imports on the sealed path), or the guard must extend to every locked source file the judge imports. "byte-identity" over one blob is otherwise partial. (Detector judges qualify — they import only numpy/sklearn.)
- **Interpreter/dependency identity is out of scope by construction** — the guard secures *source bytes*, not numpy/Python versions; "byte-identity" ≠ "execution-environment identity" (that is the manifest's environment record). Name the boundary.
- **Sealed quantity only** — disclosed precursors (marginal, baseline-only discrimination) are computed by design and not hidden.
- **Accident-not-tamper (one line):** defends an accidental invocation, not an adversary — a self-issued `LOCK_TAG`, a guard deletion, or a SHA-1 collision are out of model and the signature/human-trust layer's job. Not tamper-proof.
- **Path/file hygiene:** lookup by pinned `LOCKED_PATH` (a move under live-`__file__` would false-refuse); judge pinned to a **regular file** (not a symlink, whose blob stores link text); exec-bit irrelevant (mode is in the tree, not the blob).
- **Audit log:** logs `LOCK_TAG` + verified code object-hash; **never** the sealed value.

## 1b. Adjacent required guards

- **Single-execution / re-run guard** (output-exists refusal) in the judge preamble, **after** the H1 check, **before** compute. Soft guard (filesystem state): permits the first run (output absent), refuses a re-run; a crash leaving partial output forces the documented new-tag amendment path (intended). Minor: a stray file at the output path false-refuses (safe direction).
- **Runtime input-hash check** — assert loaded inputs match the manifest/locked-anchor hashes, else refuse. **Enforced, not merely manifested** (the hash must be over the exact materialized bytes the run loads). H1 + this ⇒ right-code-on-right-data.

## 1c. Harness shares the judge's compute-core (gating)

H1's hard-refuse-pre-lock makes the judge **un-smoke-testable on real shapes**, so a judge-only defect would first surface at the irreversible locked run. The harness therefore **calls the judge's same compute-core**, differing **only** in the loader: harness = synthetic-loader + shared core; judge = sealed-loader (H1-gated) + shared core. The loaders are **distinct files/functions** (no shared import of the sealed loader), so there is no loader channel back to the candidate. The guard gates the loader, not the core; the core is exercised pre-lock on synthetic data.

**Retroactive (#1–#4):** moot — §3.

---

## 2. Seed 2 — Smoke-harness lock-inclusion

**Requirement.** The synthetic smoke harness is a **named file in the atomic lock commit**, hashed in the manifest. Locked set = **five files**: pre-registration, judge, smoke harness, manifest, **`.gitattributes`** (the normalization pin, §1).

**Input surface — deny-by-default closed-world allowlist (gating).** A denylist can never prove exhaustiveness, and because the harness is H1-exempt it concentrates the entire residual peek-risk — so state it positively:

> The harness reads **exactly** {the pinned, hashed fixture blob(s), one literal in-process seed} and performs **no other IO** — enforced by (i) the fixture hash check, (ii) the seed pinned in the locked source, (iii) an audit/assert that **no other `open()` or import performs data IO**, executed with **no network** and a working directory containing only the fixtures.

This subsumes the channels a denylist forgets: CLI, env, stdin, config, import-time side effects, filesystem globbing/dir-scans, transitive-import IO from dependencies, deserialization side effects, the fixture-swap channel.

**Fixture and entropy hygiene (cold-pass-3b):**
- **Non-executable fixture format only** (`.npy`/`.csv`) — **never** pickle/joblib: hashing bounds the bytes, not the arbitrary code a pickle load executes (which could pull the real candidate). With a non-executable format the hash is meaningful.
- **Seed fully determines generation** — no hidden entropy from wall-clock, `os.urandom`, or `PYTHONHASHSEED`; behavior is a pure function of locked code + hashed fixture + literal seed.

**With §1c's shared core, B2 reduces to:** *harness uses the synthetic loader, judge uses the sealed loader, everything downstream is byte-identical code.*

**Claim, honest (conditional on the closed surface):** *locked artifacts auditable (harness source synthetic, provable from the hashed bytes; which harness binds to this study); non-execution outside the set operator-attested.* **B2's exhaustiveness is the hinge B3 hangs on.**

**"Results-shaped" defined on content/schema** (the judge's `--out` schema), not filename.

## 2.5 Adopt-together — a TRIPLE coupling (cold-pass-3b)

Not a pair but **H1 + T-2 + B2's deny-by-default**: H1 seals the judge's real-candidate compute and *displaces* all pre-lock exercising onto the harness; T-2 makes that displaced surface auditable; **B2 is what makes the displaced surface safe**. None adopts alone. **Acknowledged cost:** all clear the cold passes together, so an unresolved item in one (e.g. H1's git-error handling) blocks the others — conservative and accepted.

---

## 3. Grandfather #1–#4 (no re-lock) + signed additive attestation

**Grandfather, do not re-lock — consistency-required.** Re-tagging replaces the cleared bytes and destroys "locked == what was read"; rc-v1 / ersaf-v1.0 / ct-v1 were **not** retroactively re-signed for exactly this reason (the no-re-sign precedent in the LOCK RECORD is the citation). Precedent carries the re-tagging prohibition; the attestation does the retroactive-auditability work.

**Signed additive attestation — TWO schema-enforced honesty distinctions (mandatory structured fields, not droppable prose):**
1. **Claim scope** — *source-synthetic: **verifiable*** (exhibit the hashed blob + closed input surface) vs *non-execution: **attested*** (a historical negative no signature verifies). Claims **only** source-synthetic.
2. **Anchoring tier** — because the original lock did not commit the harness hash: **anchored / proof-grade** (new studies, harness hash in the signed atomic lock commit) vs **unanchored / attestation-grade** (grandfathered #1–#4, bound only by the operator's dated post-hoc identification — **explicitly weaker than contemporaneous lock-inclusion**). Collapsing these tiers lets a retroactive attestation masquerade as origin-locked; that is the way it misleads.

Mechanically (zero re-tagging, separate signed object referencing by hash) it preserves immutability; the only risk was what the artifact says about itself, closed by the two mandatory distinctions.

---

## 4. Adoption path

rev5 re-routes **two fresh** cold passes (3a/3b found gating items → count reset; author cannot clear). On adoption: standard judge template — (sealed-loader, synthetic-loader, shared-core) factoring; git-object-identity fail-closed self-guard with a locked filter-free `.gitattributes`; self-contained sealed compute; separated re-run guard; enforced runtime input-hash check; deny-by-default non-executable-fixture harness; **five-file** locked set; two-distinction signed attestation for grandfathered #1–#4. **Forward-looking; #1–#4 grandfathered without re-lock.** The triple (H1+T-2+B2) adopts as one unit. Template build kept **independent of the re-route-taxonomy decision**. H1 is a **backstop, not a replacement** for the cold reader's judgment to decline execution; the result cold-pass protocol is unchanged.

## 5. Explicitly deferred / queued (unchanged)

- **Descriptor Justification Layer formalization: DEFERRED** to ≥1 more candidate (n=1=`pred` thin).
- **Class-C target-fit: OPEN** — roadmap not rule (RTVP realizes it as a separate instrument).
- **Community-validated rung (§6.3): QUEUED** sourcing thread.
- **Scope guard:** the triple + attestation stay **template-scoped** (reviewed once, applied to #1–#4 uniformly), never retrofitted to #4 alone.

---

## Appendix — cross-pass disposition (for the record)

**cold-pass-1** (rev1→rev2): single hard-refuse mechanism (flag deleted, stdout closed by refuse-before-compute, named-tag binding, "signed" overclaim corrected, output-exists separated); Seed-2 input surface + fixture/seed hashed; "end-to-end" downgraded; grandfather on precedent + signed attestation; taxonomy split out.

**cold-pass-2** (rev2→rev3): B1 git-object-identity vs raw byte hash; B2 input constraint over all channels; B3 retroactive labeling; results-shaped by content; output-exists home; input enforced not manifested.

**cold-pass-3a** (rev3→rev4): fail-closed on git errors; filter-aware `--path`; `LOCK_TAG`/`LOCKED_PATH` pinned constants; guard-first-statement; closed-world allowlist; harness shares compute-core; anchored/unanchored attestation tiers; (sealed-loader, shared-core) factoring.

**cold-pass-3b** (rev3, independent — corroborated 3a's B1/B2/B3 folds *and* added, now folded into rev5): lossy/non-idempotent-filter wrong-compute closed by a **locked filter-free `.gitattributes`** (fifth locked artifact); **OID-not-hardcoded** prohibition; **self-containment** of the sealed compute (single-blob coverage limit); **non-executable fixture format**; **separate loaders** (no shared-import channel); **fixture entropy hygiene**; **triple coupling** (H1+T-2+B2); **interpreter/dependency-identity boundary** named; symlink/regular-file + stray-output-file minors. Architecture affirmed stable; author cannot clear; rev5 re-routes two fresh passes.
