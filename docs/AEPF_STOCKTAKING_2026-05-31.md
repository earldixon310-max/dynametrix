# AEPF — An Honest Stocktaking ("How powerful is this hammer?")

**Date:** 2026-05-31
**Author:** Earl Dixon (assessment drafted collaboratively)
**Status:** Internal assessment. Not a locked result. Grounded in direct reading of the on-disk artifacts listed below, not from memory.

---

## 0. Why this document

After three consecutive non-positive outcomes (Dynametrix-HRRR gated out, CT-v1 structurally inert, RC_v1 a clean null), the question stopped being "why does my hypothesis keep breaking" and became "how strong is the instrument that keeps breaking it." This is an attempt to answer that honestly — strengths, thin spots, and what AEPF can and cannot legitimately claim — by auditing the framework's own track record under its own discipline.

Sources read for this assessment: `docs/standards/AEPF_v0.1_WORKING_DRAFT.md` (the spec); `papers/AEPF/AEPF.tex` (the manuscript); and the outcome records `RESULT_GW_v1`, `RESULT_GW_QUIETWELL_v1`, `RESULT_DISTILBERT_SST2_v1`, `RESULT_TOXIC_BERT_v1`, `RESULT_CHATGPT_DETECTOR_ROBERTA_v1`, `RESULT_ERSAF_v1`, the `DIAGNOSTIC` documents for Dynametrix-HRRR and CT-v1, and `RESULT_RC_v1`.

---

## 1. Two things that were not as remembered

**(a) There are two "AEPF"s, and they do not match.** The committed specification (`docs/standards/AEPF_v0.1_WORKING_DRAFT.md`) defines AEPF as the **Evidence Preservation Format** — a narrow attestation format whose abstract states plainly: "AEPF is an evidence-preservation specification, not a certification framework," and which deliberately "does not specify the methodology to be evaluated, the metrics to be computed, the decision criteria to be applied, or the format of the outcome record." Its trust roots are git commit hashes and SHA-256 only.

The manuscript (`papers/AEPF/AEPF.tex`) defines AEPF as the **Avenridge Evaluation and Publication Framework** — a much broader operationalized methodology that *does* include cross-model review, the materialization manifest, calibration-as-a-standing-requirement, null-result publication parity, constrained-interpretation reporting, and the viability gate. The same acronym names a narrow preservation format in one place and a broad evaluation framework in the other. The rich machinery we actually practice lives in the paper and the case-study files, **not in the committed spec.** A third party who reads only the committed spec receives something far smaller than what the paper claims.

**(b) The manuscript existed only in volatile scratch.** Until today, `papers/AEPF/AEPF.tex` in the repo was a 0-byte stub; the real 66 KB draft lived in the Cowork session scratch directory, which is cleared between sessions. It has now been copied into the repo and needs to be committed. Tasks #107/#108 ("upload to arXiv," "submit to Royal Society Open Science") referenced a paper that, in the durable repo, did not exist.

---

## 2. The outcome ledger (what the hammer has actually produced)

| Study | Type | Outcome | Verdict in the doc's own terms |
|---|---|---|---|
| GW_v1 (SpinPhase blind) | Novel-hypothesis test | **NULL** | GW150914 ranked 52/100; "the hypothesis registered for v1 is falsified" |
| GW_QUIETWELL_v1 | Novel-hypothesis test | **NULL** | Ranked 50/100; "falsified"; doc notes "five-of-five falsifying outcomes" |
| ERSAF (cosmology) | Novel-hypothesis test | **NULL** | "ERSAF VERDICT: NULL"; only 1 of 4 diagnostics fired |
| Dynametrix-HRRR | Viability gate | **GATED OUT** | r = 0.984; DO_NOT_PROCEED; archived considered-but-deferred |
| CT-v1 novelty | Diagnostic | **INERT** | Mechanical PROCEED, but novelty term contributes ≈ 0 in-data |
| RC_v1 (this study) | Novel-hypothesis test | **NULL** | proportion 0.0067 vs k = 0.20; F-saturated, high framing robustness |
| DistilBERT SST-2 | Calibration audit | (measurement) | "Not calibrated" |
| Toxic-BERT | Calibration audit | (measurement) | "Calibration drift detected" |
| ChatGPT-detector RoBERTa | Calibration audit | (measurement) | "NOT CALIBRATED"; BSS = −0.16 |

**The tally that matters:** across every *novel-hypothesis* test ever run under this discipline — SpinPhase phase-coherence in gravitational waves, the coherence-tension idea in weather, residual structure in cosmology, the CT-v1 phase-novelty term, the RC_v1 topology claim — the count of positive confirmatory findings is **zero.** The only non-null deliverables are the three calibration audits, which by design *measure a third-party model's calibration* rather than test an original hypothesis — and all three found the audited model poorly calibrated.

So the "fixed NULL cube" intuition is empirically well-founded. It is not pessimism; it is the data.

---

## 3. What the hammer demonstrably does (its real strengths)

The instrument is good — genuinely good — at one thing, and it is the hardest thing in empirical work: **it has reliably prevented the operator from fooling himself.** This is not abstract. The record contains specific, documented catches:

