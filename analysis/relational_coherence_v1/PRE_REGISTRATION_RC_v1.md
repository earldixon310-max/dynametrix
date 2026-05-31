# PRE_REGISTRATION_RC_v1

**Behavioral-Equivalence Graph Topology Under Framing Variation: A Pre-Registered Test of Whether Graph Structure Reveals Consistency Information That Aggregate Rates Conceal, in an Open-Weight Instruction-Tuned LLM**

---

**Status:** PRE-LOCK DRAFT (review pending; lock-commit and tag `rc-v1-lock` to be applied after final user acceptance)

**Framework:** AEPF (Avenridge Evaluation and Publication Framework), v1.1 Conditional Diagnostic Layer

**Author:** Earl Dixon

**Pre-registration date:** 2026-05-30

**Lock-commit SHA:** TBD (populated at git tag time)

**Tag:** `rc-v1-lock`

---

## 0. Reading guide

This document specifies a single executable experiment. Every non-trivial choice is named here and justified by a numbered section. Post-lock, the analysis script runs exactly once against the materialized substrate; any deviation invalidates the lock and requires a documented amendment under a new tag. The one calibration value that depends on a held-out slice (the edge threshold τ) is computed from a pre-committed slice (§7) before main analysis and then frozen.

The five-line core lock is in §10. Everything else either supports those five lines or names a pre-committed limitation.

**Scope note (v1 single-bin design).** This is a deliberately narrow v1. It tests one perturbation family — *framing and layout variation* of multiple-choice prompts (semantically equivalent reformulations that keep the question and option text verbatim) — against one model on one task family. A prior multi-bin design (character / word / sentence / semantic severity bins) was considered and rejected during pre-lock review: a numbers-reconciliation sweep showed the PromptBench substrate could not supply enough distinct, meaning-preserving variants in the non-framing bins to populate evaluable cells, so the multi-bin severity ladder reduced in practice to the framing bin alone. Rather than lock a four-bin document that self-prunes to one bin at runtime, v1 locks the single bin the substrate actually supports. The severity-ladder generalization is a v2 target contingent on generators that can supply the other bins.

---

## 1. Scope and claim structure

### 1.1 Primary (gated) claim — "the simple claim"

**The behavioral-equivalence graph constructed from a model's outputs under semantically-equivalent framing variation of a prompt exhibits global topological structure that distinguishes queries which an aggregate pairwise consistency rate rates as equivalent.**

Operationalization. For each query q in the main eval set, generate N_var = 50 framing variants (§3), run the model on each (§2.2), and construct the behavioral-equivalence graph on the 50 output texts (§4). On that graph define two scalars:

- **Aggregate pairwise consistency rate** (pairwise/local):

  C(q) = 2 · |E(q)| / [N(N − 1)]

  where |E(q)| is the number of edges and N = 50. C is the fraction of variant-output pairs that meet the equivalence threshold τ — the natural single-scalar pairwise-agreement measure given the edge predicate (§4), and the discrete analog of the pairwise-consistency metrics reported in prior paraphrase-consistency work (Elazar et al. 2021 and follow-ons). C is what the simple claim says aggregate consistency conceals.

- **Pair-fraction-in-same-component** (global/topological):

  F(q) = Σᵢ nᵢ(nᵢ − 1) / [N(N − 1)]

  where {nᵢ} are connected-component sizes (full definition in §5.1). F is the probability that two randomly chosen variant outputs are in the same behavioral component — what the simple claim says topology reveals.

C and F are not algebraically reducible to one another. Consider two graphs on N nodes with the *same* edge density C ≈ 0.5 but different connectivity. Graph A is a disjoint union of two complete cliques of size N/2: every within-clique pair is an edge and no cross-clique pair is, giving C = 2·(N/2)(N/2−1)/[N(N−1)] ≈ 0.5; the same partition gives F ≈ 0.5 (a disjoint union of equal complete components has C = F). Graph B is a single *connected but non-complete* component at the same edge density ≈ 0.5 — for example a connected graph in which only about half the pairs are edges but every node is reachable from every other — giving C ≈ 0.5 and F = 1 (all nodes share one component). Same C, different F (0.5 vs 1.0): the C-equal-F-different cell exists by construction, which is what the simple claim depends on.

The gated test: for the set of comparable query-pairs {(q₁, q₂) : |C(q₁) − C(q₂)| ≤ Δ_c}, the proportion satisfying |F(q₁) − F(q₂)| ≥ δ_p is at least k.

