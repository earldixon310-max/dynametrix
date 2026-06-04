# OVP — Observable Validation Protocol, v0.1 (Working Draft)

**Status:** Public working draft v0.1 — **not locked** (the gate for locking is in §9). Sits within AEPF (Avenridge Evaluation and Publication Framework); inherits AEPF's pre-registration, materialization manifest, single atomic lock commit, single-execution discipline, null-result publication parity, and constrained-interpretation reporting without modification.

**Author:** Earl Dixon · Avenridge Institute
**Date:** 2026-06-01

> Editorial and design history is kept in version control and in `OVP_DESIGN_HISTORY.md`, deliberately **outside** this artifact, so that the spec can be cold-read per §7/§9 — by an independent reader receiving the spec body alone, with no design narrative supplied in band.

---

## 0. Purpose and scope

OVP decides one question, repeatably and honestly: **does a candidate observable carry structure beyond a simpler, pre-existing baseline observable derived from the same substrate?**

**Scope of this version.** OVP **v0.1** answers exactly that binary — structure beyond the baseline, or not. It deliberately does *not* yet separate the two ways a candidate can fail to add structure (being *redundant* with the baseline vs. being *indistinguishable from noise*); that separation requires a second pinned statistic and is the defined job of **v0.2** (§1, §9). Stating the binary v0.1 can support, and naming what it cannot, is itself the discipline.

A *candidate observable* is any derived quantity proposed to capture structure in a system (e.g., a graph-topology measure, a calibration statistic, a coherence/novelty term). OVP abstracts the shared form of the question — *does observable X exceed baseline B on the same substrate?* — and carries the lesson that **the discriminating instrument must itself be validated on synthetic ground truth before its verdicts on real candidates are trusted.**

OVP does not decide whether an observable is *scientifically interesting* or *useful*; it decides only whether a candidate adds out-of-sample structure beyond a named baseline, as measured by the version's pinned measure under a study-pinned estimator. A v0.1 verdict is therefore conditional on the pinned choices that instantiate the measure — in particular the baseline and the function class used to compute `D` (§1). A candidate Not-Validated under a linear estimator and Validated under a nonlinear one is not a contradiction; it is two legitimate, separately-recorded questions. (Separating *redundant* from *spurious* is a further thing v0.1 does not do — that is v0.2.) Interest and use are downstream judgments.

**OVP is an instrument, not the framework.** AEPF is the framework; the calibration audit and OVP are its first two instruments. The calibration audit asks whether a *probability* deserves trust given evidence and discipline; OVP asks whether an *observable* deserves trust given evidence and discipline — the same question, a different object. The framework is what makes the instruments comparable; the instruments are what make individual claims auditable. Each instrument earns the right to issue verdicts on real candidates only by first passing its own positive control (CALIB_POSCONTROL_v1 for the calibration audit; OVP_POSCONTROL_v1 for OVP).

---

## 1. The single operational measure (pinned per version)

OVP pins **exactly one operational measure per version — not per study.** A study does not choose *which statistic* decides its verdict; the version fixes that. What removes a degree of freedom here is the elimination of the choice of statistic: a study may not introduce a second, different statistic into the verdict (e.g., bolting a recoverability term onto HDG) — capability that needs a second statistic earns a **new version**, not a second pin inside this one. **The version number carries that freedom; the study does not.**

**Two levels, kept distinct.** "One measure per version" governs the *form* of the measure, not every numerical choice that instantiates it:

- **Fixed by the version (the measure):** OVP v0.1's measure is **Held-out Discriminative Gain (HDG), denoted `D`** — the out-of-sample improvement the candidate adds over the baseline alone:
  > `D` = HDG = (discrimination by baseline + candidate) − (discrimination by baseline alone), evaluated on a held-out split.
  No v0.1 study may substitute a different statistic for `D`.
