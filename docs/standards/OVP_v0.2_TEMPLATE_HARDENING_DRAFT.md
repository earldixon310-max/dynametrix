# OVP v0.2 — Template Hardening (DRAFT — not adopted)

**Status:** DRAFT. Subject to the program-evolution discipline (`OVP_DESIGN_HISTORY.md` — "program-evolution changes get the same discipline as artifacts"): this document gets its own adversarial cold-pass cycle **before** it hardens into the v0.2 standard. v0.1 and the locked detector arc are unchanged by this draft.

**Scope (deliberately tight).** This draft folds the **three template-hardening seeds** that are ready — operational script-and-lock discipline, mechanism-independent, designable now against known failure cases:

1. **Sealed-run self-guard** (seed H1, from DETECTOR_PREDCLASS_OVP CP1-post-fold)
2. **Smoke-harness lock-inclusion** (seed T-2, from CP2-post-fold)
3. **Re-route-depth taxonomy for narrow folds** (seed, from CP2-N1)

**Explicitly OUT of scope — deferred/queued (see §5):** the Descriptor Justification Layer's spec-level formalization (one first-contact application is thin evidence — deferred to ≥1 more mechanism-driven candidate); the Class-C target-fit question (no Class-C candidate exists yet — kept explicitly open with a roadmap, not a frozen rule); the community-validated sourcing problem (§6.3 operator-independence — a sourcing question, not template work — queued as its own thread with a position note).

**Why fold these three now.** Each is motivated by a concrete cold-pass finding; none depends on a specific candidate mechanism (anyone could trigger them on any judge script); the design choices can be evaluated against the failure cases already on record. On adoption they apply uniformly via one template-level review rather than per-candidate retrofit. That is the cheap, high-value half of v0.2.

---

## 1. Seed 1 — Sealed-run self-guard

**Hazard (recorded H1).** Every invocation of a `judge_*.py` computes the sealed verdict (HDG-beyond-baseline) in memory and (default `--out`) writes a results file. The no-peeking seal on a *real-candidate* run therefore rests on operator discipline + WARN text: an idle pre-lock "does it run?" both peeks and emits a result. Every other guard in the judge is structural (hash-guarded inheritance, runtime cut-point assert, 3-way revision identity); this one is not.

**Requirement.** A judge script must **refuse to compute the sealed quantity unless its study is locked** — i.e., the study's signed lock tag exists and points at the script's own committed bytes. The synthetic smoke harness (Seed 2) is the sole exemption: it computes nothing sealed.

**Mechanism evaluation (the four candidates on record).**