Pre-committed thresholds:

- Δ_c = 0.05 (aggregate consistency rates within 5 percentage points)
- δ_p = 0.10 (pair-fraction difference of 10 percentage points)
- k = 0.20 (at least 20% of comparable query-pairs show topological separation)

These thresholds may prove conservative or aggressive; they are pinned regardless. A negative result (proportion < k) is a clean null and is published with the same rigor as a positive one.

### 1.2 Secondary (exploratory, ungated) observation

Reported as characterization, not gating publication: the joint distribution of (accuracy_lenient(q), F(q)) across queries, with particular attention to the **high-accuracy + low-F cell**, operationalized as accuracy_lenient(q) ≥ 0.9 and F(q) ≤ 0.5 — queries the model answers correctly across framings (high lenient accuracy) but whose framing-response graph is fragmented (low F). These two thresholds (0.9, 0.5) define the count reported in §9; they are descriptive cut-points for an ungated, exploratory cell and do not enter the §1.1 gated test. This is the predicted signature of the mode-collapse phenomenon (the model recovers the correct label under each framing but its behavioral organization across framings is not coherent), documented in prior paraphrase-consistency literature. Its presence or absence is reported but does not gate the §1.1 claim.

### 1.3 What is *not* claimed in v1

- Universality across model families. v1 tests one open-weight model. Generalization requires re-running.
- Universality across task families. v1 tests one task family (MMLU multi-choice). Multi-task generalization is a v2 target.
- A severity ordering of perturbation types. v1 tests a single perturbation family (framing/layout variation). The character/word/sentence severity ladder is a v2 target contingent on adequate generators (see §0 scope note).
- Adversarial worst-case behavior. v1 uses model-agnostic, meaning-preserving framing variation, not model-optimized perturbation. Transferred-attack behavior is a v2 secondary analysis.
- A dynamical-systems mechanism. The Kuramoto / synchronization framing motivates the design (§12) but is not under test; the load-bearing claim is §1.1.

**Explicit acknowledgment of dropped iterations.** Prior design iterations of this study included three secondary claims that are deliberately *not* tested in v1 and are not smuggled back in through implication anywhere in this document: (a) severity-precedence — that fragmentation onset precedes accuracy onset along a multi-bin perturbation-severity axis; (b) a critical-transition signature — that cross-query variance of pair-fraction amplifies near a threshold severity, as a static analog of dynamical critical slowing down; (c) cross-bin comparison — that pair-fraction differences across distinct perturbation families reveal differential representational coherence. Each of these requires a multi-bin substrate the v1 generator does not support; each was dropped during the substrate-honest collapse documented in §16 provenance. They remain candidate hypotheses for v2 against a substrate engineered to support them.

---

## 2. Substrate identity

### 2.1 Dataset

- **Repository:** Hugging Face Hub dataset `cais/mmlu` (the canonical MMLU release; this is the same upstream data PromptBench wraps, loaded directly so that each item exposes its raw question, four separate option strings, and integer gold index — the structure the §3 generator requires. PromptBench was the substrate of record in earlier multi-bin drafts for its perturbation/attack module; the single-bin framing collapse (§0, §16) removed that role, leaving only the MMLU-loader function, which `cais/mmlu` serves directly and with a cleaner item structure.)
- **Pinned dataset revision:** `c30699e8356da336a370243923dbaf21066bb9fe` (filled at lock-commit; the `cais/mmlu` dataset revision hash recorded via the `datasets` library at time of lock)
- **Split:** `test` (per-subject configuration)
- **Task family:** MMLU multi-choice (discrete A/B/C/D labels enable clean lenient label-recovery; the free-form response format permits the mode-variation the design probes)
- **Item structure (verified against `cais/mmlu`):** each row is `{question: str, choices: list[str] of length 4, answer: int ∈ 0..3, subject: str}`. The gold index maps to the A/B/C/D label by position (0→A, 1→B, 2→C, 3→D).
- **Subjects used in main eval:** pre-committed. v1: a balanced subset of three MMLU subjects ("high_school_mathematics", "professional_law", "miscellaneous"), 100 queries per subject (300 total), deterministic selection by question-ID-sort.
- **Question-ID definition (pinned):** qid = SHA-256 of the UTF-8 concatenation `question + "␟" + "␟".join(choices)`; items within a subject are sorted ascending by qid, then sliced `[offset : offset + n]`. The ordering is fully determined by content and is independent of dataset row order.
- **Calibration slice:** first 50 queries of MMLU "elementary_mathematics" by question-ID-sort, excluded from main eval (disjoint subject). Pre-committed before any τ value is computed.

