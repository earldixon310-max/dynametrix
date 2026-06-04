# OVP — Observable Validation Protocol, v0.1 (Working Draft)

**Status:** Public working draft v0.1. Sits within AEPF (Avenridge Evaluation and Publication Framework); inherits AEPF's pre-registration, materialization manifest, single atomic lock commit, single-execution discipline, null-result publication parity, and constrained-interpretation reporting without modification.

**Author:** Earl Dixon · Avenridge Institute
**Date:** 2026-06-01

> **Drafting note.** This draft was authored from review of an earlier version and the program lineage; the five review corrections and the operator's three fork decisions — strict single measure pinned per version, restored controls-failure rejection path, symmetric arm thresholds — are incorporated. It is **not yet locked.** Per its own §7, it must pass an independent **cold-reader pass** — a reader with no design-conversation context, reading the on-disk artifact as a stranger would — before it is committed as v0.1. The spec's author (including the AI that drafted it) is the most context-saturated reader of it and cannot be that pass.

---

## 0. Purpose and scope

OVP decides one question, repeatably and honestly: **does a candidate observable carry structure beyond a simpler, pre-existing baseline observable derived from the same substrate — or is it redundant with that baseline, or indistinguishable from noise?**

A *candidate observable* is any derived quantity proposed to capture structure in a system (e.g., a graph-topology measure, a calibration statistic, a coherence/novelty term). OVP is the meta-protocol that the program kept re-deriving informally: RC_v1 asked whether graph topology `F` adds structure beyond pairwise consistency `C`; CT-v1 asked whether a novelty term adds structure beyond a baseline formula; the Dynametrix-HRRR gate asked whether a new predictor is redundant with an existing one. OVP abstracts the shared question — *does observable X exceed baseline B on the same substrate?* — and carries the hard-won lesson that **the discriminating instrument must itself be validated on synthetic ground truth before its verdicts on real candidates are trusted** (the CALIB_POSCONTROL lesson).

OVP does not decide whether an observable is *scientifically interesting* or *useful*; it decides only whether it is *non-redundant and non-spurious relative to a named baseline*. Interest and use are downstream judgments.

**OVP is an instrument, not the framework.** AEPF is the framework; the calibration audit and OVP are its first two instruments. The calibration audit asks whether a *probability* deserves trust given evidence and discipline; OVP asks whether an *observable* deserves trust given evidence and discipline — the same question, a different object. The framework is what makes the instruments comparable; the instruments are what make individual claims auditable. Each instrument earns the right to issue verdicts on real candidates only by first passing its own positive control (CALIB_POSCONTROL_v1 for the calibration audit; OVP_POSCONTROL_v1 for OVP). The question OVP operationalizes — whether a candidate quantity earns the status of *validated observable* within a given evidence base — is old (Reichenbach, Quine, Cartwright); what is new is the disciplined, falsifiable *procedure* for answering it.

---

## 1. The single operational measure (pinned per version)

OVP pins **exactly one operational measure per version — not per study.** A study does not choose its measure; the version fixes it. A choice of measure would be a degree of freedom, and OVP exists to remove degrees of freedom. **The version number carries the freedom; the study does not.**

**OVP v0.1's measure is Held-Out Discriminative Gain (HDG).** The candidate observable and the baseline are admitted to a pre-registered discrimination task, and HDG is the *out-of-sample* improvement the candidate adds over the baseline alone:

> HDG = (discrimination achieved by baseline + candidate) − (discrimination achieved by baseline alone), evaluated on a held-out split.

A candidate earns **Validated** only if HDG exceeds the pre-committed threshold on held-out data. Held-out evaluation is what makes HDG discriminating across the control arms (§4): a deterministic-redundant candidate adds no out-of-sample gain because the baseline already carries its information; a pure-noise candidate adds no out-of-sample gain because any in-sample fit fails to generalize; a genuinely meaningful candidate adds real out-of-sample gain. The exact computation — discrimination metric, split protocol, threshold — is pinned to the analysis script at lock.

