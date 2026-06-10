# OVP v0.2 — Template Hardening (DRAFT rev4 — post cold-pass-3)

**Status:** DRAFT, revised after cold-pass-3 (three gating items, all implementation-leaf; architecture affirmed stable since rev2). Program-evolution discipline: rev4 re-routes **two fresh** cold passes on the new bytes. v0.1 and the locked detector arc unchanged.

**Scope.** Two structure-*adding* judge/lock seeds that **adopt together** (§2.5): **Seed 1 — sealed-run self-guard (H1)** and **Seed 2 — smoke-harness lock-inclusion (T-2)**. Split out: re-route-depth taxonomy (own redesign-or-retire thread). Deferred: Layer formalization, Class-C, sourcing (§5).

**Architecture (stable, affirmed across three passes).** Factor every judge into **(sealed-loader, shared compute-core)**. H1 gates the *sealed-loader* path; the *compute-core* is shared with the harness and exercised on synthetic data. This single factoring is what makes the rest coherent — it is the spine of both seeds.

---

## 1. Seed 1 — Sealed-run self-guard

**Requirement.** A judge **refuses to compute the sealed quantity unless its study is locked**, verified by git object identity. The guard gates the **real-candidate load + sealed compute**; the shared compute-core remains exercisable by the harness on synthetic data (§1c).

**Mechanism (rev4 — fail-closed, filter-aware, position-pinned):**

> `LOCK_TAG` and the judge's `LOCKED_PATH` are **constant string literals pinned in the locked script bytes** (never derived from `__file__` — a post-lock move would then false-refuse). The guard is the **first executable statement reachable**, before the candidate is loaded and before any import that performs data IO (§1c). Compute the sealed quantity **iff** all hold, else **hard-refuse**:
> 1. `LOCK_TAG` resolves to an existing tag;
> 2. the working file is git-object-identical to the locked blob, by a **filter-aware** comparison — `git hash-object --path=LOCKED_PATH -- <self>` (applies the clean filter + EOL per gitattributes) equal to `git rev-parse LOCK_TAG:LOCKED_PATH`, or equivalently `git diff --quiet LOCK_TAG -- LOCKED_PATH`. **Never** `sha256(open(file,'rb'))` (raw byte hash false-refuses under `autocrlf`/smudge — the common Windows case).

**Gating (cold-pass-3 item 1) — fail CLOSED on every git-error path.** Tag missing, `.git` absent (tarball/CI), `git` binary absent, any `rev-parse`/`hash-object`/`diff` non-zero or exception ⇒ **refuse**. If the guard fails *open* on git errors it inverts precisely in the environments where an idle "does it even run?" is most likely — fresh clone before tags fetched, shallow runner. **A required test enumerates each git-error path → refuse.** This is the one place the guard could wrongly *compute*; closing it is gating.