Note: `cais/mmlu` supplies the MMLU items; the framing variants are generated by this study's own deterministic generator (§3).

### 2.2 Model

- **Identity:** Qwen2.5-7B-Instruct-AWQ (official 4-bit AWQ quantization of Qwen2.5-7B-Instruct)
- **Hugging Face repository:** Qwen/Qwen2.5-7B-Instruct-AWQ
- **Pinned revision SHA:** `b25037543e9394b818fdfca67ab2a00ecc7dd641`
- **Precision:** 4-bit AWQ (chosen over fp16 because fp16 7B weights ≈ 15 GB do not leave usable KV-cache headroom on the 16 GB RTX 5080; AWQ weights ≈ 5 GB leave ≈ 11 GB for batched inference. The study measures the framing robustness of this specific quantized deployment target, which is a legitimate and common production configuration for 7B-class models; the quantization is part of the model-under-test, not an approximation of an fp16 ideal.)
- **Decoding (primary run):** temperature = 0.0, top_p = 1.0, top_k = −1 (vLLM's "disabled" sentinel — consider all tokens; immaterial under temperature = 0 greedy decoding, where the argmax token is selected regardless of top_k), repetition_penalty = 1.0, max_new_tokens = 512 (passed to vLLM's `SamplingParams` as `max_tokens`, the same quantity), seed = 0x1DEA
- **Samples per query per variant (primary):** 1 (deterministic decoding removes stochastic noise from the fragmentation measurement)
- **Stochastic sensitivity panel:** 3 samples at temperature = 0.7, top_p = 0.95, seed = 0x1DEA + sample_index; reported as sensitivity, does not gate the primary claim. Run on a stratified 50-query subset of the main eval (not all 300), since the panel is non-gating and the trimmed volume preserves the sensitivity signal at 1/6 the compute.
- **Stochastic-panel subset (pinned).** The subset is selected pre-execution as the first 16 queries of the `high_school_mathematics` slice + the first 17 of `professional_law` + the first 17 of `miscellaneous` (16 + 17 + 17 = 50), where "first" is by the question-ID-sort order used to select the main eval set (§2.1). The selection rule is deterministic given §2.1's subject and query selection; no separate seed is needed because the ordering is fixed. The subset is therefore fully determined by the main-eval selection already recorded in the materialization manifest (§11): it is the first 16 high_school_mathematics + first 17 professional_law + first 17 miscellaneous qids in qid-sort order, derivable from the manifest's main-eval qid list without a separate field.

### 2.3 Compute profile

- **Hardware:** AMD Ryzen 9 9950X3D, 112 GB DDR5-3600, NVIDIA RTX 5080 (16 GB VRAM)
- **Inference engine:** vLLM (native AWQ support and batched throughput; pinned version `0.22.0`)
- **GPU memory utilization (pinned):** `gpu_memory_utilization = 0.80` passed to vLLM. The 16 GB RTX 5080 is shared with the Windows desktop compositor (~1.3 GB resident under WSL2), and vLLM's 0.92 default reserves more than the free remainder; 0.80 leaves headroom while still giving the AWQ model (~5.5 GB weights) ample KV-cache space for this small batched workload. This parameter governs only KV-cache reservation and does not change generated tokens under greedy decoding (§2.2) — it is a deployment resource setting, not an analysis parameter, and is excluded from the §10 result-determining fingerprint for that reason.
- **Sampler backend (pinned):** the script sets `VLLM_USE_FLASHINFER_SAMPLER=0` before importing vLLM, forcing vLLM's native PyTorch sampler rather than the FlashInfer sampler. FlashInfer JIT-compiles a CUDA kernel that requires a full CUDA toolkit (nvcc); the WSL2 deployment has the GPU driver but not the toolkit. Under the primary run's greedy decoding (T = 0, §2.2) token selection is argmax and identical across sampler backends, so this is a deployment setting with no effect on result-determining outputs and is likewise excluded from the §10 fingerprint.
- **Inference volume:** main run = 300 queries × 50 variants × 1 sample = 15,000 generations; calibration = 50 queries × 50 variants = 2,500; stochastic sensitivity panel = 50 queries (pinned subset, §2.2) × 50 variants × 3 samples = 7,500 (sensitivity only). Total ≈ 25,000 generations.
- **Wall-clock budget:** estimated 3-6 hours for the full pipeline (main + calibration + stochastic panel) at 4-bit AWQ with vLLM batching. Exact figure pinned at lock-commit after a small throughput probe on the chosen Qwen revision.

