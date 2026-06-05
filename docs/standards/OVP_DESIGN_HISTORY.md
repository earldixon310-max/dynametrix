# OVP — Design History (out-of-artifact)

This file holds the design narrative and editorial history of the Observable Validation Protocol (OVP) spec. It is kept **separate from the spec itself** on purpose: the spec (`OVP_v0.1_OBSERVABLE_VALIDATION_PROTOCOL.md`) must be cold-readable per its own §7/§9 — handed to an independent reader as a stranger would read it, with no design conversation, lineage notes, or rationale supplied out of band. Design narrative embedded *inside* the spec would defeat that gate (this was itself a cold-reader finding). So the "why" lives here; the spec carries only the "what."

## Lineage

OVP abstracts a question the program kept re-deriving informally:
- **RC_v1** — does graph topology `F` add structure beyond pairwise consistency `C`? (measure: a pair-separation rate)
- **CT-v1** — does a novelty term add structure beyond a baseline formula? (measure: an ablation correlation)
- **Dynametrix-HRRR gate** — is a new predictor redundant with an existing one? (measure: an independence correlation)

Each used a *different* operational measure, which is precisely why they are **lineage, not OVP studies**: they motivate OVP and the ledger begins empty (spec §9). The deeper lesson carried forward is CALIB_POSCONTROL's: the discriminating instrument must itself be validated on synthetic ground truth before its verdicts on real candidates are trusted.

The question OVP operationalizes — whether a candidate quantity earns the status of *validated observable* within a given evidence base — is old (Reichenbach, Quine, Cartwright). What is new is the disciplined, falsifiable procedure.

## Revision history

**Draft → working draft (the one-measure / four-verdict episode).** An early draft pinned a single measure (HDG) but declared four verdicts. The first independent cold-reader pass found this structurally impossible: a redundant candidate and a noise candidate both sit at HDG ≈ 0, so one scalar cannot separate them. Two resolutions were weighed:
- *Option 1* — pin a second statistic (baseline-recoverability) and keep four verdicts. Rejected: a second pinned statistic is a second degree of freedom even when pinned, and it would make a three-statistic v0.3 defensible by the same logic. The version mechanism exists to carry that expansion *across* versions, not within one.
- *Option 2* (adopted) — hold strict one-measure-per-version; v0.1 returns **three** verdicts (Validated, Not-Validated, Inconclusive), with the redundant-vs-noise distinction deferred to **v0.2** (= v0.1 + a pinned baseline-recoverability statistic + the four-verdict structure). The cold pass thereby handed v0.2 its design seed.

Control-failure was reclassified from a fourth verdict to a run-invalidating documented condition (you cannot trust any verdict from an instrument that failed its own setup check).

**Second cold-reader pass (assembled-draft read).** A fresh isolated reviewer, given the spec file and nothing else, returned four blocking findings, all accepted and fixed in the spec:
1. *Identity contradiction* — "one measure per version" vs "metric differs across studies" were never reconciled. Fixed by separating the version-fixed **measure form** (HDG) from the study-pinned **instantiation** (concrete metric, estimator/function class, split protocol, cut points), and noting that instantiating the same measure across substrates is not the same as pinning a second measure.
2. *τ_lo unanchored* — "D ≈ 0 → Not-Validated" only holds if τ_lo > 0, which was unstated. Fixed by pinning τ_lo strictly positive.
3. *Self-defeating cold-reader gate* — the artifact contained design narrative (the Drafting note + inline "(review …)" annotations) that the gate forbids the cold reader from seeing. Fixed by moving all design narrative to this file and stripping the inline scaffolding.
4. *By-construction vs 90/100* — a random noise arm cannot be guaranteed below τ_lo every replication. Fixed by pinning the arm's D-*distribution* (expected value + margin) on the correct side; the ≥-of-R bar is the allowance for sampling scatter.

Smaller fixes from the same pass: Arm 3 reworded from "certifies" to "exercises/witnesses" the Inconclusive verdict (a non-gated arm certifies nothing); `R` defined (replications per study; OVP_POSCONTROL_v1 pins R = 100); split-protocol contents specified; and §6's overloaded word "usable" split into a three-rung ladder — **self-validated** (positive control passes) → **operational** (self-validated + ≥3 real ledger verdicts) → **community-validated** (operational + ≥1 externally-authored candidate).