**Pins and boundaries (required-non-gating + notes):**
- **Filter-aware comparison** as above (else false-refuse on autocrlf/smudge).
- **Canonical-run environment named:** a full clone with the signed `LOCK_TAG` fetched, at the locked checkout (gitattributes drift between lock and runtime diverges normalization → safe-direction refuse). "No git → refuse" is a *feature*: the canonical verdict is produced only where provenance is verifiable.
- **Scope, precise:** closes every leak path *for the sealed quantity* (never formed pre-lock); does **not** hide disclosed *precursors* (marginal, baseline-only discrimination) computed by design. Secures *when*/*which-bytes* — not the tag **signature** (human-trust layer, disclaimed) and not **input identity** (§1b).
- **Accident-not-tamper boundary (one line, so it is never over-read):** the guard defends against an accidental invocation, not an adversary — a self-issued `LOCK_TAG`, a guard deletion, or a SHA-1 collision are out of model and are the signature/human-trust layer's job. Not tamper-proof.
- **Audit log:** the guard logs the `LOCK_TAG` and the verified code object-hash (aids audit, not sensitive); it **never** logs the sealed value.

## 1b. Adjacent required guards (chain has no soft link)

- **Single-execution / re-run guard** (the separated output-exists refusal) lives in the judge's **guard preamble, after the H1 check and before compute**. Distinct property (no-silent-rerun) — H1 does not subsume it. Edge: refusing a re-run after a crash left partial output is *correct* — a crashed run is a documented technical failure amended under a **new tag**, so forcing the new-tag path is intended, not a hole.
- **Runtime input-hash check** (right-code-on-right-data): the judge asserts the loaded inputs match the manifest/locked-anchor hashes, else refuse — **enforced, not merely manifested** (as the detector judges already do). H1 + this ⇒ right-code-on-right-data; neither leaves a link the other must cover.

## 1c. Harness shares the judge's compute-core (cold-pass-3 item 3 — gating)

H1's hard-refuse-pre-lock makes the judge itself **un-smoke-testable on real shapes** — so a judge-only defect (a dtype/shape quirk of the real candidate) would surface for the **first time at the irreversible locked run**. To prevent that, the smoke harness must **call the judge's same compute-core** (the HDG/estimator/verdict functions), swapping **only the input-loading surface**: harness = synthetic-loader + shared core; judge = sealed-loader (H1-gated) + shared core. The guard gates the *loader*, not the core; the core is exercised pre-lock on synthetic data. This both removes the un-audited harness↔judge divergence **and** makes B2 crisp (the only difference between them is which loader runs).

**Retroactive (#1–#4):** moot — §3.

---

## 2. Seed 2 — Smoke-harness lock-inclusion

**Requirement.** The synthetic smoke harness is a **named file in the atomic lock commit**, hashed in the manifest. Locked set = **four files**: pre-registration, judge, smoke harness, manifest.

**Input surface — CLOSED-WORLD ALLOWLIST, not a denylist (cold-pass-3 item 2 — gating).** A denylist of redirect channels can never prove exhaustiveness, and because the harness is H1-exempt, *any* surviving channel is a live peek path. So state it positively and enforce it:

> The harness reads **exactly** {pinned hashed fixture blob(s), one literal in-process seed} and **nothing else.** Enforced by (i) the fixture hash check, (ii) the seed pinned in the locked source, and (iii) an audit/assert that **no other `open()` or import performs data IO** — ideally executed with **no network** and a working directory containing only the fixtures.

The closed-world form subsumes the channels a denylist forgets (CLI, env, stdin, config, import-time side effects, **filesystem globbing/dir-scans, transitive-import IO from dependencies, deserialization side effects like pickle/joblib, the fixture-swap channel**). Only the allowlist lets the exhaustiveness claim be honest.

**With §1c's shared core, B2 reduces to a clean statement:** *harness uses the synthetic loader, judge uses the sealed loader, everything downstream is byte-identical code.* Easier to audit, crisper to claim.

**Claim, honest (conditional on the closed input surface):** *the locked artifacts are auditable (harness source synthetic — provable from the hashed bytes; and which harness binds to this study); non-execution of anything outside the locked set remains operator-attested.* (With H1, the judge leaves the attested set pre-lock — it refuses — narrowing the residual to ad-hoc non-judge scripts.) **B2's exhaustiveness is the hinge B3 hangs on — they cannot be cleared independently.**

**"Results-shaped" defined on content/schema** (the judge's `--out` schema), not filename — a rename cannot dodge a refusal.

## 2.5 H1 + T-2 adopt together (binding)

Complementary halves of one property: H1 seals the judge's real-candidate compute; T-2 makes the harness's synthetic-only claim auditable; §1c's shared core ties them. **Cannot adopt either alone** — T-2 without H1 locks a harness whose non-execution is still only attested; H1 without T-2's closed input surface leaves an unguarded peek path through the exempt harness. **Acknowledged cost:** both clear the template's cold passes together, so an unresolved item in one (e.g. H1's git-error handling) blocks the other — conservative and accepted.

---

## 3. Grandfather #1–#4 (no re-lock) + signed additive attestation

**Grandfather, do not re-lock — consistency-required.** Re-tagging replaces the cleared bytes and destroys "locked == what was read"; rc-v1 / ersaf-v1.0 / ct-v1 were **not** retroactively re-signed for exactly this reason (the no-re-sign precedent on record in the LOCK RECORD is the citation). Precedent carries the re-tagging prohibition; the attestation does the retroactive-auditability work.

**Signed additive attestation — TWO orthogonal honesty distinctions, both schema-enforced (cold-pass-3 items 6–7).** The attestation is a new signed object referencing the study by hash (zero re-tagging → immutability preserved). To not mislead, the label is a **structured, mandatory field** (not droppable free prose) carrying:

1. **Claim scope** — split *source-synthetic: **verifiable*** (exhibit the hashed blob + closed input surface) from *non-execution: **attested*** (a historical negative no signature can verify). The attestation claims **only** source-synthetic.
2. **Anchoring tier** — *because the original lock did not commit the harness hash*, a grandfathered attestation asserts "this blob was the smoke for study X" with **nothing in the original locked set to bind it**:
   - **anchored / proof-grade** — new studies under the v0.2 template, where the harness hash is in the signed atomic lock commit;
   - **unanchored / attestation-grade** — grandfathered #1–#4, where the binding is the operator's dated post-hoc identification, **explicitly weaker than contemporaneous lock-inclusion**.

Without the anchoring tier, grandfathered attestations get over-read as equivalent to template-locked ones. Both distinctions are mandatory structured fields, or the artifact manufactures provenance it cannot deliver.

---

## 4. Adoption path

rev4 re-routes **two fresh** cold passes (cold-pass-3 found gating items → count reset; author cannot clear). On adoption: standard judge template — **(sealed-loader, shared compute-core)** factoring; git-object-identity fail-closed self-guard; separated re-run guard; enforced runtime input-hash check; closed-world harness; four-file locked set; two-distinction signed attestation for grandfathered #1–#4. **Forward-looking; #1–#4 grandfathered without re-lock.** H1+T-2 adopt as one unit. The template build is kept **independent of the re-route-taxonomy decision** (no shared dependency, no deadline coupling). H1 is a **backstop, not a replacement** for the cold reader's judgment to decline execution; the result cold-pass protocol is unchanged.

## 5. Explicitly deferred / queued (unchanged)

- **Descriptor Justification Layer formalization: DEFERRED** to ≥1 more candidate (n=1=`pred` thin).
- **Class-C target-fit: OPEN** — roadmap not rule (RTVP realizes it as a separate instrument).
- **Community-validated rung (§6.3): QUEUED** sourcing thread.
- **Scope guard:** H1/T-2/attestation stay **template-scoped** (reviewed once, applied to #1–#4 uniformly), never retrofitted to #4 alone — which would repeat the asymmetry the design history already argued against.

---

## Appendix — cross-pass disposition (for the record)

**cold-pass-1** (rev1→rev2): single hard-refuse mechanism (flag deleted, stdout closed by refuse-before-compute, named-tag binding, "signed" overclaim corrected, output-exists separated); Seed-2 input surface + fixture/seed hashed; "end-to-end" downgraded; grandfather on precedent + signed attestation; taxonomy split out. Errors owned: override flag, "auditable end-to-end."

**cold-pass-2** (rev2→rev3): B1 git-object-identity (vs raw byte hash that false-refuses under autocrlf); B2 input constraint over all channels; B3 attestation retroactive/weaker labeling; results-shaped by content; output-exists home; input enforced not manifested.

**cold-pass-3** (rev3→rev4): three gating items folded. **(1)** B1 **fail-closed on every git-error path** (explicit test) — the one wrong-compute path; plus filter-aware `--path` comparison, `LOCK_TAG`/`LOCKED_PATH` pinned constants (not `__file__`), guard-is-first-statement, accident-not-tamper boundary, audit-log-not-sealed-value. **(2)** B2 **closed-world allowlist** (not denylist) with transitive-import/glob/deserialization channels subsumed and an IO audit. **(3)** Harness **shares the judge's compute-core** ((sealed-loader, shared-core) factoring) — else H1 leaves the judge un-smoke-tested until the irreversible run. **(B3)** two schema-enforced distinctions: claim-scope (synthetic verifiable / non-execution attested) **and** anchoring tier (new=anchored/proof-grade, grandfathered=unanchored/attestation-grade). Architecture affirmed stable; defects localizing to implementation leaves; author cannot clear; rev4 re-routes two fresh passes.