- **Pinned per study at lock (the instantiation):** the concrete **discrimination metric** (e.g., AUC, log-loss, R² — necessarily substrate-dependent, since a metric fit for a binary target is not fit for a continuous one); the **model / function class** used to compute `D` (verdicts can flip between, e.g., a linear and a nonlinear estimator, so the estimator is a pinned element, not an implementation detail); the **held-out split protocol**; and the two **decision cut points** (below). These are pre-registered, declared before any result is seen, governed by external provenance (below), and never chosen, tuned, or swapped post-hoc.

Instantiating the *same* measure differently across substrates (HDG-via-AUC here, HDG-via-R² there) is **not** the same as pinning a *second* measure: both still ask one question — "how much out-of-sample discrimination does the candidate add over the baseline?" That is why per-study instantiation does not violate one-measure-per-version, while a second statistic would.

**The split protocol** must itself pin: the partition method (e.g., single held-out split, k-fold, blocked/grouped CV), the train/test fraction or fold count, any blocking or grouping required to prevent leakage between baseline and candidate, and the seed — all at lock.

**Decision cut points.** The verdict is read from `D` against two pinned cut points, the validation edge `τ_hi` and the not-validated edge `τ_lo`, with `0 < τ_lo ≤ τ_hi`. `τ_lo` is pinned **strictly positive** so that zero or negative out-of-sample gain — a candidate that adds nothing, or actively harms held-out discrimination — falls in **Not-Validated**; this is what makes the "`D` ≈ 0 → Not-Validated" guarantee hold rather than merely assert it. The pre-registered ambiguity band is the closed interval `[τ_lo, τ_hi]`.

**Cut-point provenance.** `τ_lo` and `τ_hi` are derived from a source *external* to the study they govern — established theory, a prior published study, or a separate pre-lock calibration study run under its own lock and seed — and that source is named in the pre-registration. They are never set from the study's own runs, and in particular never from the noise arm of the positive control they are later meant to vindicate: using Arm 4 to fix the bar Arm 4 must then clear is post-hoc by §2's own logic. The no-tuning rule binds the cut points' movement after results; the provenance rule anchors their origin before lock. The two together keep the threshold from floating free.

**What v0.1's one measure deliberately cannot do.** `D` separates Validated from Not-Validated, but it is blind to *why* a candidate is Not-Validated: a deterministic-redundant candidate and a pure-noise candidate both yield `D` ≈ 0. Distinguishing *redundant* (recoverable from the baseline) from *noise* (no structure at all) requires a **second** statistic — a baseline-recoverability measure — and a second statistic is a new version by the rule above. That capability is therefore scoped to **OVP v0.2** (= v0.1 + a pinned baseline-recoverability statistic + the four-verdict structure of Validated / Redundant / Rejected / Inconclusive). v0.1 honestly reports the binary it can support; v0.2 adds the mechanism layer. Other future measures — comparable-cell discrimination, calibration gain, information gain — are likewise their own versions, each pinning a single measure.

---

## 2. Baseline Selection Rule (no post-hoc)

The baseline `B` against which the candidate is judged is selected and pinned in the pre-registration before any candidate-vs-baseline computation. A baseline selection is valid only if **all five** criteria hold:

1. **Same substrate.** `B` is derived from the same input substrate as the candidate.
2. **Strictly simpler.** `B` is simpler than the candidate — fewer parameters, lower structural complexity, or an established prior measure the candidate claims to improve upon.
3. **Pre-registered.** `B` is committed at the lock commit; no baseline may be substituted after lock.
4. **No post-hoc clause.** The candidate is never compared against a baseline chosen, tuned, or swapped after results are seen. A baseline change after lock invalidates the study and requires a new lock under a new tag.
5. **Ancestry Statement.** The candidate's pre-registration must include an explicit **Ancestry Statement** naming the simpler observable it claims to extend, and why — e.g., "`F` (pair-fraction-in-same-component) extends `C` (pairwise edge density): graph topology extends pairwise consistency." Baseline selection is **not valid without this statement.** It prevents a candidate from passing a technically-valid baseline check while never stating, on the record, what it claims to extend.

---

## 3. Verdict categories (tight)

Every OVP **v0.1** study returns exactly one of **three** verdicts, read from `D` (HDG) against its two pinned cut points `τ_lo ≤ τ_hi` (§1):