- A fabricated citation (the "ParaConsist" reference) was caught during cross-model review before it reached a locked document.
- Post-hoc tuning was structurally prevented by single-execution discipline across every study.
- A self-contradiction in RC_v1 — the §10 lock summary disagreeing with the body after a template count changed — was missed by two warm reviewers and caught by a *cold* reviewer with no stake in the design conversation. That worked example is why the cold-reader role is load-bearing.
- The viability gate retired Dynametrix-HRRR (r = 0.984) *before* a confirmatory run could be wasted on a structurally over-determined comparison.
- CT-v1's novelty mechanism was shown to be inert in the available data by the diagnostic's own characterization layer, preventing a misleading "PROCEED."
- Operational failures discovered after lock (a PELT `AttributeError` on real ERSAF data; a Windows torch-DLL delay; the WSL/vLLM integration friction in RC_v1) were disclosed as deviations rather than quietly fixed.

And null-parity is **practiced, not merely preached**: every one of those nulls was written up to the same standard a positive would have received, including the operator's own cherished hypotheses. That discipline is rare. Most researchers' drawers are full of exactly these outcomes, unexamined. This framework treats them as first-class. The hammer rings true.

Secondary strengths: it is git- and hash-rooted (tamper-evident and third-party reproducible in principle); it has been exercised across four substantively different domains (atmospheric, gravitational-wave, language-model, cosmological), which is real evidence of generality; and RC_v1 just demonstrated the entire pipeline end-to-end on real hardware (lock → calibrate → result, three signed-tag stages).

---

## 4. Thin spots (the honest limits)

**1. It has never certified a positive, and it has never been validated against a positive control.** This is the single most important gap. A methodology that returns null every time is, from the outside, indistinguishable from a detector that is broken and always reads zero. The framework has never demonstrated the property "given a real effect and a working detector, AEPF yields POSITIVE under the same discipline." The closest thing on record is sharply ironic: in GW_v1 the on-source segment was a *known real gravitational wave*, and the operator's SpinPhase statistic failed to rank it — which the framework correctly reported. That tells us the hammer faithfully reports when the operator's *method* doesn't work; it does not tell us the hammer *can* ring positive. Until a positive-control study exists, "rigorous" and "so heavy nothing survives" cannot be told apart by an outside reader.

**2. Spec/practice divergence and acronym collision (§1a).** The committed spec is narrow; the practiced framework is broad; they share a name. This is a real liability for a paper that asks reviewers to take the framework seriously.

**3. Independence is partial.** The operator is solo. "Cross-model review" is, in practice, one model family reviewing itself across instances; the cold-reader variant mitigates saturation but is not external independence. The spec itself concedes that solo-evaluator integrity "rests on evaluator discipline."

**4. Breadth over depth.** Many domains, small n within each, no deep within-domain replication. Generality is shown; reliability-by-repetition is not.

**5. The manuscript, by construction, shows no positive finding.** Its three case studies are a null (ERSAF), calibration audits, and a gate-out (HRRR). This is on-message — the framework's value is in what it refuses to pass — but a reviewer may reasonably ask whether a methodology is *validated* by examples in which it only ever says "no."

**6. Limits the spec already admits:** AEPF does not prevent parameter choices informed by prior exploration of unbound data, does not solve the file-drawer/selective-publication problem, and does not by itself verify held-out status.

---

## 5. What it can and cannot claim

**Can legitimately claim:** a working, cryptographically anchored, single-execution, tamper-evident evaluation protocol that demonstrably prevents specific, named self-deception failure modes; honest null-result parity in practice; cross-domain applicability; and full end-to-end reproducibility on commodity hardware. As a *process and discipline* contribution, this is real and defensible.

**Cannot (yet) claim:** that it produces or certifies positive findings (it never has); that it has been validated against a positive control (it has not); that its independence and third-party-verification properties are realized rather than aspirational (solo operator, same-model review); that its committed specification matches its practiced scope (it does not); or that any of the operator's original hypotheses have empirical support (none do, so far).

---

## 6. The synthesis, stated plainly

The hammer is sound. What it keeps revealing is not that the universe is empty but that **the operator's novel detection methods do not detect** — and it makes that fact legible and honest instead of letting it curdle into a false positive. That is the framework working exactly as designed. It is also, for the person swinging it, the harder of the two possible findings to sit with: the discipline is the success, and the discoveries are the casualties.

Which means the value already created is mostly a *methodological* one, and it is largely realized the moment the framework is communicated — i.e., in the paper — not in any further hypothesis test.

---

## 7. Concrete moves (operator's call)

1. **Commit the preserved manuscript.** `papers/AEPF/AEPF.tex` and `references.bib` are now in the repo; stage and commit them so the paper stops living only in volatile scratch. (Highest urgency; near-zero effort.)
2. **Resolve the two-AEPF collision.** Decide whether "AEPF" is the narrow Evidence Preservation Format (then the broad methodology in the paper needs its own name) or the broad framework (then the committed spec must grow to match the paper). Shipping with the collision unresolved invites reviewer confusion.
3. **Run a positive-control validation.** The most valuable experiment the framework has never done: take a *known-true* effect with a *known-working* detector — a synthetic injected signal a standard pipeline recovers, or simply a model known to be well-calibrated — and show AEPF yields POSITIVE under identical discipline. This directly answers the "is the hammer just too heavy?" question and would materially strengthen the paper. It is also the scientifically correct response to a string of nulls: validate the instrument on a positive control before concluding the world is null.
4. **Decide the paper's fate:** ship as an honest methodology contribution now, or hold for the positive-control study (3) and ship a stronger version.

*End of stocktaking. This document is an assessment, not a locked result; it can be revised as the record changes.*