| mechanism | strength | failure modes |
|---|---|---|
| (a) lock-tag git check (tag exists ∧ points at script's own commit/blob hash) | strongest — self-evidencing, tied to the actual lock | git unavailable: fresh-clone-before-tags, tarball/zip checkout, CI without git, detached states |
| (b) env-var gate set by the lock procedure | no git dependency | weak — env is trivially set by accident; not self-evidencing |
| (c) `lock_status` sentinel file committed at lock | in-repo, git-light | needs its own integrity story; a stray sentinel re-enables |
| (d) output-file-exists refusal | cheap; blocks silent re-run/overwrite | does **not** prevent the in-memory peek — partial only |

**Proposed mechanism: a composition, refuse-by-default with a loud, no-silent-results fallback.**
- **Primary — lock-tag check.** On startup the judge attempts: does the study's lock tag exist *and* does the committed blob of this script at that tag match the running script's bytes? If git is available and the answer is no → **HARD REFUSE** (no sealed computation, exit non-zero). This covers the real threat: the operator's own pre-lock "does it run?" on a machine where git is present.
- **Fallback — git unavailable.** The script cannot self-verify, so it must (i) require an explicit `--unlocked-acknowledged` flag, (ii) print a loud banner, and (iii) **refuse to write any results-shaped output** — so an accidental or exploratory run can never masquerade as the locked run's artifact. Absent the flag, refuse.
- **Always-on — (d) output-exists refusal.** Refuse to overwrite an existing canonical results file, guarding against silent re-run regardless of git state.
- **Rationale.** The threat model is the operator's accidental pre-lock invocation *on their own machine, where git exists* — so (a) covers the real risk; the fallback degrades safely (refuse-by-default, explicit-noisy-override, no silent results) rather than offering false security via a weak gate.

**Template shape.** A standard `assert_locked_or_refuse(lock_tag, this_file)` called once before any sealed computation; the smoke harness never calls it. Spec to be pinned in the template module; cold pass to stress the git-blob-identity check and the fallback's "no silent results" guarantee.

**Retroactive application (#1–#4).** Forward-looking. **#1–#4 are grandfathered, not re-locked** — their runs are complete and committed, so the seal-relevant window has *closed* and the guard is moot for them; re-locking to add a now-moot guard would needlessly churn their lock provenance (new judge bytes → new manifest → invalidated original tag). The guard becomes mandatory for v0.2-onward studies. (Design call flagged for the cold pass: confirm "grandfather, don't re-lock" is the right provenance-preserving choice.)

---

## 2. Seed 2 — Smoke-harness lock-inclusion

**Hazard (recorded T-2).** A judge's no-peeking claim rests on its build-and-smoke being synthetic-only (the smoke loads substrate-shape inputs and never the real candidate). But the smoke harness is not in the locked set (only pre-reg + judge + manifest), so a future auditor **cannot verify from the locked record** that the smoke never touched the sealed candidate. The judge-side is auditable; the smoke-side is taken on the operator's word.

**Requirement.** The synthetic smoke harness is a **named file in the atomic lock commit**, hashed in the manifest's `artifacts` list — making no-peeking auditable end-to-end from the locked record. **The locked set becomes four files:** pre-registration, judge, **smoke harness**, manifest.

**Harness required properties (pinned, cold-checkable):**
- loads only the substrate-shape inputs the smoke needs (e.g. `B, y`) and **never** the real candidate column(s) or the sealed feature;
- exercises only synthetic null + synthetic-meaningful (+ any foil-mechanic) checks;
- writes **no** results-shaped output that could be confused with the locked run's artifact;
- is the **one** script exempt from Seed 1's self-guard (computes nothing sealed).

**Interaction with Seed 1.** Together they make no-peeking both *enforced* (the judge refuses to peek pre-lock) and *auditable* (the locked harness proves the smoke was synthetic-only). The two seeds are complementary halves of one no-peeking guarantee.

**Retroactive application (#1–#4).** Forward-looking; **not re-locked.** Any #1–#4 smoke harness not already tracked is committed as **supplementary reference** (tracked, available for audit) without re-locking the original tags — preserving original provenance. #1–#4 ran under operator discipline (which held); their harnesses become reference artifacts, not retro-added locked-set members. (#4's `smoke_synthetic_predclass.py` is already tracked from its records commit.)

---

## 3. Seed 3 — Re-route-depth taxonomy for narrow folds

**Recurring pattern + hard constraint (recorded).** Reviews keep producing "cold pass finds a substantive-but-non-gating issue → fold → full warm + two-cold re-route." The full re-route is the correct conservative default and was applied as written every time (verdict-#3 ancestry fold; CP2-N1). The open question: is there a *principled* middle tier for folds that are **substantive in meaning but narrow in surface**? **Hard constraint:** any such tier must NOT become "clear-modulo by another name" — the bar set at the truncation NB1 fold (*the locked artifact is exactly the one that was read*) cannot erode, and the fix-author can never self-certify a change as "narrow enough."

**Proposed three-tier taxonomy.**

- **Tier C — full re-route (warm + two cold). Default for SUBSTANTIVE folds.** Any change to a gating rule, a pinned constant/seed, the estimator, a computation, a measurement, OR the *meaning* of a pre-committed interpretation. (On record: σ_m grid, AP orientation, bootstrap removal, ε_null encoding, CP2-N1.) When in doubt → Tier C.
- **Tier B — one fresh cold pass + a pre-committed ripple-site checklist. NEW middle tier, for NARROW folds.** A change that is *provably* single-section and **not** substantive in the Tier-C sense — only a precision / completeness / propagation tightening of an *already-locked* commitment. Requires **all** of the narrowness test below, **and** one fresh independent cold reader who verifies both the change and that the enumerated ripple set is complete — and who can **escalate to Tier C** if the change is broader than attested. Fix-author cannot clear. *One* cold read on the final bytes (not two), so "the locked artifact is exactly what was read" still holds.
- **Tier A — no new pass; prescribed-fix verified by the next already-scheduled pass. PURELY EDITORIAL.** Whitespace/formatting/typo, or a fix **explicitly prescribed by a cold reader and applied verbatim**, verified by the next pass already in the pipeline. (On record: the 65/33 fix, the foil-fraction symmetry add, CP1-post-fold's four fixes, #3's N1/N2.) No new independent pass because the change was reader-prescribed and is mechanically checkable.

**The narrowness test (pre-committed; gates Tier B — fail any ⇒ Tier C):**
1. touches exactly one section, provably (diff-scoped);
2. no change to any gating rule, pinned constant, seed, estimator, computation, or measurement;
3. does **not** create or alter the *meaning* of a pre-committed interpretation — only tightens precision/completeness/propagation of an already-locked one;
4. the fix-author writes an explicit ripple-site enumeration (every section the change could touch);
5. an independent cold reader confirms (1)–(4) and is empowered to escalate.

**Self-check (the taxonomy reproduces the calls we already made by judgment).** Substantive folds (σ_m, AP, bootstrap, ε_null, CP2-N1) → Tier C, as run. The 65/33 fix, foil-fraction symmetry, CP1-post-fold fixes, #3's N1/N2 → Tier A/B, as run (prescribed/narrow, not full-re-routed). The taxonomy does not *loosen* any call already made; it *names* the floor so the next instance is a designed rule, not an improvisation — and it keeps an independent reader on the final bytes in every tier.

---

## 4. Adoption path

This draft is itself an artifact under the program-evolution discipline: **it gets an adversarial cold-pass cycle before it hardens.** On adoption it becomes the standard judge-study template (4-file locked set, self-guard, ripple-checklist for Tier-B folds), forward-looking for new studies; **#1–#4 grandfathered without re-lock** (guards moot post-run; harnesses committed as reference). The standard cold-pass charge for *this* document: stress the self-guard's git-blob-identity check and fallback; confirm the 4-file locked set + harness properties are auditable; pressure the narrowness test for any "clear-modulo by another name" leak; confirm the grandfather-not-re-lock provenance choice.

---

## 5. Explicitly deferred / queued (NOT in this draft)

- **Descriptor Justification Layer — spec-level formalization: DEFERRED.** Exactly one first-contact application (#4 = `pred`); the structure held, but one data point is thin for freezing the Layer's rules (Ancestry shape, foil construction, interpretation pattern vary by mechanism). Formalizing now would bake in #4's idiosyncrasies. Stays a **seed-being-exercised** until ≥1 more mechanism-driven candidate's first contact tests it across a different mechanism.
- **Class-C target-fit: EXPLICITLY OPEN.** No Class-C (organizational/regime) candidate exists in the ledger. Kept as an open methodological question with a **roadmap to a Class-C worked example** (a different target — regime transition / behavioral break — or a parallel instrument), not a frozen v0.2 rule.
- **Community-validated rung (§6.3 operator-independence): QUEUED as its own thread.** A *sourcing* problem — externally-authored input the principal operator did not design — that is moved by **neither** template hardening **nor** more internal candidates. Position note recorded in `OVP_DESIGN_HISTORY.md`; not v0.2 spec work.
