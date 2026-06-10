# OVP v0.2 — Template Hardening (DRAFT rev2 — post cold-pass-1)

**Status:** DRAFT, revised after cold-pass-1. Subject to the program-evolution discipline (same bar as artifacts): re-routed cold passes before it hardens into the v0.2 standard. v0.1 and the locked detector arc are unchanged.

**Scope (narrowed at cold-pass-1).** This draft now folds **two** mechanical, structure-*adding* template seeds — both judge/lock script discipline that only *adds* guarantees:

1. **Sealed-run self-guard** (seed H1)
2. **Smoke-harness lock-inclusion** (seed T-2)

**Split out at cold-pass-1:** the **re-route-depth taxonomy** has been removed from this draft to its own thread (`OVP_REROUTE_DEPTH_REVIEW.md`). Cold-pass-1's decisive scope finding: that seed *relaxes* a safety invariant (two-independent-pass coverage of a fold's delta), which is a different — and higher — risk class than two guards that only add structure. Grouping them under "mechanism-independent, designable now" sorted on independence, not on risk-direction. A discipline-*relaxing* change earns its own adversarial pass; it does not ride this one.

**Still OUT of scope — deferred/queued (unchanged, see §5):** Descriptor Justification Layer formalization (defer to ≥1 more candidate); Class-C target-fit (open, roadmap not rule); community-validated sourcing (separate thread, position note recorded).

---

## 1. Seed 1 — Sealed-run self-guard

**Hazard (H1).** Every `judge_*.py` invocation computes the sealed verdict in memory and (default `--out`) writes a results file; the no-peeking seal on a real-candidate run rests on operator discipline + WARN text. Every other guard in the judge is structural; this one is not.

**Requirement.** A judge must **refuse to compute the sealed quantity unless its study is locked** — verified, not attested. The smoke harness (Seed 2) is the sole exemption (it computes nothing sealed).

**Mechanism — a single hard-refuse rule (the composition in rev1 was rejected at cold-pass-1).**

> **Compute the sealed quantity iff git positively verifies that *this study's named lock tag* exists and the running script's on-disk bytes hash-match that tag's committed blob. In every other state — git unavailable, the named tag missing, or a blob mismatch — hard-refuse before any sealed computation.** No override flag.

