# OVP v0.2 — Template Hardening (DRAFT rev3 — post cold-pass-2)

**Status:** DRAFT, revised after cold-pass-2 (which returned three blockers, all fixable without redesign — the architecture was affirmed). Subject to the program-evolution discipline: rev3 re-routes **two fresh** cold passes on the new bytes before it hardens. v0.1 and the locked detector arc are unchanged.

**Scope.** Two mechanical, structure-*adding* judge/lock seeds: **Seed 1 — sealed-run self-guard (H1)** and **Seed 2 — smoke-harness lock-inclusion (T-2)**. **They adopt together, not independently** (see §2.5): H1's harness exemption is non-relaxing *only* because T-2's input constraint guarantees the harness cannot reach the candidate.

**Split out (own thread):** the re-route-depth taxonomy (`OVP_REROUTE_DEPTH_REVIEW.md`) — a discipline-*relaxing* change, higher risk class, its own pass.

**Deferred/queued (unchanged, §5):** Descriptor Justification Layer formalization; Class-C target-fit; community-validated sourcing.

---

## 1. Seed 1 — Sealed-run self-guard

**Hazard (H1).** Every `judge_*.py` invocation computes the sealed verdict and (default `--out`) writes it; the no-peeking seal rests on operator discipline + WARN text. Every other guard is structural; this one is not.

**Requirement.** A judge **refuses to compute the sealed quantity unless its study is locked** — verified, not attested. The smoke harness (Seed 2) is the sole exemption.

**Mechanism — single hard-refuse rule, by git *object identity* (not raw byte hash — cold-pass-2 B1).**

> Let `LOCK_TAG` be a constant string **pinned inside the locked script bytes** (the script names its own study's tag, so script→tag→blob is a fixpoint the lock fixes). Compute the sealed quantity **iff** all hold, else **hard-refuse before any sealed computation**:
> 1. `LOCK_TAG` exists as a tag in the repo;
> 2. the judge's working-tree file is **git-object-identical** to the blob recorded for its tracked path at that tag — i.e. `git hash-object <judge_file>` (which applies git's clean-filter/normalization) equals `git rev-parse LOCK_TAG:<judge_tracked_path>`. **Not** `sha256(open(file,'rb'))` — a raw byte hash mismatches under `autocrlf`/gitattributes filters and would false-refuse a legitimate locked run (the common Windows case).

No override flag (rev1's `--unlocked-acknowledged` stays deleted: the harness already answers "does it run?", so computing the *real* sealed value on an unlocked script has no legitimate use). Refusing *before* the value is formed closes the file/stdout/pipe/log leak by construction.

**Required companions to the comparison (cold-pass-2 B1-adjacent + minors):**
- **Pin `.gitattributes` for the judge path** (deterministic normalization across checkouts), so (2) is stable.
- **Name the canonical-run environment:** a full clone with the signed `LOCK_TAG` fetched locally. "No git → refuse" is a *feature* only because the canonical verdict is produced *only* where provenance is verifiable; a shallow/tagless CI runner is correctly not such an environment.
- **Path resolution:** the comparison is against the judge's *tracked path* in the tag's tree; a post-lock file move invalidates and must be handled explicitly (re-verify), not silently refused.

**Scope of the guarantee, stated precisely (cold-pass-2):**
- It closes every leak path **for the sealed quantity** — because the value is never formed pre-lock. It does **not** hide *precursors* computed before the refuse point (the disclosed marginal, baseline-only discrimination); those are visible **by design** (the marginal is disclosed). "Closes every peek path" means *of the sealed quantity*, not of inference about it from disclosed precursors.
- It secures **when** (post-lock) and **which script bytes** — **not** the tag's **signature** (signature is the human-trust layer at lock, disclaimed here) and **not** input identity (the manifest's job, §1b).
- **Boundary, stated plainly so the guard is not over-read as tamper-proof:** a self-issued `LOCK_TAG` or deleting the guard bypasses it. That residual is correctly the signature/human-trust layer's job; the guard converts "a peek is one casual run away" into "a peek requires deliberately forging the named lock tag or editing the guard out" — the intended structure-over-discipline upgrade, nothing more.