- **Validated** — `D` > `τ_hi`: the candidate adds out-of-sample structure beyond the baseline. The candidate does work the baseline does not.
- **Not-Validated** — `D` < `τ_lo`: the candidate adds no demonstrated out-of-sample structure beyond the baseline. Deliberately **mechanism-agnostic** — it covers both a candidate redundant with the baseline and one indistinguishable from noise, because v0.1's single measure cannot tell those apart (§1). Distinguishing the two is the job of v0.2.
- **Inconclusive** — `τ_lo ≤ D ≤ τ_hi`: `D` falls in the pre-registered ambiguity band, or power was insufficient to place `D` cleanly on either side. Recorded as such and published with the same parity as any other verdict.

The three regions partition the real line at `τ_lo` and `τ_hi`, so the categories are mutually exclusive and jointly exhaustive given a *valid* completed run.

Two conditions sit **outside** the verdict set and are documented, not scored as verdicts: a **technical failure to run** (AEPF single-execution discipline), and a **required-control failure** — a pre-registered validation control (e.g., a substrate non-degeneracy or generator-sanity check) that does not behave as required, which invalidates the run rather than judging the candidate (you cannot trust any verdict from an instrument that failed its own setup check). A control-failed study is documented and amended under a new lock tag, never silently re-run.

**Versioning note.** v0.2 will replace the mechanism-agnostic **Not-Validated** with the two-way distinction **Redundant** (recoverable from the baseline) vs **Rejected** (noise-like), once a second statistic — baseline-recoverability — is pinned. v0.1's three verdicts and v0.2's four verdicts are an explicit, designed progression, not an accident of scope.

---

## 4. Control arms and per-arm pass thresholds (instrument-validation studies)

Before any **real** candidate is judged, the protocol itself is validated against synthetic ground truth. An OVP instrument-validation study (the first being **OVP_POSCONTROL_v1**) runs the locked decision rule over synthetic arms whose correct verdicts are known by construction, across **`R` replications** under one master seed. `R` is pinned per study; OVP_POSCONTROL_v1 pins **R = 100**.

**How the arms relate to the cut points.** For a per-arm pass bar to mean anything, each gated arm's construction must place `D` on the correct side of the band — but `D` is a statistic computed on finite, partly-random data, so this placement is **distributional, not per-replication deterministic**. Each gated arm pins the *distribution* of `D` (its expected value plus enough margin) on the intended side of the band; the per-arm bar (e.g., ≥90/100) then measures how often the *realized* `D` lands correctly under sampling scatter. The bar is precisely the allowance for that scatter — not slack in a guarantee. If a gated arm cannot be shown a priori to place its expected `D` clear of the band in the intended direction, its bar is untestable and the arm is mis-specified.

**Arms (constructions pinned in the study):**

- **Arm 1 — Known-meaningful.** A candidate constructed to carry genuine incremental structure beyond the baseline (structure the baseline provably cannot recover), with expected `D` above `τ_hi` by a pinned margin. Correct verdict: **Validated**. (Positive control; bounds the false-*reject* rate / Type-II floor.)
- **Arm 2 — Deterministic-redundant.** A candidate that is a deterministic function of the baseline, carrying no incremental information by construction, with expected `D` below `τ_lo`. Correct v0.1 verdict: **Not-Validated**. (Specificity; bounds the false-*validate* rate against a redundant candidate.)
- **Arm 3 — Partial-redundancy (Inconclusive witness).** A candidate mostly determined by the baseline but carrying a small, known increment, constructed so its expected `D` targets the ambiguity band `[τ_lo, τ_hi]`. **Non-gated**, because the "correct" verdict near the boundary is genuinely ambiguous — but its verdict distribution across replications is reported as a **band-occupancy** check: the fraction of replications landing Inconclusive (vs. spilling to Validated or Not-Validated) is recorded. This **exercises** the third verdict under its intended condition and maps the protocol's sensitivity gradient.
- **Arm 4 — Pure-noise.** A candidate random/independent of the substrate's structure, with expected `D` ≈ 0 (hence below the strictly-positive `τ_lo`). Correct v0.1 verdict: **Not-Validated**. (False-discovery floor.)

