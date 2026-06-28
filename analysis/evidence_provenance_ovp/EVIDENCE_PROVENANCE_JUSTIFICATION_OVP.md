# Evidence Provenance — Candidate Justification (DRAFT v0, for warm review)

**The first OVP candidate drawn from an information source exogenous to the model: the structure of the retrieval pipeline.**

> Status: DRAFT. Nothing here is locked, no pipeline is built. This is the one page that decides whether the candidate earns a locked OVP run. Discretionary choices are flagged **[DECISION]**. Naming: this concept is **Evidence Provenance** — distinct from "Candidate Provenance," the OVP v0.2 candidate-justification section. Don't let the names collide.

---

## 0. What this is, and why it's different from #1–#5

OVP #1–#5 tested **endogenous** descriptors — quantities computed from the model's own forward pass over a single example. Every one was Not-Validated/Inconclusive, and we converged on a structural reason: anything the model computes from its own machinery is suspect of being **pre-absorbed into the weights during training**, so it's redundant with confidence by construction. The program's open question became: *can a descriptor drawn from information the model never had add gain beyond confidence?*

This candidate is the first deliberate attempt. The information source is the **retrieval pipeline's structure** in a retrieval-grounded QA system — a layer that exists *outside* the model's forward pass and (for the right observables) outside its training distribution.

## 1. The candidate (one sentence)

On a retrieval-augmented QA system, an **Evidence Provenance** observable — computed from retrieval-pipeline metadata, before the answer is judged — adds Held-out Discriminative Gain beyond the model's answer confidence (and beyond a trivial retrieval-score baseline) in predicting answer correctness.

**Scoped pilot candidate (warm-passed):** *Does **retrieval-score entropy** — the Shannon entropy of the top-k **sum-normalized** retrieval scores (each score ÷ the top-k sum → distribution → entropy; sum-normalization pinned over softmax-with-temperature, which would smuggle in a temperature parameter) — add held-out correctness gain beyond **model confidence + max retrieval score** in a single pinned RAG QA system?* One dataset, one retriever, one generator, one metadata-only scalar, one correctness rule. No vector, no content-contradiction signal, no source reputation. Retrieval-score entropy is chosen as the lead observable because it is **always available from any retriever** (independent of URL/domain metadata, which QA benchmarks often distort), **metadata-only**, **pre-answer**, **non-circular**, and **plausibly invisible to the generator** — while directly encoding whether the retriever found one clear support passage or a flat, ambiguous evidence set.

## 2. Mechanism (what process generates it; what it measures)

A RAG answer is conditioned on a retrieved evidence set. When that set is **evidentially weak** — sources disagree, the retrieval is thin or flat (no passage strongly matches), or the apparent "many sources" are near-duplicates of one origin — the answer rests on poor ground and is more likely wrong. Crucially, the *generation step may not register this*, because it conditions on the passages' **content** but not on the pipeline's **structural metadata** (how many distinct sources, how peaked the retrieval scores, how large the candidate pool was). The mechanism: **evidential support structure bounds answer reliability independently of how confident the generation feels.**

## 3. Information source + Atlas entry

Atlas entry: **retrieval-pipeline structure** — `OPEN / exogenous`. Concretely, observables computable from retrieval metadata:

- **retrieval-score geometry:** max / mean / entropy of top-k similarity (a flat distribution = ambiguous retrieval, no clear support);
- **source independence:** count of distinct sources/domains in top-k; near-duplicate rate among passages (five copies of one wire ≠ five confirmations) — computable from URLs/hashes, not content;
- **pool/coverage:** how many candidates exceeded a similarity threshold (thin vs rich evidence);
- **recency:** age spread of sources, where timestamped.

## 4. Orthogonality claim — the make-or-break, in two parts

A descriptor is only worth running if it's plausibly orthogonal to confidence on **both** axes:

- **(a) Not in the context window.** The generation step never sees retrieval scores, the size of the candidate pool, or source-independence computed from URLs/hashes. These are produced by the retriever, not shown to the model. So confidence *cannot* condition on them at inference.
- **(b) Not directly available as retrieval metadata (warm-pass correction — the weaker, defensible claim).** "Not in training" is overreach: a web-trained model has likely learned *textual* proxies for evidential weakness — vague or low-specificity passages, hedging, conflicting snippets, single-source framing, stale facts, SEO-style repetition. So the claim is **not** that the model is blind to evidence weakness. It is that **metadata-only provenance encodes retrieval-*process* structure the generator is never shown** — score entropy, duplicate rate, pool size, distinct-source count — which it cannot read directly even though it may *infer* some evidence weakness from content. The locked test is therefore precise: does the process-structure signal add gain **over and above** whatever content-inferred weakness confidence already captures? That narrower orthogonality claim survives skepticism, and it is the one this candidate stands or falls on.

**Honest gradient.** The observables split by how orthogonal they are. *Metadata-only* signals (score entropy, pool size, distinct-source/near-duplicate count) are strongest on both axes — the model literally cannot read them. *Content-derived* signals (cross-passage contradiction via NLI) are more powerful but **weaker on orthogonality**, because the model *does* read the passages and may already sense contradiction. **Therefore the candidate leads with metadata-only observables**; content-derived ones are secondary and explicitly flagged as lower-orthogonality.

## 5. Non-circularity / independence commitment

The observable is computed from retrieval metadata **before** any correctness judgment and **never** references `y`. This is the OVP no-peeking firewall transplanted: provenance scored on the evidence-as-data, not on whether we ended up agreeing with the answer. (Explicitly *excludes* historical source-reputation scores, which are circular — built from past correctness judgments — and likely partly absorbed by the model anyway.)

## 6. Baselines it must beat

`B` is not just confidence. The candidate must add gain beyond **confidence AND a trivial retrieval-score baseline** (e.g. max top-k similarity). Beating confidence alone is not enough if a one-line retrieval score already captures it. **[DECISION]** the confidence operationalization for a generative answer (sequence log-prob / token-confidence / verbalized confidence / max-softmax of an answer head).

## 7. Surface control / confound

Pre-committed non-gating confound covariates (the OVP length/domain analog): **retrieval count, answer length, query length/difficulty**. If provenance's gain collapses when these are added, it was a proxy for "how much was retrieved," not evidential structure. Plus the permuted-provenance foil (provenance scores shuffled across examples) must land below `τ_lo`.

## 8. Failure prediction (pre-committed readings)