## 1b. Adjacent required elements (so the chain has no soft link — cold-pass-2 residual)

- **Single-execution / re-run guard (the separated output-exists refusal) has a home here.** Refuse to overwrite an existing canonical results file. It is a *different property* than peeking and lives as a named element of this template (not orphaned by the split from the peek guard). Composition check: post-lock canonical run computes (tag verifies) and writes (no prior output); any second run refuses on output-exists. Clean.
- **Input identity must be *enforced*, not merely manifested.** H1 hands input identity to the manifest — correct scoping — but "the manifest's job" is only real if the judge **verifies input hashes against the manifest/locked anchors at runtime** (as the detector judges already do: `verify_cut_points`, `load_inherited` hash-verify). The template **requires** this runtime input-hash check, so a locked script cannot compute against wrong inputs while the guard happily passes. Enforced, not attested.

**Self-charge (open).** This seed's cold pass chooses/stresses the *mechanism* (B1 and the self-issued-tag boundary were mechanism-level findings, not composition tweaks) — it does not presuppose a design.

**Retroactive (#1–#4):** moot — §3.

---

## 2. Seed 2 — Smoke-harness lock-inclusion

**Hazard (T-2).** A judge's no-peeking claim rests on its smoke being synthetic-only, but the harness is not in the locked set — so an auditor cannot verify *from the locked record* that the smoke never touched the sealed candidate.

**Requirement.** The synthetic smoke harness is a **named file in the atomic lock commit**, hashed in the manifest. The locked set is **four files**: pre-registration, judge, smoke harness, manifest.

**Harness input constraint — over ALL channels (cold-pass-2 B2; this is what makes H1's exemption safe).**
> The harness reads **no redirectable external input of any kind** — no CLI parameter, environment variable, stdin, network fetch, or external file path (hardcoded or cwd-relative). Its **only** inputs are bytes literal in the locked source, or data generated in-process from a **seed pinned in the locked source**.

Stating it only as "no `--input`" (rev2) closed the CLI redirect but left env/stdin/path/network channels open; an exempt script with *any* live channel to the real candidate is a peek path routing around H1. The exemption is safe *only* under the all-channel constraint above.

**Synthetic data in the locked/hashed set:** a loaded fixture is hashed in the manifest, or generation uses a seed pinned in the locked harness — else the four-file set has a fifth, unaudited dependency that could carry real candidate data.

**What this buys, claimed honestly (cold-pass-2 affirmed; if anything under-claims, the safe direction):**
- *Auditable:* is the harness source synthetic? — yes, provable from the locked bytes; and the four-file lock binds *which* harness to *this* study (provenance).
- *Still attested:* non-execution of anything *outside* the locked set. No committed artifact proves the operator ran nothing else against the candidate. (With H1 in place the judge itself leaves the attested set pre-lock — it refuses — narrowing the residual to ad-hoc non-judge scripts.)
- **Claim:** *the locked artifacts are auditable; non-execution of anything outside the locked set remains operator-attested.*

**"Results-shaped" defined on content/schema, not filename** (cold-pass-2 minor) — the judge's canonical `--out` schema — so a rename cannot dodge a refusal.

## 2.5 H1 + T-2 adopt together (coupling — cold-pass-2)

H1 and T-2 are **not independent**. H1 exempts the harness from the self-guard; that exemption is non-relaxing **only because** T-2's all-channel input constraint guarantees the harness cannot reach the candidate. **You cannot adopt H1 without T-2's (corrected) input constraint**, or H1's exemption becomes an unguarded peek path. They are reviewed and adopted as one unit.

---

## 3. Grandfather #1–#4 (no re-lock) + signed additive attestation

**Grandfather, do not re-lock — consistency-required.** Re-tagging #1–#4 to add a now-moot guard or a fourth locked file replaces the exact bytes the cold readers cleared, destroying "locked == what was read." Precedent governs: rc-v1 / ersaf / ct-v1 were **not** retroactively re-signed, because re-tagging a locked study violates the immutability the lock guarantees. The precedent carries the **re-tagging prohibition**; the attestation does the **retroactive-auditability** work — two jobs, correctly separated.

**Signed additive attestation — and it must carry its post-hoc status on its face (cold-pass-2 B3).** A signature applied *now* authenticates *who asserts the claim and when (now)* — it does **not** prove the historical fact that harness H was the smoke for study X *back then* (there was no contemporaneous anchor; the harness was not in the original locked set). So the attestation MUST state on its face that it is:
- **retroactive**, dated now, not part of study X's original locked set;
- a record of the operator's **post-hoc identification** of the smoke harness;
- **explicitly weaker than contemporaneous lock-inclusion** (authenticates the assertion, not the history);
- claiming **only** what Seed 2's downgraded claim allows — *harness source synthetic* (provable from the now-hashed bytes), **not** non-execution of anything else (unprovable retroactively, exactly as in the forward case).

With that label it informs without misleading; without it, a signed "study-bound" note manufactures the appearance of contemporaneous provenance it cannot deliver. (Mechanically — zero re-tagging, separate signed artifact referencing by hash — it preserves immutability; the only defect was what the artifact says about itself.)

---

## 4. Adoption path

rev3 re-routes **two fresh** cold passes (cold-pass-2 found blockers → count reset; author cannot clear). On adoption: standard judge template (4-file locked set; git-object-identity self-guard; separated re-run guard; enforced runtime input-hash check), **forward-looking**; **#1–#4 grandfathered without re-lock**, strengthened by the labeled signed additive attestation. H1 and T-2 adopt as one unit (§2.5). The re-route taxonomy is decided separately.

## 5. Explicitly deferred / queued (unchanged)

- **Descriptor Justification Layer formalization: DEFERRED** to ≥1 more mechanism-driven candidate (n=1 = `pred` too thin).
- **Class-C target-fit: OPEN** — roadmap, not rule (RTVP, developed separately, is its realization as a distinct instrument).
- **Community-validated rung (§6.3): QUEUED** sourcing thread; position note in `OVP_DESIGN_HISTORY.md`.

---

## Appendix — cross-pass disposition (for the record)

**cold-pass-1** (rev1→rev2): collapsed Seed 1 to a single hard-refuse mechanism (deleted the override flag, closed stdout by refuse-before-compute, named-tag binding, corrected the "signed" overclaim, separated output-exists); constrained Seed 2's input surface + hashed the fixture/seed + downgraded "end-to-end" to "locked artifacts auditable, non-execution attested"; landed grandfather on precedent + signed additive attestation; split out the re-route taxonomy as a higher-risk discipline-relaxing change. Errors owned: rev1's override flag and "auditable end-to-end" overclaim.

**cold-pass-2** (rev2→rev3): three blockers, all folded without redesign. **B1** — git-object-identity comparison (`git hash-object` vs `LOCK_TAG:<path>`) replaces the raw byte hash that would false-refuse under `autocrlf`; pinned `.gitattributes`; named canonical-run environment; path-resolution + tag-name-pinned-in-locked-bytes fixpoint; signature-omission boundary and sealed-quantity-only scope stated. **B2** — input constraint restated over *all* channels (CLI/env/stdin/path/network), which is what makes H1's harness exemption safe (now explicit as a coupling, §2.5). **B3** — the signed attestation must carry its retroactive / weaker-than-contemporaneous / Seed-2-claim-scoped status on its face, or it forges contemporaneous provenance. Plus tighten-ups: results-shaped by content not filename; output-exists guard given a definite home; input identity enforced (runtime hash check) not merely manifested. Architecture affirmed; author cannot clear; rev3 re-routes two fresh passes.