Future operational measures — comparable-cell discrimination, calibration gain, information gain, and others — are **future versions** (OVP v0.2, v0.3, …), each pinning its single measure. They are not options inside v0.1. (The program's lineage studies used different measures — RC_v1 a pair-separation rate, CT-v1 an ablation correlation, HRRR an independence correlation — which is precisely why those are *lineage*, not OVP studies: see §9.)

---

## 2. Baseline Selection Rule (no post-hoc)

The baseline `B` against which the candidate is judged is selected and pinned in the pre-registration before any candidate-vs-baseline computation. A baseline selection is valid only if **all five** criteria hold:

1. **Same substrate.** `B` is derived from the same input substrate as the candidate.
2. **Strictly simpler.** `B` is simpler than the candidate — fewer parameters, lower structural complexity, or an established prior measure the candidate claims to improve upon.
3. **Pre-registered.** `B` is committed at the lock commit; no baseline may be substituted after lock.
4. **No post-hoc clause.** The candidate is never compared against a baseline chosen, tuned, or swapped after results are seen. A baseline change after lock invalidates the study and requires a new lock under a new tag.
5. **Ancestry Statement** *(review correction 3).* The candidate's pre-registration must include an explicit **Ancestry Statement** naming the simpler observable it claims to extend, and why — e.g., "`F` (pair-fraction-in-same-component) extends `C` (pairwise edge density): graph topology extends pairwise consistency." Baseline selection is **not valid without this statement.** It prevents a candidate from passing a technically-valid baseline check while never stating, on the record, what it claims to extend.

---

## 3. Verdict categories (tight)

Every OVP study returns exactly one verdict, under the locked decision rule:

- **Validated** — `D` exceeds the pre-committed threshold for incremental structure beyond the baseline. The candidate does work the baseline does not.
- **Redundant** — `D` is below the redundancy threshold; the candidate's structure is explained by (recoverable from) the baseline. It is not noise — it is the baseline wearing a more complex costume.
- **Rejected** — the candidate carries no validated structure relative to the substrate, by either of two **distinct** paths, recorded distinctly in the ledger:
  - **Rejected-A (noise-like):** no held-out discriminative gain over the baseline; the candidate is indistinguishable from noise on the operational measure.
  - **Rejected-B (controls failure):** the candidate fails a pre-registered required validation control (e.g., a substrate non-degeneracy or generator-sanity check), regardless of any apparent gain. A candidate can look useful and still be rejected here.
  These are different failure modes — a descriptor that performs no better than noise is not the same as one that fails a required control — and they are not collapsed.
- **Inconclusive** — the study completed but `D` falls in the pre-registered ambiguity band, or statistical power was insufficient to discriminate. Recorded as such and published with the same parity as any other verdict.

The four categories are mutually exclusive and jointly exhaustive given a completed run; a technical failure to run is a separate documented condition (AEPF single-execution discipline), not a verdict.

---

## 4. Control arms and per-arm pass thresholds (instrument-validation studies)

Before any **real** candidate is judged, the protocol itself is validated against synthetic ground truth. An OVP instrument-validation study (the first being **OVP_POSCONTROL_v1**) runs the locked decision rule over synthetic arms whose correct verdicts are known by construction, across `R` replications under one master seed.

**Arms (constructions pinned in the study):**

- **Arm 1 — Known-meaningful.** A candidate constructed to carry genuine incremental structure beyond the baseline (structure the baseline provably cannot recover). Correct verdict: **Validated**. (Positive control; bounds the false-*reject* rate / Type-II floor.)
- **Arm 2 — Deterministic-redundant.** A candidate that is a deterministic function of the baseline, carrying no incremental information by construction. Correct verdict: **Redundant**. (Specificity; bounds the false-*validate* rate against redundancy.)
- **Arm 3 — Partial-redundancy.** A candidate mostly determined by the baseline but carrying a small, known increment. **Characterization-only — not gated**, because the "correct" verdict is genuinely ambiguous near the boundary; this arm maps the protocol's sensitivity gradient rather than passing or failing.
- **Arm 4 — Pure-noise.** A candidate random/independent of the substrate's structure. Correct verdict: **Rejected**. (False-discovery floor.)

**Per-arm pass thresholds** *(review addition 4).* The spec **requires** every OVP instrument-validation study to pre-commit a pass threshold for each gated arm, **stratified by property** (per the AEPF v1.1 lesson — no single conjunction across heterogeneous arms). OVP_POSCONTROL_v1 commits:

| Arm | Property tested | Correct verdict | Pre-committed bar |
|---|---|---|---|
| 1 — known-meaningful | sensitivity (Type-II floor) | Validated | ≥ 90 / 100 replications |
| 2 — deterministic-redundant | specificity vs redundancy | Redundant | ≥ 90 / 100 replications |
| 3 — partial-redundancy | sensitivity gradient | (none) | characterization-only, reported not gated |
| 4 — pure-noise | false-discovery floor | Rejected | ≥ 90 / 100 replications |

The spec names that the requirement exists; each instrument-validation study fills the numbers. A near-miss on a gated bar is reported as a near-miss (the CALIB_POSCONTROL discipline: no kinder seed, no softened threshold), and the soundness-vs-power distinction is documented rather than collapsed.

---

## 5. The OVP ledger (fields named)

Every OVP verdict — synthetic or real — is recorded as one row in the public OVP ledger, with:

- **study_id** and lock tag
- **candidate observable**: name + definition hash (pinned analysis code)
- **baseline observable**: name + the candidate's **Ancestry Statement**
- **substrate**: pinned dataset/model/manifest identifiers (revision-level)
- **operational measure** `D`: name, value, and the pre-committed thresholds
- **verdict**: one of {Validated, Redundant, Rejected, Inconclusive}
- **cross-pass record**: both independent verification-pass verdicts (Section 7), including any divergence
- **operator**: author identity of the candidate (for the independence criterion, Section 6)
- **date**

Redundant, Rejected, and Inconclusive rows are recorded with the same standing as Validated rows. The ledger's value is precisely that it does not hide the costumes-and-noise.

---

## 6. Convergence criterion (when OVP is an established instrument)

*(review correction 2 — three non-redundant conditions, each measuring a different property.)* OVP is considered an established, usable instrument when **all three** hold:

1. **Synthetic correctness.** OVP_POSCONTROL_v1 passes, under the per-arm thresholds of Section 4.
2. **Ledger volume.** At least **three real candidate-observable verdicts** are in the ledger, of **any outcome** (Validated, Redundant, Rejected, or Inconclusive). The verdict type cannot be pre-committed for real candidates — the protocol determines it — so only the *count of completed real verdicts* is committed here.
3. **Operator independence.** At least **one** of those three real verdicts is for a candidate **not authored by the principal operator**.

The three conditions measure distinct properties — synthetic correctness, ledger volume, operator independence — and none is implied by another.

---

## 7. Cross-pass discipline (in-spec)

*(review addition 5 — preserving the AEPF v1.1 lesson the program earned through worked example, the RC_v1 §10 cold-reader catch.)*

Every OVP study — instrument-validation and candidate-validation alike — must undergo **two independent verification passes**, by reviewers with **no overlapping design-conversation context** (the "cold reader" requirement: at least one reviewer reads the locked artifacts directly, not the design narrative). Warm review catches mechanical drift; it is not the independence gate.

**Diverging verdicts between the two passes are themselves recorded in the ledger** (Section 5), not silently reconciled. A divergence is data about the study's clarity and the reviewers' independence, and suppressing it would discard the exact signal the discipline exists to surface.

---

## 8. Inheritance from AEPF

Unchanged from AEPF and assumed here: the pre-registration, analysis script, and materialization manifest are committed in a single atomic lock commit and signed tag; the study runs once (single-execution); technical failures are documented and amended under a new tag, never silently re-run; every verdict — including Redundant, Rejected, and Inconclusive — is published with positive-result parity; and interpretation is constrained to what the locked measure and decision rule support.

---

## 9. Status and the gate

v0.1 working draft. **OVP_POSCONTROL_v1 is the protocol's own positive control and must pass (Section 4) before any real candidate verdict is admitted to the ledger.** Until then, no candidate-observable verdict produced under OVP may be cited as established.

**The OVP ledger begins empty.** RC_v1, CT-v1, and the Dynametrix-HRRR gate are **lineage**, not OVP studies: they are the worked problems from which this protocol was abstracted, and each used a *different* operational measure (a pair-separation rate, an ablation correlation, an independence correlation) than the one OVP v0.1 pins (§1). They are cited as ancestry — the reason the protocol has the shape it does — but they are **not** retroactively entered as OVP verdicts, and the convergence count of §6 starts at zero. The discipline is the same one the program applied throughout: clean history over retroactive claims. The ledger fills only with studies run *under* OVP, prospectively, after this spec is locked.

**Cold-reader gate (per §7).** This draft has not yet passed an independent cold-reader pass and is therefore not locked. Its author — including the AI collaborator that drafted it — is the most context-saturated reader of it and cannot serve as that pass. The cold reader must receive the on-disk spec **only**: no design conversation, no lineage notes beyond what the document itself states, no rationale supplied out of band. Locking to v0.1 follows the cold pass and the recording of any divergence (§7).

*End of OVP v0.1 working draft.*