Arms 2 and 4 both correctly return **Not-Validated** in v0.1, by construction undifferentiated as to mechanism: both place `D` below `τ_lo`, and v0.1's single measure does not distinguish "redundant with the baseline" from "indistinguishable from noise." That is exactly the binary v0.1 claims to validate — meaningful structure vs. its absence — and the positive control rings true on it. The mechanism-distinguishing layer (separating these two arms into Redundant vs Rejected) is what **OVP_POSCONTROL_v2** will validate, once v0.2 pins the second statistic.

**Per-arm pass thresholds.** Every OVP instrument-validation study must pre-commit a pass threshold for each gated arm, **stratified by property** (no single conjunction across heterogeneous arms). OVP_POSCONTROL_v1 commits:

| Arm | Property tested | Correct v0.1 verdict | Pre-committed bar |
|---|---|---|---|
| 1 — known-meaningful | sensitivity (Type-II floor) | Validated | ≥ 90 / 100 replications |
| 2 — deterministic-redundant | specificity vs redundant candidate | Not-Validated | ≥ 90 / 100 replications |
| 3 — partial-redundancy | sensitivity gradient + Inconclusive witness | (none — band occupancy reported) | non-gated; report fraction landing in `[τ_lo, τ_hi]` |
| 4 — pure-noise | false-discovery floor | Not-Validated | ≥ 90 / 100 replications |

The spec names that the requirement exists; each instrument-validation study fills the numbers. A near-miss on a gated bar is reported as a near-miss (no kinder seed, no softened threshold), and the soundness-vs-power distinction is documented rather than collapsed.

All three v0.1 verdicts are **exercised** by this control — Validated (Arm 1), Not-Validated (Arms 2/4), Inconclusive (Arm 3) — so none ships without having fired at least once under a known condition. The two gated verdicts are additionally **certified** by their pass bars; Inconclusive is exercised and its band-occupancy reported, but not gated (a non-gated arm with no single correct answer certifies nothing — it witnesses). An over-wide band is bounded indirectly anyway: Arm 1 would start missing its Validated bar. What Arm 3 adds is confirmation that the band fires correctly when it should, which no other arm can supply.

---

## 5. The OVP ledger (fields named)

Every OVP verdict — synthetic or real — is recorded as one row in the public OVP ledger, with:

- **study_id** and lock tag
- **candidate observable**: name + definition hash (pinned analysis code)
- **baseline observable**: name + the candidate's **Ancestry Statement**
- **substrate**: pinned dataset/model/manifest identifiers (revision-level)
- **operational measure** `D`: the HDG value; the discrimination metric, model/function class, and split used to compute it; and the pinned cut points `τ_lo`, `τ_hi` with their external provenance (§1)
- **verdict**: one of {Validated, Not-Validated, Inconclusive} (v0.1), plus a flag if the run was invalidated by a control failure
- **cross-pass record**: both independent verification-pass verdicts (§7), including any divergence
- **operator**: author identity of the candidate (for the independence criterion, §6)
- **date**

Not-Validated and Inconclusive rows are recorded with the same standing as Validated rows. The ledger's value is precisely that it does not hide the negatives.

**Cross-row comparability.** `D` is scaled by the study-pinned discrimination metric, which differs across studies (§1); raw `D` values are therefore **not comparable between rows**, and neither are cut points. Only **verdicts** compare across the ledger. A reader ranking studies by `D` magnitude is reading noise.

---

## 6. Convergence criterion (the maturity ladder)

OVP's standing is read on a three-rung ladder, each rung a distinct, separately-checkable property. The rungs use distinct words on purpose, so "usable" never carries two meanings:

1. **Self-validated** — **OVP_POSCONTROL_v1 passes**, under the per-arm thresholds of §4. The instrument is sound against synthetic ground truth.
2. **Operational** — self-validated **and** at least **three real candidate-observable verdicts** are in the ledger, of **any outcome** (Validated, Not-Validated, or Inconclusive). The verdict type cannot be pre-committed for real candidates — the protocol determines it — so only the *count* of completed real verdicts is committed here. At this rung the instrument is usable by its operator and has a track record, but its independence is not yet demonstrated.
3. **Community-validated** — operational **and** at least **one** of those real verdicts is for a candidate **not authored by the principal operator**.

The three rungs measure distinct properties — synthetic correctness, ledger volume, operator independence — and none is implied by another. A study or claim must state which rung OVP currently occupies; it may not call a self-validated-only instrument "community-validated."

**Honest note on independence (the binding constraint).** For a single-principal-operator institute, rung 3 (an externally-authored candidate) and §7's cold-reader requirement are the hardest parts of this protocol to satisfy, and the spec does not pretend otherwise. Independence here is **sourced**, not assumed: an acceptable external author is a person or model that did not participate in designing the candidate observable or this protocol, and an acceptable cold reader is one with no exposure to the design conversation. How independence was sourced and verified for each study — who the external party was and what they did and did not have access to — is recorded in the ledger row (§5) so the claim can be audited rather than taken on faith.

---

## 7. Cross-pass discipline (in-spec)

Every OVP study — instrument-validation and candidate-validation alike — must undergo **two independent verification passes**, by reviewers with **no overlapping design-conversation context** (the "cold reader" requirement: at least one reviewer reads the locked artifacts directly, not any design narrative). Warm review catches mechanical drift; it is not the independence gate. The cold reader receives the spec and locked artifacts **only** — no design conversation, no rationale supplied out of band (design history is kept outside the artifact for exactly this reason; see the front-matter note and `OVP_DESIGN_HISTORY.md`).

**Diverging verdicts between the two passes are themselves recorded in the ledger** (§5), not silently reconciled. A divergence is data about the study's clarity and the reviewers' independence, and suppressing it would discard the exact signal the discipline exists to surface.

---

## 8. Inheritance from AEPF

Unchanged from AEPF and assumed here: the pre-registration, analysis script, and materialization manifest are committed in a single atomic lock commit and signed tag; the study runs once (single-execution); technical failures are documented and amended under a new tag, never silently re-run; every verdict — including Not-Validated and Inconclusive — is published with positive-result parity; and interpretation is constrained to what the locked measure and decision rule support.

---

## 9. Status and the gate

v0.1 working draft. **OVP_POSCONTROL_v1 is the protocol's own positive control and must pass (§4) before any real candidate verdict is admitted to the ledger.** Until then, no candidate-observable verdict produced under OVP may be cited as established.

**The OVP ledger begins empty.** RC_v1, CT-v1, and the Dynametrix-HRRR gate are **lineage**, not OVP studies: they are the worked problems from which this protocol was abstracted, and each used a *different* operational measure than the one OVP v0.1 pins (§1). They are not retroactively entered as OVP verdicts, and the convergence count of §6 starts at zero. Clean history over retroactive claims. The ledger fills only with studies run *under* OVP, prospectively, after this spec is locked. (Lineage detail is recorded in `OVP_DESIGN_HISTORY.md`, outside this artifact.)

**v0.2 design seed (recorded, not yet built).** **OVP v0.2 = v0.1 + a pinned baseline-recoverability statistic + the four-verdict structure** (Validated / Redundant / Rejected / Inconclusive), validated by OVP_POSCONTROL_v2 in which Arms 2 and 4 separate into Redundant and Rejected. v0.2 is not started and nothing here commits to it; it is logged so the version progression is explicit and the redundant-vs-noise capability has a known home rather than leaking back into v0.1.

**Cold-reader gate (per §7).** This draft has not yet passed an independent cold-reader pass on its current form and is therefore not locked. Its author — including the AI collaborator that drafted and revised it — is the most context-saturated reader of it and cannot serve as that pass. The cold reader must receive the **spec body only**. Locking to v0.1 follows the cold pass and the recording of any divergence (§7).

*End of OVP v0.1 working draft.*