**Third cold-reader pass (external, post-extraction read).** A fresh external reader, given the rewritten spec body alone, returned two blocking findings in the verdict machinery plus three lesser, all accepted and fixed:
1. *Inconclusive had a second, undefined entry route* — "or power was insufficient to place D cleanly" let a study return Inconclusive on non-D grounds, breaking the "partition the real line / read from D" claim and invoking an unpinned power/CI instrument. Fixed: the verdict is now a deterministic function of the single value `D` against the two cut points; the power disjunct is removed; uncertainty is handled by band placement and characterized by the positive control, not by a verdict-time test.
2. *"Discrimination" had no pinned orientation* — log-loss (lower-is-better) was an admitted example metric, which would invert the sign of `D` and break the `τ_lo` guarantee. Fixed: discrimination is pinned higher-is-better; natively lower-is-better metrics are admitted only in negated/skill-score form.
3. *Provenance satisfiability for the first study* — with an empty ledger and different-measure lineage, the first HDG study (OVP_POSCONTROL_v1) had no obvious admissible cut-point source. Fixed: the **separate pre-lock calibration study** bootstrap path is named explicitly.
4. *"Validation/validated" overloaded* — against §6's own "distinct words" boast. Fixed the two sharpest collisions: "validation edge τ_hi" → "upper cut point"; "validation control" → "setup control."
5. *§5 comparability vs §0* — "only verdicts compare" was in mild tension with §0's "a flip is two different questions." Fixed: verdicts compare only as categorical outcomes, each conditional on the row's pinned baseline/metric/estimator.

The reader also confirmed what holds: boundary handling (Inconclusive closed, the two verdicts open) genuinely partitions for the D-based rule; the v0.1/v0.2 scoping, second-statistic-is-a-new-version rule, gated-vs-witness arm logic, and anti-post-hoc provenance reasoning are internally coherent.

**Fourth cold-reader pass (external).** A fresh external reader, spec body alone, returned three local blockers plus two clarity collisions and a scoping note — none architectural; the reader stated that with these fixed it would be "lockable on internal-consistency grounds." All accepted and fixed:
1. *§2(2) simplicity loophole* — "strictly simpler" admitted "an established prior measure the candidate claims to improve upon," which need not be simpler, weakening every "beats baseline" verdict. Fixed by subordinating the established-prior clause to the simplicity bar (eligible only if no more complex than the candidate).
2. *§4 over-claimed Inconclusive coverage* — asserted all three verdicts "fired at least once," but Arm 3 (the only Inconclusive source) is non-gated, so zero landings are permitted. Fixed: Inconclusive is *targeted but not gated*; band-occupancy is reported; zero occupancy is a recorded calibration finding, not a silent pass.
3. *§1 permitted τ_lo = τ_hi* — collapsing the ambiguity band to a measure-zero point, making Inconclusive unreachable. Fixed: strict inequality `τ_lo < τ_hi` required.
4. *"Positive control" double-used* — study-level (OVP_POSCONTROL_v1) vs Arm 1. Fixed: Arm 1 renamed "sensitivity arm"; "positive control" reserved for the study.
5. *"Binary" vs three verdicts* — §0 called the question binary while §3 lists three. Fixed: Inconclusive framed as an *abstention* from the binary, not a third answer.
Scoping note (not a defect): §8 inherits AEPF terms the body never defines. Added a pointer that they are defined in the parent AEPF spec, supplied among the locked artifacts per §7.

Convergence trend across passes: four structural findings → two blockers + three localized → three local blockers + two clarity, none architectural. Defects are shrinking and localizing toward the leaves of the document.

## Pre-committed lock bar (pinned 2026-06-04, before the fifth pass)

The stopping rule for OVP v0.1 was pre-registered **before** the next cold read, so the read's result cannot move it: **the spec locks as v0.1 when an external cold pass returns no finding that falls in the lock-blocker set defined below.** The label "no lock-blocker = lock" is not self-sufficient; the discipline lives in pre-committing *what counts as a blocker*, so the classification is fixed at the moment of reading rather than negotiated after. The cold reader is shown this taxonomy **before** reading the spec and classifies each finding against it as they read.

**Lock-blocker (returns the document to revision; no lock):**
- Internal contradiction (two sections specifying inconsistent things)
- Defect in the operational measure `D`'s definition, threshold/cut-points, or model/function-class pinning
- Defect in the verdict categories (the three v0.1 verdicts; mutual exclusivity; joint exhaustiveness)
- Defect in the convergence-criterion conditions (§6 ladder)
- Defect in the cross-pass §7 specification
- Defect in §4's control-arm constructions or thresholds
- Anything that materially changes what `OVP_POSCONTROL_v1` would test

**Non-blocker (document locks; finding logged for a v0.x revision queue):**
- Wording, clarity, or readability improvement
- v0.2 design suggestion
- Additional example or worked-instance suggestion
- Stylistic inconsistency
- Forward-looking note about future-version capability
- Improved framing of an honest limitation

If the cold pass returns only non-blockers, the spec locks and the non-blockers go into a v0.x revision queue (not folded in before lock, so the locked artifact is exactly the one that was read). If even one lock-blocker is returned, the spec does not lock; it is revised, and earns a fresh pass under this same bar. The fix-author (including the AI collaborator) cannot be the clearing reader.

