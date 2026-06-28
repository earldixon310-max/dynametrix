# Pre-Registration — EVIDENCE_PROVENANCE Stage 0 (y-free feasibility screen)

**Can retrieval-score entropy possibly add held-out gain beyond the baseline — decided WITHOUT ever looking at correctness.**

> Status: DRAFT for warm + cold review, then lock. This is **Stage 0** of the three-leg arc (y-free screen → calibration → locked candidate; justification doc §9.5). It is **exploratory, not a verdict** — it can only *close* the candidate or *pass it through* to calibration. Discretionary pins flagged **[DECISION]**.

---

## 0. Role, and why this is not peeking

The locked OVP question — does entropy add HDG for correctness `y` beyond `B` — is sealed to a later stage. Stage 0 answers a strictly weaker, **outcome-free** question: is entropy even linearly independent enough of `B = {confidence, max retrieval score}` to *possibly* add gain, and does it have any spread at all? If entropy is (near-)collinear with `B`, its independent variance is too small to be worth calibrating — in the exact-collinear limit a logistic on `[B, entropy]` gains nothing by construction, and at the pinned near-collinear threshold the residual is too small to justify the compute — so we close the candidate then.

This is the FC-03 move (characterize substrate viability before validating) — legitimate **only because it never references `y`.** The firewall below makes that structural, not a promise.

## 1. The screen's question (y-free)

On a development run of the pinned RAG-QA pipeline, computing only quantities that **do not reference correctness**: does `retrieval_score_entropy` carry independent, non-degenerate variance relative to `B = {confidence, max_retrieval_score}`?

## 2. Substrate + the structural y-firewall

The pipeline (pins in §7): **NQ-open** queries → **pyserini / Anserini BM25** (`k1 = 0.9`, `b = 0.4`, index `wikipedia-dpr-100w`) over Wikipedia → **`Qwen/Qwen2.5-7B-Instruct`** @ pinned HF revision, 4-bit bitsandbytes, greedy → answer + token log-probs. Per query it emits:

- `entropy` = Shannon entropy of the **top-k sum-normalized** BM25 scores (each score ÷ top-k sum → distribution → entropy);
- `confidence` = length-normalized answer sequence log-probability;
- `max_retrieval_score` = max top-k BM25 score.

**Structural firewall (the load-bearing guarantee).** Stage 0 reads a derived file `stage0_screen_input.csv` containing **only** `(qid, entropy, confidence, max_retrieval_score)`. **Correctness is neither computed nor attached at Stage 0** — the answers are generated but **not graded against gold**; the grading function and gold answers are **not accessed** in this stage. As in the detector arc's derived-input firewall, the screen *literally cannot see `y`* because the file it reads does not contain it, and the grading step is deferred to the sealed candidate run. A source-level check covers **both sides** of the file: (i) the Stage 0 reading code never imports the grader or reads a gold/correctness column; **and (ii) the module that constructs `stage0_screen_input.csv` likewise never imports the grader or accesses gold/correctness, and emits — asserting at write time — exactly the four columns `(qid, entropy, confidence, max_retrieval_score)`.** The four-column guarantee is thus enforced at the point of construction, not merely asserted downstream: a stray outcome column cannot be written in the first place, let alone read.

## 3. Pre-committed y-free statistics (exact; no others computed)

1. **Spread of `entropy`:** mean, sd, min/max, and the fraction of mass in the single most-occupied decile bin. (Confirms entropy is not degenerate/constant.)
2. **`corr(entropy, confidence)`** — Pearson and Spearman.
3. **`corr(entropy, max_retrieval_score)`** — Pearson and Spearman.
4. **Joint collinearity — multiple `R`:** least-squares fit of `entropy ~ confidence + max_retrieval_score`; report the **multiple correlation `R`** (joint, *not* max pairwise — a pairwise Pearson against one feature would miss entropy being a linear combination of *both*). The regression is fit on the **same data the decision is read from** — no held-out split, because the question is the candidate's *structural* redundancy, not its predictive performance. (Residual independent variance is the only thing that could add gain **under the pinned linear estimator** — §8 scopes the "only" to linearity.)

No statistic touching `y` appears here, by §2.

## 4. Pre-committed decision rule (CLOSE vs PROCEED) — thresholds pinned BEFORE running

**Pinned decision rule (deterministic from the data; no operator discretion at decision time):**

> **CLOSE** if `multiple-R(entropy ~ confidence + max_retrieval_score) ≥ 0.98` (equivalently `R² ≥ 0.9604`) **OR** `sd(entropy) < 0.10 nats`. **PROCEED** to Stage 1 otherwise.

Two named failure modes, both deterministic, pinned with intent:

- *near-collinear (`R ≥ 0.98`):* entropy carries at most ~4% independent variance beyond `{confidence, max_retrieval_score}` — effectively redundant, and **not expected to add linear gain under the pinned estimator**. ("Cannot" would overstate: at `R ≥ 0.98` the residual variance is real but too small to be worth calibration compute; only the *exact*-collinear limit gives zero gain by construction.) **ρ = 0.98** is conservative by the cost asymmetry: a false CLOSE kills a possibly-real candidate with no further test, whereas a false PROCEED costs only the calibration sub-study (a day or two on the 5080). Compute is the cheaper error to absorb, so the screen spends it to protect against premature closure. (ρ = 0.95 would start to bite borderline candidates carrying small-but-real residual signal.)
- *degenerate (`sd < 0.10 nats`) — a CLOSE arm, but a distinct one:* this closes **not because entropy is redundant** but because it has **no variance to screen from** — the signature of a broken/mis-configured retriever returning identical top-k structure for every query. It is a **pipeline-health abort**, not a candidate-viability judgment, and it earns a different Atlas annotation than the redundancy close (§5, §8). For top-k = 10 with sum-normalization, entropy ∈ [0, ln 10 ≈ 2.303 nats]; `sd < 0.10` (~4% of the maximum) means entropy is functionally constant across the dataset. High enough to fire only on "no variation to predict from," low enough not to close a legitimately concentrated distribution (e.g. one sitting tightly around 0.5–1.0 nats).

## 5. What PROCEED does and does not establish

**PROCEED** means **only** that entropy is not trivially redundant with `B` and is not degenerate — **necessary, not sufficient**; it says nothing about whether entropy adds gain *for `y`*, the sealed Stage 2 measurement (necessary-condition-vs-descriptor). **CLOSE has two distinct arms, neither of which forecasts the Stage 2 verdict:**

- **CLOSE-redundant** (`R ≥ 0.98`): *not* a forecast that y-gain is zero, but a **cost-asymmetry resource decision** — entropy is redundant enough with `B` that it isn't worth spending calibration compute to find out, given a false CLOSE is the cheaper error than a false PROCEED (§4). (Zero y-gain holds *by construction* only in the exact-collinear limit, not at `R ≥ 0.98` — hence "declines to pay," not "predicts no gain.")
- **CLOSE-degenerate** (`sd < 0.10`): not a statement about the candidate at all, but a **pipeline-health abort** — entropy has no variance to screen from, signalling a broken/mis-configured retriever. The screen cannot run meaningfully, so the candidate is *not adjudicated*; the pipeline is fixed before anything proceeds.

So: **PROCEED defers the verdict, CLOSE-redundant declines to pay for it, CLOSE-degenerate aborts because the instrument isn't working.** The two CLOSE arms warrant different Atlas annotations (§8).

## 6. Single-execution + persistence

Run **once** on the pinned dev run; no parameter sweep, no recomputation to a new threshold. **Single-execution extends to the pipeline:** the study installs **one** pyserini version and uses **one** Qwen revision, both recorded *before* the run; re-running the screen under a different pyserini version or model revision to obtain a different verdict is the pipeline-level form of fishing and is disallowed. The exact version/revision actually used are written into the result JSON and the build manifest. Persist `stage0_feasibility_result.json`: the four §3 statistics, the two thresholds, the **three-way verdict as a categorical string** — `PROCEED` / `CLOSE-redundant` / `CLOSE-degenerate` (not a boolean; the two CLOSE arms are different findings per §5/§8, and a downstream reader must not be able to conflate them), and the pipeline pins + input hash. A re-run under different thresholds would be fishing and is disallowed; thresholds are part of the locked bytes.

## 7. Discretionary pins for sign-off

**Pinned (decision-rule):** `ρ = 0.98` (multiple-R) and `ε_sd = 0.10 nats` (§4); `k = 10` for top-k; entropy over the **sum-normalized** top-k scores; full NQ-open dev split (~3K, representative).

**Pinned (mechanical — exact version/hash strings captured at lock from the operator's environment, since they fix the inputs, not the rule):**

- *Retriever:* **pyserini / Anserini BM25**, `k1 = 0.9`, `b = 0.4` (Anserini defaults — any other value is an unjustified tuning DOF); prebuilt index **`wikipedia-dpr-100w`** (Dec-2018 Wikipedia dump, the NQ-open convention — the index identity determines what is retrievable and hence the entropy distribution, so it is part of the pin). pyserini **version recorded at build** (not yet installed) via `pip show pyserini`, before the single run — single install, no version-shopping (§6).
- *Generator:* **`Qwen/Qwen2.5-7B-Instruct`** at a **fixed HF revision recorded at build, before the run** (intended pin: the detector arc's verified revision `a09a35458c702b33eeacc393d103063234e8bc28`; single revision, no shopping — §6), **4-bit bitsandbytes** quantization (the verified RTX 5080 path from the detector arc), **greedy decoding**. Confidence `B`-term = length-normalized answer sequence log-probability.

The pin is the **exact revision/version string, not the bare name** — same discipline as the detector arc, where a name alone admitted multiple materializations.

## 8. Honest limits

- Stage 0 is a **linear** redundancy screen. Entropy could be non-linearly related to `B` and still pass — that's acceptable, because the locked estimator is also linear (`[B, C]` logistic), so linear independence is the relevant notion. A candidate that passes Stage 0 can still null at Stage 2.
- A high `R²` close is a heuristic, not a proof of zero gain; the conservative `ρ` guards against false closure at the cost of occasionally calibrating a candidate that later nulls.
- Stage 0 binds to this pipeline; it is not a statement about retrieval entropy in general.
- If Stage 0 closes the candidate, the meaning depends on the arm: **CLOSE-redundant** is a clean Atlas annotation ("retrieval-score entropy: redundant with confidence + max-score on NQ-open/BM25; closed at feasibility") and a worked example for the consolidation paper — not a failure. **CLOSE-degenerate** is *not* a candidate annotation at all — it records a pipeline fault to fix, after which the screen reruns; the candidate stays un-adjudicated.