### 2.4 Embedding model (used in §4 edge predicate)

- **Identity:** sentence-transformers/all-MiniLM-L6-v2
- **Pinned revision SHA:** `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`
- **Embedding precision:** fp32

### 2.5 Base prompt template (pinned)

The framing variants of §3 are constructed from a base assembled prompt. The canonical base template is:

```
Question: {question}
Options:
(A) {option_A}
(B) {option_B}
(C) {option_C}
(D) {option_D}

Answer:
```

(Trailing whitespace after "Answer:" preserved; no format restriction; no "answer with only the letter" instruction; no chain-of-thought elicitation; no system prompt beyond the default model chat-template wrapping.)

Rationale: the template is deliberately open-ended. A stricter template (e.g., "Respond with only the letter A, B, C, or D.") would collapse the response-mode variation the design is built to detect — the predicted high-accuracy-low-F cell requires that the model can produce the correct label in multiple surface forms (`(A)`, `The answer is A.`, `A) is correct because…`). A maximally-elicitive template (e.g., "Think step by step.") would oversaturate the mode-variation channel. The pinned template sits between these.

The `{question}` and `{option_*}` slots are filled from the `cais/mmlu` item structure verbatim (`question` and the four `choices` entries; §2.1), with no normalization beyond whitespace trimming. This template is itself a design choice; v2 sensitivity analyses may include template variations.

---

## 3. Framing-variation generator (pinned)

The single perturbation family in v1 is framing and layout variation: semantically-equivalent reformulations of the base prompt that keep the verbatim `{question}` and option contents and vary only the instructional wrapper and the option layout. The generator is the product of two orthogonal dimensions; the orthogonality guarantees the product yields distinct strings.

**Framing templates (10).** Each places `{question}` and the (schema-formatted) options block `{OPTIONS}`, then an answer cue. None adds a meta-frame ("which is correct?") that could stack awkwardly against negatively-phrased questions; the prior draft's T2 and T9, which carried that interaction, are excluded by design.

1. `Question: {question}\n{OPTIONS}\n\nAnswer:`
2. `Q: {question}\n{OPTIONS}\n\nA:`
3. `Please answer this multiple-choice question.\n{question}\n{OPTIONS}\n\nAnswer:`
4. `Read the question carefully and select the best option.\n{question}\n{OPTIONS}\n\nAnswer:`
5. `Answer the following.\n{question}\n{OPTIONS}\n\nAnswer:`
6. `Multiple choice question:\n{question}\n{OPTIONS}\n\nAnswer:`
7. `{question}\nSelect one:\n{OPTIONS}\n\nAnswer:`
8. `The following is a multiple-choice question.\n{question}\n{OPTIONS}\n\nAnswer:`
9. `Examine the question below and identify the correct choice.\n{question}\n{OPTIONS}\n\nAnswer:`
10. `Here is a question. Choose the correct answer from the options.\n{question}\n{OPTIONS}\n\nAnswer:`

**Option-layout schemas (5).** Each renders the four options as `{OPTIONS}`.

- **S1 (vertical, parenthesized):** `Options:\n(A) {A}\n(B) {B}\n(C) {C}\n(D) {D}`
- **S2 (vertical, no header):** `(A) {A}\n(B) {B}\n(C) {C}\n(D) {D}`
- **S3 (inline):** `(A) {A}  (B) {B}  (C) {C}  (D) {D}`
- **S4 (vertical, blank-line separated):** `Options:\n(A) {A}\n\n(B) {B}\n\n(C) {C}\n\n(D) {D}`
- **S5 (lettered with periods):** `A. {A}\nB. {B}\nC. {C}\nD. {D}`

**Variant set.** 10 × 5 = 50 distinct combinations per query, used in full (N_var = 50 exactly; no selection step and no operator freedom over which combinations enter the cell). Combinations are enumerated by (template_index, schema_index) in lexicographic order; the master seed 0x1DEA is recorded for provenance but the ordering is fully determined by the indices.

**Meaning preservation by construction.** Option *content* and option *order* (the A→B→C→D label-to-content mapping) are never permuted — permuting option content would change the gold label and break meaning preservation. The verbatim `{question}` text is never altered. Only the surrounding framing and the option layout vary. Consequently every variant is semantically equivalent to its source by construction, which is why v1 requires no separate preservation-stratification step (contrast the rejected multi-bin design, which needed one to handle meaning-changing perturbations). A reported sanity check (§3.1) confirms the variants are near-verbatim in embedding space.