**Rationale for Option 1 over the alternatives** (recorded so the choice itself is auditable): zero-findings (Option 2) is asymmetric and likely unattainable — a careful cold reader almost always finds *something*, so the bar would equate a disengaged skim with a careful clean read, and would tend to fail on first attempt and become its own moving target. Two-reader concordance (Option 3) is the right bar for first-time validation of a novel instrument, but is wrong-sized for a *confirmatory* pass on an already-cold-reviewed structure where the open question is narrow (does the three-verdict reshape hold together?); §6's own independence note flags the single-operator sourcing constraint, so requiring two readers here costs timeline without proportional gain. Option 1 with a pinned blocker definition is the proportionate, pre-committed choice.

## Fifth cold-reader pass (external, confirmatory — the clearing read)

Run under the pre-committed bar above (pinned at commit `c806c2e` *before* this read). The external reader was shown the lock-blocker taxonomy first and classified each finding at the moment of finding. Result: **no lock-blocker.** Four findings, all non-blockers:

1. §2(2) — "strictly simpler" (forbids equal complexity) vs the established-prior clause's "no more complex" (permits it): a wording inconsistency within the criterion. *Non-blocker (clarity).*
2. §6 — "none is implied by another" (about the three *properties*) juxtaposed with rungs that are cumulative; defensible as written, but invites misreading. *Non-blocker (clarity/framing).*
3. §1 vs §4 — "the seed" (singular) vs "one master seed" over R=100 replications; consistent, but the singular/master relationship is left implicit. *Non-blocker (clarity).*
4. v0.2 material (baseline-recoverability, four-verdict structure, OVP_POSCONTROL_v2) — explicitly scoped out of v0.1. *Non-blocker (future-version; no action — confirms scoping is working as intended).*

The reader's passed checks (recorded as positive evidence): D and its orientation/τ_lo guarantee; the strict cut-point ordering and non-circular bootstrap provenance; the three-verdict real-line partition with failures correctly outside the verdict set; §4 arm constructions/thresholds aligned to the cut points with cut points not sourced from Arm 4; and the §7 cross-pass spec consistent with the §5 ledger and the design-history exclusion.

**Disposition under the bar:** the spec is cleared to lock as **v0.1**. The four non-blockers are **not** folded in before lock (the locked artifact is exactly the one that was read); they enter the v0.x revision queue below.

### v0.x revision queue (deferred; do not fold in before lock)
- [v0.x] §2(2): reconcile "strictly simpler" with "no more complex" — pick one complexity relation and use it consistently.
- [v0.x] §6: separate the "distinct properties" claim from the cumulative-rungs structure so the disclaimer can't be misread as "the rungs don't imply each other."
- [v0.x] §1/§4: state explicitly that the single pinned "seed" is the master seed from which per-replication draws are derived.
- [v0.x] (no action) confirm v0.2 scope note remains accurate when v0.2 is opened.

## LOCK RECORD — OVP v0.1

**Status: LOCKED.** OVP v0.1 (`OVP_v0.1_OBSERVABLE_VALIDATION_PROTOCOL.md`) was locked on **2026-06-04** at signed tag **`ovp-v0.1-lock`**.

- **Cleared by:** the fifth external cold pass, which returned **no lock-blocker** under the bar pinned at `c806c2e` (before the read). Four non-blocker findings, queued above for v0.x.
- **Lock mechanics (decided deliberately):** *tag-only, byte-exact.* The spec body is **unmodified** from the version the cold reader cleared — its front matter still reads "working draft — not locked" by design. Editing even the status line would have broken the pre-committed "locked artifact = exactly what was read" property and set a precedent for carving exceptions out of "exactly." The lock is therefore carried by the signed tag, `OVP_v0.1_LOCK_NOTICE.md`, and this record — never by touching the reviewed file.
- **Independence:** the fix-author (including the AI collaborator) did not serve as the clearing reader.
- **Signed-tag discipline begins here (honest asymmetry).** `ovp-v0.1-lock` is the program's **first cryptographically signed** lock tag (SSH signing). The prior lock tags — `rc-v1-lock`, `ersaf-v1.0-lock`, `ct-v1-lock` — are **annotated but unsigned**, created under the earlier practice; the AEPF docs' "signed git tag" language was, until now, aspirational rather than literal for those locks. They are **not** retroactively re-signed: re-tagging a locked study would itself violate the immutability the lock exists to guarantee. The asymmetry is recorded plainly — those tags carried the discipline available at the time; OVP v0.1 inherits a spec whose §8 says "signed," so its lock is actually signed, and signed-tag discipline starts at this tag going forward.
- **Convergence ladder (§6):** OVP is **not** yet self-validated — locking the *spec* is distinct from passing `OVP_POSCONTROL_v1`. The instrument earns "self-validated" only when the positive control passes, "operational" at three real verdicts, "community-validated" with an externally-authored candidate. The locked spec is the rulebook; the rungs are still ahead.

## Standing discipline

The spec is **not locked**. Per §7/§9, locking to v0.1 requires an independent cold-reader pass on the spec body alone, with any divergence recorded. The spec's author — including the AI collaborator that drafted and revised it — is the most context-saturated reader and cannot be that pass. Each revision above that changed structure earned a fresh cold read; this file records that history so the spec need not.
