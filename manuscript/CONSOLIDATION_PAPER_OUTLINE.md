# Outline (DRAFT v0) — Consolidation Paper

**Working title:** *Measuring Latent Properties Without Fooling Yourself: An Evaluation Architecture and Its Worked Negatives.*

**Thesis (one sentence).** Across four substrates (atmospheric organization, cosmological residuals,
LLM-detector reliability, retrieval provenance) the recurring scientific question is not "can we predict
X" but "can a proposed latent property be **measured independently of the observable it is meant to
explain**" — and answering it credibly required an evaluation architecture whose principal output, so far,
is a body of *trustworthy negatives* plus a structural account of why such negatives are likely.

> The paper's honesty is its argument: it reports that the program has produced **no validated descriptor
> yet**, and shows that this is a result about the search space, not a failure of the instrument.

---

## 1. Introduction — measurement vs. fit
- The confusion the program exists to dissolve: *interesting pattern* ≠ *predictive information* ≠
  *measurement*. A fit is scored by reproducing the observable; a measurement by capturing what the
  observable does not already give you.
- The invariant question: *can a latent property be measured independently of the observable it explains?*
  Instantiated as: weather/precipitation, ERSAF/ΛCDM, OVP/confidence, RTVP/its own descriptor.
- Claim: the contribution is **architecture, not any single descriptor.**

## 2. The architecture
- The funnel: **characterize (y-free) → calibrate → evaluate.** Cheap descriptive work eliminates weak
  candidates before expensive calibration; the verdict is sealed behind a no-peeking firewall.
- Components: AEPF (is the claim worth testing) · Candidate Provenance / Descriptor Justification (mechanism,
  information source, orthogonality, surface control, failure prediction) · OVP (does the observable add
  information) · RTVP (is there an independent transition) · Control Library · Findings Ledger ·
  Observable Registry · Design Canon. **Framed as principles + minimal apparatus, not a "measurement OS."**

## 3. OVP in depth (the verdict instrument)
- Held-out Discriminative Gain over a baseline; standardized-logistic estimator; paired splits; frozen band.
- The lock discipline: pre-registration, structural no-peeking, single-execution, the H1 byte-identity
  self-guard, permuted-foil + confound diagnostics, signed tags.
- **Tier-1 / Tier-2** gating: gate steerability + operative accuracy; fix prose precision in place.

## 4. Worked examples (the results carry the paper)
- **LLM-detector arc (#1–#5).** Every endogenous scalar Not-Validated/Inconclusive; `perturbation_spread`
  (multi-pass) the sharpest case — *confidence already absorbs it* (D = −0.0071, scope-stamped 1785/2000).
- **Calibration methodology.** How a band that defines "real gain" is established on a substrate, and why
  it does not transfer across substrates.
- **Evidence Provenance Stage 0.** The first *exogenous*-source candidate; the y-free funnel caught a
  **structurally degenerate** observable (sum-normalized BM25 entropy, sd = 0.0027) for zero calibration
  compute — the discipline working, and the degenerate-arm refinement (broken-pipeline vs variance-less-observable).
- **Weather origin (Dynametrix).** CT-v1 and the calibrated verification record (CSI 3%, Brier worse than
  climatology): the project that *forced* the methodology. Principal outcome methodological, not meteorological.

## 5. A structural theory of negatives
- **Confidence is the model's own self-assessment** — the strongest single-forward-pass baseline. Anything
  computed downstream of the same computation is suspect of being **pre-absorbed during training**, hence
  redundant by construction.
- Corollary (the design principle): **a YES almost has to come from information exogenous to the model's
  training** — cross-model disagreement, human disagreement, external retrieval, deployment shift.
- The Observable Registry as the empirical ledger of this claim: all endogenous candidates closed; the
  exogenous frontier open.

## 6. Methodological discoveries (transferable beyond any substrate)
- Necessary-condition-vs-process-descriptor (gate the first, disclose the second).
- The claim↔code audit and its failure modes: stale docstrings; the unachievable guarantee ("never in
  memory"); summary/abstract drift; the **exhaustive-negative** trap (and its recursion — the log that
  catches the log).
- **Execution catches what static review cannot:** the H1 wrong-file-resolution defect, invisible to nine
  static passes, surfaced only by running H1 against the real repository at lock time.
- The degenerate-arm refinement (Sec 4).

## 7. What this establishes / does not
- **Does:** a reusable architecture for honestly adjudicating latent-property observables, substrate-
  independent at the level of *principles* (residualize, baseline, no-peek, lock, ledger); a structural
  account of why same-information-space observables null; a set of rigorous, reproducible negatives.
- **Does not:** validate any descriptor; claim the apparatus (band/foil/estimator) ports without rework
  across substrates; resolve whether atmospheric organization, detector reliability, or retrieval
  provenance possess measurable latent structure — those remain open, now askable with rigor.

## 8. Limitations & future
- No positive result yet; the exogenous frontier untested at the verdict level; the dynamic-range
  retrieval-ambiguity successor (dormant). Apparatus-vs-principle transfer is itself a research question.

## Appendices
- A: locked artifacts + signed tags (OVP #1–#5, calibration, Evidence-Provenance Stage 0).
- B: the Findings Ledger and the Observable Registry.
- C: the Design Canon / discipline rules (Tier-1/Tier-2, no-peeking, single-execution, exhaustive-negatives).

---

*Next: agree the framing and section order, then draft Section 4 (the worked examples) first — it is the
spine, it is entirely from locked material, and writing it will show whether any section is missing.*