Pre-lock generation-capacity check: 10 × 5 = 50 distinct combinations equals N_var = 50 exactly for every query (the generator is query-independent), so the N_var = 50 target is met for all queries by construction with no selection step. The variant set cannot be structurally under-populated in v1's single-bin design.

### 3.1 Meaning-preservation sanity check (reported, not gating)

For each variant v of query q, compute p(v) = cosine(MiniLM(prompt_v), MiniLM(prompt_q_base)), the input similarity of the framed variant to the canonical base prompt. Because the framing variants keep the verbatim question and option text and change only wrapper and layout, the p(v) distribution is expected to be tightly clustered near 1.0 (anticipated ≥ 0.9 for essentially all variants). This is a sanity check that the generator behaves as specified, reported as a distribution; it does not stratify or gate the analysis. If the observed p(v) distribution were unexpectedly low or bimodal, that would indicate a generator defect and is a documented failure condition (§14).

No template adds a meta-frame ("which is correct?", "which option is right?") that could stack against negatively-phrased questions; the prior draft's T2 and T9, which carried that interaction, were dropped at lock time precisely to remove that potential confound. The 10 surviving templates touch only the instructional wrapper and answer cue — never the question's own framing.

---

## 4. Edge predicate (output graph)

### 4.1 Construction

For each query q, the behavioral-equivalence graph has:

- **Nodes:** the N_var = 50 output texts produced by running the model on the 50 framing variants
- **Edges:** pair (i, j) has an edge iff cosine_similarity(MiniLM(output_i), MiniLM(output_j)) ≥ τ
- **Edges are undirected and binary**

### 4.2 Threshold τ calibration

On the calibration slice (§2.1):

1. For each calibration query, generate the 50 framing variants under §3
2. Run the model under §2.2 primary decoding parameters
3. Within each calibration query, compute all pairwise output cosine similarities
4. τ is set to the 5th percentile of these similarities, pooled across all calibration queries (i.e., the threshold at which 95% of within-query variant-output pairs are connected on the calibration slice)
5. τ is frozen before any main-run inference and written to `calibration_constants.json` with a SHA-256 hash

### 4.3 Why outputs, not inputs

The edge predicate is on model *output* texts because the claim concerns the model's behavioral coherence across framing variation: do the outputs form one connected behavioral component or fragment? The input similarity p(v) (§3.1) is measured separately and used only as a sanity check that the inputs are meaning-preserving; it deliberately does not enter the edge predicate.

---

## 5. Graph scalars

### 5.1 Primary scalar

**Pair-fraction-in-same-component:**

F(q) = Σᵢ nᵢ(nᵢ − 1) / [N(N − 1)]

where {nᵢ} are connected-component sizes of the behavioral-equivalence graph on N = 50 output nodes. F = 1 for a single connected component; F → 0 for an atomized graph; F decreases monotonically under each split. Direct interpretation: the probability that two randomly chosen variant outputs are in the same behavioral component. This is the discrete analog of a Kuramoto order parameter (§12).

### 5.2 Contrast scalar

**Aggregate pairwise consistency rate** C(q) = 2|E(q)|/[N(N−1)] (defined in §1.1). This is the quantity the claim contrasts F against; it is the aggregate that the topology is hypothesized to reveal structure beyond.

### 5.3 Sensitivity scalar

**Largest connected component fraction** LCC(q) = max(nᵢ)/N, reported alongside F to flag cases where F and LCC diverge (one dominant component plus scattered isolates vs. two near-equal components).

### 5.4 Deferred

Algebraic connectivity, modularity, persistent-homology features are v2.

---

## 6. Accuracy measure

### 6.1 Lenient label-recovery (primary)

For MMLU multi-choice with gold label ∈ {A, B, C, D}, the extraction rule is:

1. Lowercase and strip the full output text
2. Search in order for the following patterns, returning the first match's letter:
   - `(?:answer|response|choice)[\s:]*(?:is|=|:)?[\s]*[\(\[]?([abcd])[\)\]]?`
   - `[\(\[]([abcd])[\)\]]`
   - `^[\s]*([abcd])[\s.,:;]`
   - the standalone token `\b([abcd])\b` — a lone a/b/c/d delimited by word boundaries, at any position (last resort; the word-boundary anchors prevent matching a letter embedded inside another word)