- **Validated** (`D > τ_hi`): pipeline-structural provenance carries correctness information confidence does not — the program's first orthogonal-source positive.
- **Not-Validated** (`D < τ_lo`): confidence already absorbs evidential support — the `perturbation_spread` outcome generalized to the retrieval layer, and itself a sharp result (the model's certainty already prices its evidence).
- **Confound-collapsed:** gain survives `[B]` but dies under `[B, retrieval_count, length]` → a retrieval-volume proxy, caveated.
- **Foil red flag:** `D_foil ≥ τ_lo` → permutation/leakage pathology, interpretive trust suspended.

## 9. Substrate + the methodological-generality test (pre-committed)

This is the **first OVP study on a retrieval-grounded substrate**. OVP's machinery (band calibration, standardized-logistic HDG, permuted foil, no-peeking, single-execution, H1) was built for single-pass classification. So this run is *also* a test of whether that machinery **transfers without modification**:

- transfers cleanly → evidence of methodological generality (a paper result);
- needs adaptation → information about OVP's scope (also a result).

Either outcome is recorded. **[DECISION]** dataset/retriever/model: a QA benchmark with retrievable corpus and gradeable answers — e.g. Natural Questions / TriviaQA / HotpotQA, an open retriever (BM25 or a pinned dense retriever), a pinned generator. The substrate must yield, per example: query, retrieved set + metadata, answer, confidence, and **independently gradeable correctness `y`**.

## 9.5 Sequence: y-free feasibility screen → calibration → locked candidate (warm pass)

A cheap, **outcome-free** feasibility screen precedes the expensive calibration — the FC-03 lesson (characterize substrate viability before validating) — with one firewall that must cut through it:

- **Stage 0 — y-free feasibility screen (cheap; can close the candidate; touches NO `y`).** On a development split, compute only quantities that **do not reference correctness**: entropy's distribution/spread, `corr(entropy, confidence)`, `corr(entropy, max retrieval score)`, and a collinearity check of `C` against `B`. If entropy is (near-)collinear with `B` — e.g. `entropy ≈ f(max retrieval score)`, multiple-`R ≈ 0.98` — its residual independent variance is too small to be worth calibrating (zero gain holds *by construction* only in the exact-collinear limit), and the candidate is **closed before any calibration** on cost-asymmetry grounds, as a clean Atlas annotation. This is legitimate FC-03-style characterization precisely *because it never looks at the outcome.*
- **The firewall (critical).** Quantities that touch `y` — `MI(entropy, correctness)`, entropy-by-correct-vs-incorrect, any look at the `C↔y` relation — are **NOT** feasibility screening. They **are** the sealed OVP measurement, and computing them pre-lock is peeking. They stay behind the no-peeking firewall, visible only in the single locked run. The FC-03 analogy licenses *only* the target-free half; the moment characterization touches the outcome, it has become the experiment.
- **Stage 1 — calibration sub-study** (only if Stage 0 passes): synthetic null + positive-control candidates on this substrate set `[τ_lo, τ_hi]`, mirroring `detector-ovp-calib`. This is the §9 methodological-generality test made concrete — clean port = evidence OVP generalizes; needed adaptation = recorded scope finding.
- **Stage 2 — locked candidate OVP run** against the calibrated band.

We adopt the *practice* of this funnel; we do **not** formalize a new Atlas state machine now — that's apparatus, and it belongs in the consolidation paper as a described pattern (weather / OVP / RTVP as worked examples), not as a framework built ahead of results.

## 10. Target + what a result establishes

Target `y` = per-example answer correctness **[DECISION: exact-match / F1 / judged]**. A **Validated** verdict establishes that pipeline-structural provenance adds correctness information beyond confidence *on this substrate/retriever/generator*, under the pinned estimator and band — **not** that it generalizes across retrievers, that it's practically large, or that the model is "uncalibrated." A **Not-Validated** verdict establishes that, here, the generator's confidence already prices its evidential support.

## 11. Discretionary decisions for sign-off

(a) dataset — **leaning NQ-open** (clean single-canonical-answer ground truth, ~3K, fewer moving parts than TriviaQA); (b) retriever — **leaning pyserini BM25** with `k1`/`b`/tokenization pinned verbatim (so entropy reproduces bit-stably) over its Wikipedia corpus; (b′) score→distribution normalization — **sum-normalization, pinned** (not softmax-with-temperature); (c) generator model + revision (pinned open instruct 7–8B with accessible token log-probs) — and **compute budget confirmed** (≈3K NQ-open × generator + calibration reps ≈ a day or two on the RTX 5080; size the substrate before locking); (d) confidence operationalization (length-normalized answer sequence log-prob recommended); (e) the exact provenance observable — **settled at warm pass: top-k retrieval-score entropy**, one scalar, no vector. (Distinct-source count was the first instinct but rejected for the pilot: many QA benchmarks don't preserve real-world source diversity, so domain/URL metadata is noisy or meaningless — entropy needs no such metadata.) (f) correctness grader; (g) the inherited-vs-fresh band (OVP needs a `[τ_lo, τ_hi]` — does it come from a calibration on this substrate, mirroring the detector arc?).

## 12. Honest limits / where it most likely nulls

- **Most likely null mode:** the generator's confidence already reflects evidential weakness (it reads contradictory passages and hedges). The metadata-only lead is the hedge against this, but it can still null — and that null is informative.
- **Transfer risk:** OVP may not port cleanly; if the band/foil/estimator need rework, that's a finding, not a failure, but it complicates a clean verdict.
- **Single observable first.** No `(C, E, P, R)` vector until one metadata-only provenance scalar survives — whether the four are separable sources or reaggregations of the same retrieval variables is a downstream question.
- **Substrate-scoped.** A verdict binds to this retriever/generator/corpus; it is not a claim about RAG in general.
- This page is the gate. If the orthogonality argument in §4 doesn't survive warm review — specifically (b), not-in-training — the candidate does **not** earn a run, and that judgment is itself a useful Atlas annotation.