- **No flag.** rev1's `--unlocked-acknowledged` is deleted. It had no legitimate use case: the smoke harness already answers "does it run?", so there is never a reason to compute the *real* sealed value on an unlocked script — the flag was a pure intentional-peek path that reintroduced the exact discipline-dependence this seed exists to remove.
- **"No git → no sealed run" is a feature, not a gap.** The canonical sealed run should occur *only* where its provenance is verifiable; tarball/CI/detached-checkout cases are not environments in which to produce the locked verdict. Refuse there.
- **Refuse *before* compute.** Because the guard refuses before the sealed value is ever formed, there is no value to leak — closing the stdout/logs/pipe hole (`judge.py > out.json`) by construction, not by a "don't write" promise.
- **Bind to the *named* tag, not "any tag whose blob matches."** Blob identity is content-addressed (identical bytes ⇒ identical blob — robust to commit graph), but a judge byte-shared across studies must verify *its own* study's tag, or a sibling tag could satisfy it.
- **The guard's claim, stated precisely.** It verifies tag-existence + blob-identity — *when* (post-lock) and *which script bytes* — and **not** the tag's cryptographic signature (signature verification is the human-trust layer applied at lock, not the accident-prevention layer; rev1's "signed lock tag" phrasing over-promised what the check delivers). Input identity is the **manifest's** job, not this guard's. The guard is one link — *when/which-bytes* — in a chain whose other links (inputs, signature) live elsewhere.

**Orthogonal guard (separated out at cold-pass-1).** Output-exists refusal — refuse to overwrite an existing canonical results file — is a **single-execution / silent-re-run** guard, a *different property* than peeking. It belongs with the re-run discipline, not folded into the peek guard. Keep it; name it correctly.

**Self-charge (widened).** This seed's own cold pass must be free to **choose the mechanism**, not merely "stress the composition" — rev1 presupposed a composition it should have been free to reject (and was).

**Retroactive (#1–#4):** moot — see §3.

---

## 2. Seed 2 — Smoke-harness lock-inclusion

**Hazard (T-2).** A judge's no-peeking claim rests on its smoke being synthetic-only, but the smoke harness is not in the locked set, so an auditor cannot verify *from the locked record* that the smoke never touched the sealed candidate.

**Requirement.** The synthetic smoke harness is a **named file in the atomic lock commit**, hashed in the manifest. The locked set becomes **four files**: pre-registration, judge, smoke harness, manifest.

**What this does and does not buy (corrected at cold-pass-1 — rev1 overclaimed "auditable end-to-end").**
- It makes auditable: *is the harness source synthetic?* — yes, now provable from the locked bytes.
- It does **not** make auditable: *was nothing else run against the sealed candidate?* Under build-time (not single-execution) smoke, an operator could run a separate unlocked peeking script and still commit an innocent harness. No committed artifact can prove non-execution of things outside the set.
- **Honest claim:** *the locked artifacts (judge, harness) are auditable; non-execution of anything outside the locked set remains operator-attested.* The gap moves from "is the harness synthetic?" (now closed) to "did the operator run nothing else?" (still attested) — a real narrowing, not a closure.

**Harness properties (pinned, cold-checkable — strengthened at cold-pass-1):**
- **No candidate-redirect input surface.** The harness accepts **no parameter** that can point it at the real candidate (no `--input <path>`). Inputs are hardcoded or generated in-process — so the locked bytes cannot read clean while the *invocation* peeked (`smoke.py --input real_candidate.csv`).
- **Synthetic data is itself in the locked/hashed set.** If the harness loads a fixture, that fixture is hashed in the manifest; if it generates data, the generation seed is pinned *in the locked harness*. Otherwise the four-file set has a fifth, unaudited dependency that could carry real candidate data.
- exercises only synthetic null + synthetic-meaningful (+ foil-mechanic) checks; writes **no** output matching the judge's canonical `--out` schema (the positive definition of "results-shaped", so the refusal is testable);
- is the one script exempt from Seed 1's self-guard — an exemption made *safe* by the no-candidate-redirect input constraint above.

**Retroactive (#1–#4):** see §3.

---

## 3. Grandfather #1–#4 (no re-lock) + signed additive attestation

**Grandfather, do not re-lock — and the deciding argument is the program's own precedent.** Re-locking #1–#4 to add a now-moot guard or a fourth locked file would replace the exact bytes the cold readers cleared with new bytes, **destroying "locked == what was read"** — the very property the lock exists to guarantee. This is not a new judgment call: rc-v1 / ersaf / ct-v1 are unsigned and were **not** retroactively re-signed, precisely because re-tagging a locked study violates the immutability the lock guarantees. Grandfathering is therefore not just locally right but **consistency-required**. For the self-guard specifically the seal-relevant window is closed (runs complete), so the guard is genuinely moot for #1–#4.

**Signed additive attestation (the provenance-optimal strengthening).** Bare grandfathering leaves #1–#4's no-peeking operator-attested (their harnesses were not in the lock commits), and re-locking cannot fix that. A **signed, study-bound additive note** — recording each harness's hash and "this synthetic-only harness was the smoke for study X," tied to the original study **without re-tagging it** — captures the retroactive-auditability value at **zero cost to immutability**. (rev1's "committed as supplementary reference" stopped short of *signed* and *study-bound*; this is the same call, done right.)

---

## 4. Adoption path

This draft remains an artifact under the program-evolution discipline: re-routed cold passes (cold-pass-1 found blockers → count reset) before it hardens. On adoption it becomes the standard judge-study template (4-file locked set; single hard-refuse self-guard; separated re-run guard), **forward-looking** for new studies; **#1–#4 grandfathered without re-lock**, strengthened by the signed additive harness attestation. The re-route taxonomy is **not** part of this adoption — it is decided separately in its own thread.

---

## 5. Explicitly deferred / queued (unchanged)

- **Descriptor Justification Layer — spec-level formalization: DEFERRED** to ≥1 more mechanism-driven candidate (n=1 = `pred` is thin; freezing now bakes in #4's idiosyncrasies).
- **Class-C target-fit: EXPLICITLY OPEN** — roadmap to a Class-C worked example, not a frozen rule. (The RTVP charter, developed separately, is the realization of this roadmap as a distinct instrument.)
- **Community-validated rung (§6.3): QUEUED** as its own sourcing thread — moved by neither template hardening nor more internal candidates; position note in `OVP_DESIGN_HISTORY.md`.

---

## Appendix — cold-pass-1 disposition (for the record)

Single adversarial cold reader, process/template review. Findings accepted in full and folded: Seed 1 collapsed to a single hard-refuse mechanism (flag deleted, stdout closed by refuse-before-compute, named-tag binding, "signed" claim corrected, output-exists separated); Seed 2 input-surface constrained, fixture/seed hashed, "end-to-end" downgraded to "locked artifacts auditable, non-execution attested," "results-shaped" given a positive definition; grandfather landed on the rc-v1/ersaf/ct-v1 precedent + signed additive attestation; the re-route taxonomy split out as a higher-risk discipline-relaxing change deserving its own pass. The two errors owned: rev1's override flag (a peek path) and rev1's "auditable end-to-end" overclaim. Author cannot clear; rev2 re-routes fresh.