3. If no match, accuracy_lenient(q, v) = 0
4. Otherwise, accuracy_lenient(q, v) = 1 iff matched letter == gold

Rationale: the high-accuracy + low-F observation (§1.2) requires that the model can produce the correct label in multiple surface forms. Strict-format extraction would collapse that cell by definition.

### 6.2 Strict-format (sensitivity)

The output must begin with `(A)`, `(B)`, `(C)`, or `(D)` (case-insensitive, leading whitespace allowed). Reported in sensitivity panels; not the primary measure.

### 6.3 Aggregate accuracy per query

accuracy_lenient(q) = mean over the 50 variants of accuracy_lenient(q, v).

---

## 7. Calibration procedure

The calibration slice (§2.1) is processed before the main run:

1. Generate the 50 framing variants per calibration query under §3
2. Run model inference under §2.2 primary decoding parameters
3. Compute pairwise output cosines within each calibration query → τ as the 5th percentile across all within-query pair similarities pooled (§4.2)
4. Compute the p(v) sanity-check distribution (§3.1) and confirm it clusters near 1.0; a failure here is a documented generator defect
5. Freeze τ and write to `calibration_constants.json`; the SHA-256 of that file is printed and recorded in the materialization manifest (§11); commit under tag `rc-v1-calibrated`
6. The full pooled within-query output-cosine vector and the full p(v) vector (not only the percentile summaries) are persisted to `calibration_distributions.npz` alongside `calibration_constants.json`, and are reported alongside main results

No τ value is computed against the main eval set. The calibration slice does not enter the main analysis. The calibration step is single-execution under the same discipline as the main run (§14).

---

## 8. Evaluability

Because the framing generator produces all 50 distinct variants for every query by construction (§3), and every variant is meaning-preserving and enters the graph, **every query yields one evaluable cell of exactly N = 50 nodes.** There is no preservation-filtering attrition (contrast the rejected multi-bin design, where attrition could drop cells below a floor) and therefore no inconclusive-cell handling in v1.

N = 50 nodes per query yields 1,225 pairs. The per-query F estimate's 95% confidence interval is computed by bootstrap resampling over the 50 nodes (resample node indices with replacement, recompute F on the induced subgraph; B = 10,000 resamples, seed = 0x1DEA, percentile interval at 2.5/97.5) at analysis time and reported per query (§9); the design expectation is that the per-query CI half-width is below the pinned δ_p = 0.10 detection threshold, but the exact value depends on the realized component structure (a near-complete or near-atomized graph yields a tighter interval than a balanced multi-component one) and is not asserted in advance. The power of the gated test (§1.1) rests on the aggregate over comparable query-pairs across the full eval set, not on any single per-query interval. A query is excluded only if model inference fails technically on one or more of its variants (OOM, generation error); such a query is dropped, the drop is reported, and it does not enter the analysis. The target main-eval set is 300 queries; the analysis is evaluated on the queries that complete inference cleanly.

---

## 9. Pre-committed reporting

All of the following are reported regardless of outcome:

- Calibration constants (τ) and the calibration slice's output-cosine distribution and p(v) distribution
- Per query: C(q), F(q), F(q) 95% bootstrap CI (the per-query diagnostic referenced in §8), LCC(q), accuracy_lenient(q), accuracy_strict(q). The number of variants completing inference is N = 50 for every analyzed query by construction: a query that fails inference on any variant is dropped in full (§8), so surviving queries always have all 50 variants; this is stated in the result run-summary and the identities of dropped queries are listed separately, rather than carried as a constant per-query column.
- Aggregate: mean and distribution of C, F, LCC, accuracy_lenient and accuracy_strict across queries; cross-query variance of F
- Primary positive-result statistic: proportion of comparable query-pairs satisfying |ΔF| ≥ δ_p out of those with |ΔC| ≤ Δ_c
- The (accuracy_lenient, F) joint distribution and the count of queries in the high-accuracy + low-F cell (§1.2; cell defined as accuracy_lenient(q) ≥ 0.9 and F(q) ≤ 0.5)
- Stochastic sensitivity panel (T = 0.7, 3 samples) results
- Strict-format accuracy sensitivity panel results
- Count and identity of any queries dropped for technical inference failure

Null results are published under the same protocol as positive results. Publication is not gated on the sign of the primary statistic.

---

## 10. The five-line lock (core pre-commitment)

