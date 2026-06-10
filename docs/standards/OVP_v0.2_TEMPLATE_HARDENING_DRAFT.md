# OVP v0.2 — Template Hardening (DRAFT rev7 — post cold-pass-3a/3b/3c/3d)

**Status:** DRAFT, **architecturally converged**. **cold-pass-3d CLEARED rev6 with no lock-blocker** (first clean pass) — every finding in the implementation-leaf/claim-scoping layer, and the reader explicitly corroborated §6 ("exactly the things its test suite should assert rather than prose should argue"). rev7 folds 3d's one wording fix (the §1 R-1 over-claim) plus its leaf tightenings. **Recommendation: the spec is done; the next artifact is the tested reference implementation** (§6), where the leaf properties are verified by *execution*. The spec is the *design input* to that implementation — which is the artifact the two-pass lock bar should attach to (code + tests), not the spec prose. Program-evolution discipline: any further prose revision re-routes fresh passes on the actual draft bytes. v0.1 and the locked detector arc unchanged.

**Claim discipline (R-1 — the through-line).** Every guarantee here is pinned to **accident-prevention**, never tamper-resistance. The machinery (signed tags, blob identity, attestations) invites over-reading as adversary-proof; it is not. A motivated party who forges a tag or edits the guard out defeats it — that residual is the signature/human-trust layer's job, explicitly disclaimed. Every claim below holds *only* against an honest premature or mistaken invocation.