For human verification and external audit:

1. **Substrate.** `cais/mmlu` (canonical MMLU) at pinned dataset revision (`c30699e8356da336a370243923dbaf21066bb9fe`), `test` split, MMLU multi-choice subset (subjects: high_school_mathematics, professional_law, miscellaneous; 300 queries, 100 each; selection by qid-sort per §2.1), pinned base prompt template per §2.5, single perturbation family = framing/layout variation via the §3 generator (10 framing templates × 5 layout schemas = 50 distinct meaning-preserving combinations, all 50 used per query with no selection step, enumerated in lexicographic order by (template_index, schema_index)), N_var = 50 per query, master seed 0x1DEA recorded for provenance.
2. **Model.** Qwen2.5-7B-Instruct-AWQ (4-bit AWQ) at HF revision (`b25037543e9394b818fdfca67ab2a00ecc7dd641`), served via vLLM, temperature 0.0, top_p 1.0, top_k −1, max_new_tokens 512, seed 0x1DEA, 1 sample per variant primary.
3. **Edge predicate.** Edge (i, j) iff cosine(MiniLM(output_i), MiniLM(output_j)) ≥ τ, using all-MiniLM-L6-v2 (revision `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`); τ = 5th percentile of pooled within-query output-cosine pairs on the calibration slice; frozen at calibration.
4. **Graph scalars.** C(q) = 2|E(q)|/[N(N−1)] (pairwise edge density, contrast quantity) and F(q) = Σᵢ nᵢ(nᵢ−1)/[N(N−1)] (pair-fraction-in-same-component, primary); LCC(q)/N reported as sensitivity. N = 50; every query is one evaluable cell (no preservation stratification in v1).
5. **Primary positive result.** Among comparable query-pairs {(q₁, q₂) : |C(q₁) − C(q₂)| ≤ Δ_c = 0.05}, at least k = 20% satisfy |F(q₁) − F(q₂)| ≥ δ_p = 0.10. The high-accuracy-low-F observation is reported as secondary characterization but does not gate.

---

## 11. Materialization manifest (sketch)

Produced at lock-commit time. The actual manifest is a JSON file with SHA-256 hashes of:

- `cais/mmlu` dataset at pinned revision (revision hash via the `datasets` library)
- Selected MMLU subjects and query IDs (deterministic qid-sorted list, per §2.1)
- Qwen2.5-7B-Instruct-AWQ at pinned revision (config + weights hash via HF API)
- all-MiniLM-L6-v2 at pinned revision
- Analysis script `rc_v1_analysis.py` at lock-commit SHA
- Seed master = 0x1DEA
- Calibration constants file `calibration_constants.json` and its SHA-256, plus the full-distribution companion `calibration_distributions.npz` (populated after calibration step, before main run)

The manifest is produced by `build_manifest.py` (committed alongside this document), which resolves the HF revisions, computes the content fingerprints and the deterministic qid lists via the analysis script's own `load_mmlu_items`, and — with `--apply` — pins the resolved revisions into this document's §2.x and §10 TBD slots. The manifest is committed alongside this document. Any divergence between materialized substrate and manifest hashes invalidates the run.

---

## 12. Framing constraints (motivation vs. finding)

### 12.1 Kuramoto / synchronization motivation

The design takes intellectual scaffolding from Kuramoto-type synchronization (Strogatz, *Sync*) and temporal-network structure (Holme & Saramäki). The behavioral-equivalence graph is treated as a discrete proxy for an order-parameter-like global property; F is the discrete analog of the Kuramoto order parameter r; fragmentation is the analog of desynchronization.

**This is motivation only.** The claim under test (§1.1) does not require a synchronization mechanism, a phase-transition threshold, or any dynamical-systems analogue to be validated. A coherent finding here neither confirms nor refutes a Kuramoto-style mechanism in LLM representations; it confirms only that graph-topology measurement (F) reveals structure aggregate consistency (C) conceals.

### 12.2 Representational-manifold framing

The "coupling" in this setup is not between independent variant samples but is mediated through the model's internal representation: the 50 framing variants are independent draws conditioned on a fixed model, and their output coherence is a readout of how the model's representation treats semantically-equivalent framings — as one behavioral orbit or as separate orbits. The graph therefore reads as a probe of representational coherence at query-locality under framing variation. This is the honest description of what the experiment measures; the synchronization framing is the conceptual home that motivated the construction.

---

## 13. Pre-committed limitations