**Scope.** Two structure-*adding* judge/lock seeds that **adopt together** (§2.5 — really a *triple* with B2's deny-by-default): **Seed 1 — sealed-run self-guard (H1)**, **Seed 2 — smoke-harness lock-inclusion (T-2)**. Split out: re-route-depth taxonomy (own thread). Deferred: Layer formalization, Class-C, sourcing (§5).

**Architecture (stable).** Factor every judge into **(sealed-loader, synthetic-loader, shared compute-core)**. The two loaders are **distinct**; only the core is shared. H1 gates the *sealed-loader* path; the harness drives the *synthetic-loader* + shared core on synthetic data. This factoring is the spine of both seeds.

---

## 1. Seed 1 — Sealed-run self-guard

**Requirement.** A judge **refuses to compute the sealed quantity unless its study is locked**, verified by git object identity. The guard gates the real-candidate load + sealed compute; the shared core stays exercisable by the harness (§1c).

**Mechanism (rev5):**
- `LOCK_TAG` and `LOCKED_PATH` are **constant literals pinned in the locked script bytes** (never derived from `__file__`). The expected blob OID is **fetched dynamically** from `LOCK_TAG:LOCKED_PATH` — **never hard-coded** into the script (hard-coding the OID reintroduces the circularity the fixpoint avoids; state this prohibition so it isn't "optimized" back in).
- The guard is the **first executable statement reachable**, before the candidate is loaded and before any import that performs data IO. The sealed value must never exist on the refuse path (closes `--out`/stdout/pipe/log/traceback/partial-state by construction).
- Compute **iff** `LOCK_TAG` resolves **and** the working file is git-object-identical to `git rev-parse LOCK_TAG:LOCKED_PATH`, via a **filter-aware** comparison (`git hash-object --path=LOCKED_PATH -- <self>` — content-identity, **move-robust**; or `git diff --quiet LOCK_TAG -- LOCKED_PATH` — which false-refuses on a legitimate path move, safe-direction but **not** equivalent, so prefer the content-identity form). **Never** a raw byte hash.

**Normalization must be pinned, or it runs the wrong way (cold-pass-3b).** Filter-aware comparison neutralizes autocrlf and round-trip clean filters, but a **lossy / non-idempotent** filter breaks it *both* ways — a non-idempotent filter false-refuses; a **lossy** filter (stripping whitespace, keyword expansion) can clean two *different* working files to the *same* blob → **wrong-compute on non-locked bytes**. Close it by pinning the judge and harness paths **filter-free** (`-text`, no `filter`) in a **`.gitattributes` that is itself in the locked set** — a **fifth locked artifact**. With `-text` the blob is the raw bytes and the comparison is unambiguous, closing the lossy-filter collision **under the accident model**. (It is *not* impossible by construction: higher-precedence **local** attribute sources outside the locked set — `$GIT_DIR/info/attributes`, `core.attributesFile` — could re-introduce a lossy filter; that is deliberate local misconfiguration, i.e. out-of-model **tamper** per R-1, and is a reference-suite assertion against a hostile `info/attributes`, not a construction-level guarantee.)

**Fail CLOSED on every git-error path (gating).** Tag missing, `.git` absent (tarball/CI), `git` binary absent, `__file__` absent (`python -c`, zipapp), any command non-zero/exception ⇒ **refuse**. A required test enumerates each → refuse. Fail-*open* here inverts the guard precisely where an idle invocation is most likely. **No non-git override:** every sealed run (canonical *and* technical-failure amendment — which is itself a new lock) occurs in the git-available locked checkout; an override would reopen the accident door.

**Coverage and boundaries (precise — so nothing is over-read):**
- **Self-containment.** The guard verifies **one** blob, so the sealed computation must be **wholly self-contained in the guarded file** (no project-local imports on the sealed path), or the guard must extend to every locked source file the judge imports. "byte-identity" over one blob is otherwise partial. (Detector judges qualify — they import only numpy/sklearn.)
- **Interpreter/dependency identity is out of scope by construction** — the guard secures *source bytes*, not numpy/Python versions; "byte-identity" ≠ "execution-environment identity" (that is the manifest's environment record). Name the boundary.
- **Sealed quantity only** — disclosed precursors (marginal, baseline-only discrimination) are computed by design and not hidden.
- **Pre-lock and wrong-bytes only (R-2).** H1 closes *pre-lock* peeks and *wrong-bytes* runs. It does **not** close a *post-lock* re-run with non-canonical `--seed`/`--reps` — that passes the guard (tag exists, bytes match) and computes a real HDG. Post-lock single-execution and canonical-parameter discipline are governed **separately** (single-execution rule + the output-exists guard, §1b — partial: same `--out` only). The claim is "closes pre-lock/wrong-bytes peeks," never "every peek path."
- **Accident-not-tamper (one line):** defends an accidental invocation, not an adversary — a self-issued `LOCK_TAG`, a guard deletion, or a SHA-1 collision are out of model and the signature/human-trust layer's job. Not tamper-proof.
- **Path/file hygiene:** lookup by pinned `LOCKED_PATH` (a move under live-`__file__` would false-refuse); judge pinned to a **regular file** (not a symlink, whose blob stores link text); exec-bit irrelevant (mode is in the tree, not the blob).
- **Audit log:** logs `LOCK_TAG` + verified code object-hash; **never** the sealed value.

## 1b. Adjacent required guards

- **Single-execution / re-run guard** (output-exists refusal) in the judge preamble, **after** the H1 check, **before** compute. Soft guard (filesystem state): permits the first run (output absent), refuses a re-run; a crash leaving partial output forces the documented new-tag amendment path (intended). Minor: a stray file at the output path false-refuses (safe direction). **Scope (honest):** it closes silent **same-output** re-run only; a re-run to a *different* `--out` path survives the mechanism and falls back to single-execution discipline (consistent with R-2 — the chain is not "fully mechanized re-run closure").
- **Runtime input-hash check** — assert loaded inputs match the expected hashes, else refuse. **Enforced, not merely manifested** (the hash must be over the exact materialized bytes the run loads). **The expected hashes must be identity-covered (cold-pass-3c):** pinned in the **guarded blob** (hardcoded constants — as the detector judges already do with `EXPECTED_…_SHA256`), so the self-guard's blob-identity check covers them. If instead read from the manifest, the manifest must itself be inside the blob-identity check — otherwise trust silently moves to an unverified file. H1 + this ⇒ right-code-on-right-data.

## 1c. Harness shares the judge's compute-core (gating)

H1's hard-refuse-pre-lock makes the judge **un-smoke-testable on real shapes**, so a judge-only defect would first surface at the irreversible locked run. The harness therefore **calls the judge's same compute-core**, differing **only** in the loader: harness = synthetic-loader + shared core; judge = sealed-loader (H1-gated) + shared core. The loaders are **distinct files/functions** (no shared import of the sealed loader), so there is no loader channel back to the candidate. The guard gates the loader, not the core; the core is exercised pre-lock on synthetic data.

**Retroactive (#1–#4):** moot — §3.

---

## 2. Seed 2 — Smoke-harness lock-inclusion

**Requirement.** The synthetic smoke harness is a **named file in the atomic lock commit**, hashed in the manifest. Locked set = pre-registration, **every sealed-path source file** (judge + shared compute-core + guard — see §1 self-containment-or-cover; corrected from "five files" by cold-pass-A finding 1, which demonstrated that omitting the imported core left a post-lock-edit wrong-compute), smoke harness, manifest, **`.gitattributes`** (the normalization pin, §1). H1 verifies every sealed-path source at runtime, not just the judge.

**Input surface — deny-by-default closed-world allowlist (gating).** A denylist can never prove exhaustiveness, and because the harness is H1-exempt it concentrates the entire residual peek-risk — so state it positively:

> The harness reads **exactly** {the pinned, hashed fixture blob(s), one literal in-process seed} and performs **no other IO** — enforced by (i) the fixture hash check, (ii) the seed pinned in the locked source, (iii) an audit/assert that **no other `open()` or import performs data IO**, executed with **no network** and a working directory containing only the fixtures. **Audit (iii) is the load-bearing enforcement, not belt-and-suspenders:** the working-dir/no-network sandbox bounds relative-path and glob resolution but **not** absolute-path reads (`open("/abs/…")`, `$HOME`, `/tmp`), so the IO audit is what actually closes the surface. Its one unpinned edge — distinguishing data IO from benign library-load IO (numpy opens shared objects at import) — is a reference-suite assertion (audit hook installed before first import; an absolute-path read attempt asserted caught), not a prose proof.

This subsumes the channels a denylist forgets: CLI, env, stdin, config, import-time side effects, filesystem globbing/dir-scans, transitive-import IO from dependencies, deserialization side effects, the fixture-swap channel.

**Fixture and entropy hygiene (cold-pass-3b):**
- **Non-executable fixture format only** (`.npy`/`.csv`) — **never** pickle/joblib: hashing bounds the bytes, not the arbitrary code a pickle load executes (which could pull the real candidate). With a non-executable format the hash is meaningful.
- **Seed fully determines generation** — no hidden entropy from wall-clock, `os.urandom`, or `PYTHONHASHSEED`; behavior is a pure function of locked code + hashed fixture + literal seed.

**With §1c's shared core, B2 reduces to:** *harness uses the synthetic loader, judge uses the sealed loader, everything downstream is byte-identical code.*

**Claim, honest (conditional on the closed surface):** *locked artifacts auditable (harness source synthetic, provable from the hashed bytes; which harness binds to this study); non-execution outside the set operator-attested.* **B2's exhaustiveness is the hinge B3 hangs on.**

**"Results-shaped" defined on content/schema** (the judge's `--out` schema), not filename.

## 2.5 Adopt-together — the FULL CHAIN, not a subset (cold-pass-3b/3c)

The binding unit is the **whole closure chain — H1 + T-2 + B2 deny-by-default + runtime input-hash (§1b) + output-exists (§1b)** — not the two named seeds. Each closes a distinct hole: H1 (pre-lock/wrong-bytes peek) displaces pre-lock exercising onto the harness; T-2 makes that surface auditable; B2 makes it safe; the input-hash check closes data-substitution (which H1 leaves open — script identity ≠ run validity); output-exists closes silent re-run. **If the coupling is written as just H1+T-2, the input-hash and output-exists guards become omittable, reopening data substitution and re-run** — a partial guard that *looks* complete, which is worse than none. None adopts alone. **Acknowledged cost:** all clear together, so an unresolved item in one blocks the others — conservative and accepted.

---

## 3. Grandfather #1–#4 (no re-lock) + signed additive attestation

**Grandfather, do not re-lock — consistency-required.** Re-tagging replaces the cleared bytes and destroys "locked == what was read"; rc-v1 / ersaf-v1.0 / ct-v1 were **not** retroactively re-signed for exactly this reason (the no-re-sign precedent in the LOCK RECORD is the citation). Precedent carries the re-tagging prohibition; the attestation does the retroactive-auditability work.

**Signed additive attestation — TWO schema-enforced honesty distinctions (mandatory structured fields, not droppable prose):**
1. **Claim scope** — *source-synthetic: **verifiable*** (exhibit the hashed blob + closed input surface) vs *non-execution: **attested*** (a historical negative no signature verifies). Claims **only** source-synthetic.
2. **Anchoring tier** — because the original lock did not commit the harness hash: **anchored / proof-grade** (new studies, harness hash in the signed atomic lock commit) vs **unanchored / attestation-grade** (grandfathered #1–#4, bound only by the operator's dated post-hoc identification — **explicitly weaker than contemporaneous lock-inclusion**). Collapsing these tiers lets a retroactive attestation masquerade as origin-locked; that is the way it misleads. *Optional hardening (cold-pass-3d):* narrow the unanchored pure-assertion with a checkable temporal bound — require the attested harness blob to be present in repo history at/before the original lock date, constraining (not eliminating) honest misidentification of which historical harness version was used.

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

## 6. Next artifact — the tested reference implementation (recommended terminus)

The spec has converged; the open items across rev4–rev6 are **implementation leaves** (git-error enumeration, IO-audit exhaustiveness, filter determinism, fixture-format rejection, guard placement, input-hash sourcing). These are verified far more reliably by **execution** than by prose: a test that runs the guard with no `.git` and asserts refusal is *proof*; a reader asserting "it should refuse" is *attestation*. cold-pass-3c made the ceiling explicit — a prose pass re-derived folds already in the bytes and could not clear without reading them.

**Recommended next artifact:** a reference implementation of the `(sealed-loader, synthetic-loader, shared-core)` judge + harness + guard, with a **test suite** exercising each required property — fail-closed on every git-error path; filter determinism under `autocrlf`; closed-world IO audit (no other `open()`/import performs data IO); non-executable-fixture rejection; pinned-path move-robustness; output-exists + input-hash composition; the two attestation tiers. The reference template + tests become the **actual locked v0.2 artifact**; future studies instantiate it rather than re-deriving the guards, and review shifts from imagining edge cases to reading code + tests that exercise them. This rev6 is the spec that implementation implements.

---

## Appendix — cross-pass disposition (for the record)

**cold-pass-1** (rev1→rev2): single hard-refuse mechanism (flag deleted, stdout closed by refuse-before-compute, named-tag binding, "signed" overclaim corrected, output-exists separated); Seed-2 input surface + fixture/seed hashed; "end-to-end" downgraded; grandfather on precedent + signed attestation; taxonomy split out.

**cold-pass-2** (rev2→rev3): B1 git-object-identity vs raw byte hash; B2 input constraint over all channels; B3 retroactive labeling; results-shaped by content; output-exists home; input enforced not manifested.

**cold-pass-3a** (rev3→rev4): fail-closed on git errors; filter-aware `--path`; `LOCK_TAG`/`LOCKED_PATH` pinned constants; guard-first-statement; closed-world allowlist; harness shares compute-core; anchored/unanchored attestation tiers; (sealed-loader, shared-core) factoring.

**cold-pass-3b** (rev3, independent — corroborated 3a's B1/B2/B3 folds *and* added, now folded into rev5): lossy/non-idempotent-filter wrong-compute closed by a **locked filter-free `.gitattributes`** (fifth locked artifact); **OID-not-hardcoded** prohibition; **self-containment** of the sealed compute (single-blob coverage limit); **non-executable fixture format**; **separate loaders** (no shared-import channel); **fixture entropy hygiene**; **triple coupling** (H1+T-2+B2); **interpreter/dependency-identity boundary** named; symlink/regular-file + stray-output-file minors. Architecture affirmed stable; author cannot clear; rev5 re-routes two fresh passes.

**cold-pass-3c** (charge-only — packet error P-1: reader received design history + spec + taxonomy thread, **not** the draft bytes; not a valid clearing pass). Independently re-derived three folds already in rev5 (pinned-path constant, anchored/unanchored attestation tiers, git-env operating constraint) — corroboration. Four genuine refinements folded into rev6: **(1)** adopt-together unit is the **full closure chain** (H1+T-2+B2+input-hash+output-exists), not the triple; **(2)** input-hash expected values **identity-covered** (pinned in the guarded blob); **(3)** R-2 — H1 closes pre-lock/wrong-bytes only, **not** post-lock non-canonical re-runs; **(4)** R-1 — claims pinned to accident-prevention, stated prominently. Process: routing must send the actual draft file; spec now converged → §6 recommends the tested reference implementation as the terminus.

**cold-pass-3d** (rev6, correct packet — **first clean pass; no lock-blocker**). Confirmed sound: fixpoint, refuse-before-compute, guard-in-loader-not-core, named-tag binding, signature omission, fail-closed, the honest B2 claim split, grandfather + precedent, the two attestation distinctions, the full-chain coupling, the deferrals and split. One wording fix (folded → rev7): §1 "lossy-filter collision impossible" over-claimed against R-1 — `info/attributes`/`core.attributesFile` are higher-precedence, outside the locked set, so the collision is closed *under the accident model*, not by construction (out-of-model tamper; reference-suite assertion). Leaf tightenings folded: the two compare forms aren't move-equivalent (prefer content-identity); audit (iii) is load-bearing (sandbox doesn't bound absolute paths); output-exists is same-output-only; unanchored-attestation temporal-bound option. Reader explicitly corroborated §6 — the residuals are the reference suite's job to prove by execution. Author cannot clear; a second independent clean pass (or, per §6, the reference implementation's own review) is the remaining gate.