1. **Single model, single task family, single perturbation family.** No claim of generalization across models, tasks, or perturbation types. All three are v2 targets.
2. **Framing variation is near-verbatim.** The generator changes only wrapper and layout, keeping question and option text verbatim. It therefore probes framing/format sensitivity specifically, not deeper paraphrastic robustness (which would require question rewording, infeasible at scale without an LLM paraphraser that would introduce a second model into the pipeline). This is a deliberate v1 scope choice; deeper paraphrase is a v2 target.
3. **Embedding model encodes its own notion of equivalence.** The cosine-over-MiniLM edge predicate uses a model trained on a particular corpus and objective; "behavioral equivalence" here is MiniLM-equivalence in output space, not ground truth.
4. **Deterministic decoding removes one variance source.** T = 0 makes output differences fully attributable to input framing. The stochastic sensitivity panel (T = 0.7) partially probes sampling noise.
5. **The simple claim is robust but not unfalsifiable.** A negative result (proportion < k) is a clean null and is published as such. A degenerate outcome in which all queries have F ≈ 1 (the model is perfectly framing-robust) or all have similar C with similar F (no topological variation) would yield a null and is the expected outcome if framing robustness is high.

---

## 14. Single-execution discipline

The analysis script `rc_v1_analysis.py` is drafted, reviewed, and committed at the same tag as this document. Post-lock:

- The main run is single-execution
- No hyperparameter is adjusted, no threshold is re-tuned, no model is swapped after lock
- Technical failure (OOM, crash, dependency mismatch, or a p(v) sanity-check failure indicating a generator defect) is documented; the lock is amended under a new commit explaining the failure mode; rerun is under the new lock
- Repeated runs to "improve" a result invalidate the lock
- The materialization manifest's hashes must match at execution time; mismatch is a documented failure

This discipline is the same one applied to ERSAF, the Dynametrix-HRRR independence diagnostic, and CT-v1.

---

## 15. Acceptance and lock procedure

After user review and acceptance of this document:

1. Pin TBD values (`cais/mmlu` dataset revision, Qwen2.5-7B-Instruct-AWQ revision, MiniLM revision, vLLM version). The MMLU subject selection and per-subject query counts are already pinned in §2.1 and are not subject to change at lock time.
2. Draft and review `rc_v1_analysis.py` to match every commitment in this document; verify code-document consistency via cross-model lens (per AEPF discipline)
3. Compute materialization manifest with all hashes
4. Run the pre-lock integration dry run on the target hardware (Profile B): `python rc_v1_analysis.py --mode smoke --smoke-n 2`. Confirm `cais/mmlu` loads in the expected shape, vLLM accepts the `SamplingParams`, the AWQ model + KV cache fit in 16 GB VRAM, and the embed→graph path runs. This writes no artifacts and does not consume the single-execution budget; a failure here is an integration/setup issue to fix before lock, not a result.
5. Commit document + analysis script + manifest as a single atomic commit
6. Apply git tag `rc-v1-lock` to that commit
7. Run calibration step on calibration slice; freeze τ; commit `calibration_constants.json` and `calibration_distributions.npz` under tag `rc-v1-calibrated`
8. Run main analysis once
9. Write `RESULT_RC_v1.md` reporting against §9; tag `rc-v1-result`
10. Publish under the same null-result-parity discipline as positive-result publication

---

## 16. Provenance

This document is the product of an extended cross-model design pass: substrate verification of PARAREL (rejected for cloze/masked-LM modality mismatch) and PromptBench (adopted as the MMLU source in the multi-bin drafts for its perturbation/attack module, then — once the single-bin framing collapse removed any use of that module — replaced by direct loading of the canonical `cais/mmlu` test split, which exposes the raw question / four options / gold index the §3 generator requires without PromptBench's pre-assembled item shape; this is the same upstream MMLU data accessed directly, recorded here as a named-substrate change ratified by the operator at lock time); the lenient-label-recovery accuracy explicitization; the Option-B semantic-bin p* calibration (subsequently rendered unnecessary by the single-bin simplification); the numbers-reconciliation sweep that exposed the N_var/cell-size contradiction and, on a second pass, the sentence-bin variant-capacity shortfall that showed the multi-bin severity ladder reducing to a single bin; and the resulting decision to collapse the design to the single framing-variation bin the substrate actually supports. The full intellectual provenance is recorded in the project transcript at the lock-commit timestamp.

---

*End of pre-registration draft. Lock-commit pending user acceptance.*
