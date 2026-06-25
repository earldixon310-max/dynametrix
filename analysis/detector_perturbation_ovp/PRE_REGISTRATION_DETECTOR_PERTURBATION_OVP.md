# Pre-Registration — DETECTOR_PERTURBATION_OVP (candidate study; OVP real candidate #5)

**Study type:** OVP **real candidate** study — judges whether the candidate observable **`perturbation_spread`** (the spread of the detector's `predicted_prob_ai` across {original + K paraphrases of the text}) adds Held-out Discriminative Gain (HDG) beyond the baseline **`confidence`** (folded `max(p,1−p)`) in predicting ChatGPT-detector correctness. **Fifth** real candidate on the ChatGPT-detector substrate; the **second** generated under the Descriptor Justification Layer, and the **first real instantiation of the adopted OVP v0.2 reference template**.
**Governing spec:** OVP v0.1 @ `ovp-v0.1-lock` (tag-only/byte-exact) for all gating rules; **judge/harness/guard built on the adopted v0.2 reference template** (`analysis/ovp_v0.2_template/`, rev8 @ `03ce7a4`, ADOPTED 2026-06-10). The Descriptor Justification Layer adds locked disclosure/interpretation/foil structure and does not alter any v0.1 gating rule.
**Status:** DRAFT — not locked. Descriptor Justification + pre-reg **warm-passed**; six discretionary pins (§11) **confirmed**; four warm-pass sharpenings applied (flip-rate operationalization §4/§11.2; structural no-peeking via a derived input file §8.1; Layer 6→7-item acknowledgment §0.5; Ancestry wording §3). Awaiting materialization + build-and-smoke + two cold passes.

---

## 0. Architectural framing

```
DETECTOR_OVP_CALIB        → froze the ChatGPT-detector HDG band [τ_lo, τ_hi] (USABLE BAND; locked)
DETECTOR_TRUNCATION_OVP   → `truncated`           → Inconclusive   (#1; input feature, B-information-source)
DETECTOR_LENGTH_OVP       → `text_length`         → Not-Validated  (#2; input feature, B-information-source)
DETECTOR_DIRECTION_OVP    → `predicted_prob_ai`   → Inconclusive   (#3; same single-pass probability as B)
DETECTOR_PREDCLASS_OVP    → `pred`                → Inconclusive   (#4; same single-pass probability as B; Layer first contact)
DETECTOR_PERTURBATION_OVP → THIS study: `perturbation_spread` → first candidate from an information source INDEPENDENT of B's single forward pass
```

**The structural point #1–#4 establish:** every prior detector candidate was either an **input feature** (`truncated`, `text_length`) or **derived from the same single-pass probability** B is computed from (`predicted_prob_ai`, `pred`). All four returned Inconclusive/Not-Validated — the prediction of "a candidate from the same information source as B is absorbed by B." `perturbation_spread` requires a **second (and further) forward pass** to compute, so by construction it carries information B's single-pass nature cannot contain. It is the first detector candidate with a genuine, non-trivial prior of a **Validated** verdict — and OVP's ledger has never issued one on real data.

---

## 0.5 Descriptor Justification Layer (locked disclosure — NOT an admission gate)

1. **Mechanism (disclosed).** *Instability under input perturbation.* The detector's `confidence` is a function of a single forward pass and is structurally blind to its own instability: texts whose `predicted_prob_ai` swings when the text is paraphrased (meaning preserved, surface form changed) are ones on which the detector is unreliable, and that swing is information no single output of the detector contains. Self-consistency / ensemble-disagreement as error predictors are documented. Mechanism-first, not availability.
2. **Baseline-blindness argument (mechanistic Ancestry; see §3).** `B = max(p,1−p)` is computed from **one** forward pass on the original text. `perturbation_spread` carries **variance information across paraphrases** that B (a single-point magnitude of the original) cannot carry — even though C's input space includes the original `p` that B is derived from. The information distinction is **statistical (spread vs point), not algebraic**: a logistic on `[B]` alone cannot fit C's contribution because C is not a function of B.
3. **What is actually being tested (the genuine uncertainty).** The verdict does **not** follow from the mechanism being real (the single pass provably cannot see the spread). It hinges on whether **confidence already absorbs the spread signal via training** — i.e. whether the detector has effectively encoded its own instability into its single-pass output even though the single pass cannot *compute* it at inference. **Sealed until the locked run** (the HDG-beyond-confidence is NOT computed pre-lock). The structural-orthogonality argument raises the prior of a positive above zero but does not predetermine it.
4. **Pre-committed interpretations (locked; anti-rescue):**
   - **Validated:** perturbation-disagreement adds discriminative information beyond single-pass confidence, **on the analyzed subset of the detector substrate** (the examples clearing the per-text ≥3-valid gate; §6), under this estimator, against the inherited band. Does **NOT** establish generalization beyond the detector, nor practical magnitude, **nor anything about the detector's reliability on the excluded texts** (those for which the pinned paraphraser produced < 3 valid paraphrases — concentrated in poetry/reddit under this config) — only that the structural orthogonality argument was correct on this subset.
   - **Not-Validated:** confidence **already absorbs** the perturbation-disagreement signal **on the paraphraseable subset** — the detector's training has encoded the instability information into its single-pass output. **Do NOT reach for "the paraphraser was too weak"** — fidelity (cosine/Jaccard) is the gate and excluded texts are disclosed, not hidden. A null *is* the finding **on the scoped subset; it says nothing about poetry/reddit.**
   - **Inconclusive:** C's incremental contribution sits in the band; no legitimacy claim.
5. **Surface foil (paired disconfirming control; §4/§6).** **Permuted `perturbation_spread`** — spread scores shuffled across examples — preserves C's exact marginal while destroying `C↔correctness`. Target-independent; run as a **non-gating diagnostic**, expected below `τ_lo`; the pre-committed caveat (§6) handles the case where it is not.
6. **Confound control (non-gating; the multi-pass-specific concern).** Distinct from target-independence: *is the gain genuine instability, or a proxy for a text property the paraphrasing co-varies with* — most obviously **length**. Handled by a **covariate diagnostic** (§4): HDG of C beyond `[B, text_length, domain]` vs beyond `[B]`, with a pinned `ε_confound` (§6). (The "C is a transformation of B" worry is auto-handled by HDG itself — a deterministic function of B gains nothing out-of-sample.)
7. **Target-fit.** **Correctness is the right target** — a reliability question ("does instability-under-paraphrase predict when the detector errs, beyond confidence"). Class-B mechanistic; no target mismatch.

*Layer-structure note (6→7 items).* The locked Descriptor Justification Layer seed is **6 items**, with the foil (item 5) covering both target-independence and any confound concern. The multi-pass construction here surfaces a distinct **confound class** — covariate co-variation with paraphrasing (e.g. length) — that item 5's permutation foil does not separately address, so this pre-registration treats confound discharge as a **new item (6 here, target-fit moved to 7)**. This is a Layer *extension* flagged explicitly, not silently introduced; whether the Layer's formal structure should incorporate it permanently is a v0.2-spec question, to be informed by this study's first-contact outcome.

---

## 1. Objective

Determine whether **`perturbation_spread`** carries out-of-sample information about **detector correctness** beyond the **folded confidence** `B` — i.e., whether the detector's instability under meaning-preserving paraphrase is confidence-orthogonal (a genuinely new, second-pass information source) or already encoded in its single-pass confidence.

---

## 2. Substrate, inheritance, and candidate materialization (hybrid — the structural novelty)

Unlike #1–#4 (zero new materialization), this candidate **inherits `B`, `y`, the band, and the estimator** from the locked calibration substrate, but **materializes `C` fresh**. Materialization is permitted pre-lock; the **HDG (and any `C↔y` relationship) is sealed to the locked judge** (§8).

**Inherited (hash-verified, NOT re-materialized):**
- **Model/dataset (pinned, provenance):** `Hello-SimpleAI/chatgpt-detector-roberta` @ `d2b342c61775d5dd0221808a79983ed3b86ffd86` over the RAID test subsample sha256 `a29f8f2c…ff615a47`.
- **`B`, `y`, the original `predicted_prob_ai`, and `domain` (`source_domain`)** from the calibration-locked `../detector_truncation_ovp/detector_per_example.csv`, sha256 **`24dac07828949a7e93fcc686ff3df70229c026195d3db873e688c1b401afc643`** (abort on mismatch). `(B, y)` byte-identical to the calibration substrate, so the inherited band applies. `domain` (inherited, not re-derived) is used only in the confound diagnostic (§4).
- **`text_length` is NOT in the inherited CSV** (build-time catch) — it is **materialized** alongside `C` (the materialization reads the text, so it emits character length per example, a non-`y` quantity), and used only in the confound diagnostic.

**Newly materialized candidate `C = perturbation_spread` (pinned; materialization reads the derived input file of §8 step 1(a) — `(id, text, predicted_prob_ai)` only, never `y`):**
- **Paraphraser (rev-3 — uniquely pinned, single path):** `Qwen2.5-7B-Instruct`, **4-bit bitsandbytes nf4**, @ revision **`a09a35458c702b33eeacc393d103063234e8bc28`**. **No fallback** — the materialization script requires bitsandbytes (`ImportError` aborts) and aborts on a resolved-revision mismatch (cold-pass-#1 (b) fix: the earlier "7B if available else 3B" auto-detect admitted two materializations from one pre-reg and is removed). (7B-AWQ was the original pin but has no working AWQ backend on Windows — vLLM/autoawq/gptqmodel all fail; bnb-4bit is the reachable 7B route.) Engine = `transformers` `generate`; **temperature 0.5 / top_p 0.95**, **`PARAPHRASE_SEED = 20260618`** (per-text reset), a **fidelity-first prompt (pinned verbatim in the manifest)**, **K = 5**.
- **The scientific object is the committed materialized artifact, not a reproducible procedure.** GPU sampling is **not bit-reproducible** (hardware/library nondeterminism), so re-running the pinned procedure will *not* regenerate `detector_perturbation_per_example.csv` byte-identically. The **committed bytes** (sha `ad5901b160b37c763752607f85cfd2f3ed2a3fe2bf5d0d48627ae5b1bddd5318`) are authoritative; the manifest sha and the judge's `EXPECTED_MATERIALIZED_SHA256` are the integrity check; the pinned procedure documents the artifact's **provenance**. (See §13 rev-3.)
- **Detector re-run:** the **same locked detector** @ `d2b342c6…` on each paraphrase, **first-512-token truncation** and `softmax(logits)[ai_class_index]` exactly as the original audit → `predicted_prob_ai` per paraphrase.
- **Spread statistic:** `perturbation_spread` = **std (ddof = 1)** of `predicted_prob_ai` over {original `predicted_prob_ai` (inherited)} ∪ {valid paraphrase probs}. *(flip-rate of `pred` retained as a non-gating sensitivity panel — §4; std is primary because flip-rate floors to zero on easy texts.)*
- **Paraphrase-quality control (pre-lock; touches NO `y`):** each paraphrase must clear **embedding cosine ≥ θ = 0.80** under `all-MiniLM-L6-v2` @ pinned revision **AND token-level Jaccard distance ≥ δ = 0.30** vs the original. A failing paraphrase is **excluded** from the spread. **OPERATIVE GATE (rev-2): per text ≥ 3 valid of 5**; texts below it are **excluded from the analysis as substrate attrition** (the verdict is scope-stamped to the included subset — §6). The **aggregate set-level pass rate is REPORTED ONLY — no threshold, no gating function** — so it cannot trigger a bar-recalibration loop. (The original ≥ 95 % set-level gate was demoted on 2026-06-19; see the Amendment Log — the basis is methodological: the aggregate gate did not correspond to the per-example scientific requirement.)
- **Persistence:** `detector_perturbation_per_example.csv` (`id, perturbation_spread, flip_rate, text_length, n_valid, mean_cosine, mean_jaccard_dist`) + the full paraphrase set and per-paraphrase probabilities, all hashed; the per-example sha pinned in the manifest. The judge inherits `(B, y, domain)` from the calibration CSV and **joins `perturbation_spread`, `flip_rate`, `text_length` by `id`**. **The judge verifies the materialized `id` set is identical to the inherited `id` set — no missing or duplicated ids — and aborts on mismatch.**

---

## 3. Baseline, candidate, and §2 baseline-rule conformance

- **Baseline `B`:** detector **confidence** = `max(p,1−p)` — the single-pass folded magnitude.
- **Candidate `C`:** **`perturbation_spread`** — the multi-pass disagreement statistic above.
- **Ancestry Statement (spec §2.5; mechanistic — the cleanest the program has written):** **`perturbation_spread` extends single-pass confidence by adding variance information across paraphrases that a single forward pass structurally cannot contain.** B is computed from one pass; C requires a second (and further) pass; the second pass's information is provably not in the first. The distinction is statistical (spread vs point), not algebraic: `B` is a single-point magnitude of the original, while `C` carries variance information across paraphrases that `B` (a scalar) cannot encode. `C` and `B` are correlated (C's inputs include the original `p` from which B is derived), so a logistic on `[B]` partially fits `C`'s contribution through that correlation — but **even the best linear function of `B` alone cannot fully fit `C`'s contribution to predicting `y`; the irreducible part is the spread component, the information the multi-pass construction makes available.** The claim under test is that this instability information is not already encoded in `B` via training.
- **§2 criteria:** (1) **same substrate** — same pinned detector model, same 2000 RAID examples, same `y`; C uses the detector on derived inputs (paraphrases) — an *extended materialization* of the same substrate, disclosed in §2; (2) **strictly extends** — nested `[B] ⊂ [B, C]`; (3) **pre-registered**; (4) **no post-hoc**; (5) **Ancestry** above. **One honest departure from #1–#4:** C requires new materialization (paraphraser + paraphrases + detector re-runs), with the new pinned dependencies and the no-peeking constraint of §8. Conforms.

---

## 4. HDG instantiation (pinned; inherited estimator) + foil + confound diagnostic

- **Measure (spec §1):** `D` = HDG = `AUC_test(pipeline[B, C]) − AUC_test(pipeline[B])`, out-of-sample.
- **Estimator (identical to the calibration / #1–#4):** `Pipeline(StandardScaler(with_mean=True, with_std=True), LogisticRegression(solver='lbfgs', C=1.0, max_iter=1000, fit_intercept=True))`, fit on the training partition only; `C` z-scored by the same scaler.
- **Split protocol:** repeated **stratified 50/50 train/test splits** on `y`, **R = 200**, baseline and candidate **paired**. **Master seed `0x5B5EAD`** — fresh, distinct from the calibration (`0xD37EC7`) and #1–#4 (`0x77C0DE`/`0x73C0DE`/`0xDEC0DE`/`0xC1A55D`). `SeedSequence(master).spawn(R)`, one child per replication.
- **The scalar `D` (pinned, identical form to #1–#4):** `D = median(HDG_AUC[1..200])` — ordinary median, all 200, no trimming; the gating verdict reads `D` alone.
- **PERMUTED-C FOIL (non-gating; pinned construction, identical to #4):** on the **same split** as the real candidate, compute `HDG_foil = AUC_test(pipeline[B, C_perm]) − AUC_test(pipeline[B])`, `C_perm` = `perturbation_spread` permuted across all examples. **Permutation RNG:** `foil_children = SeedSequence(0x5B5EAD ^ 0xF011).spawn(R)`; replication `r` permutes with `default_rng(foil_children[r])`. Full foil-HDG distribution + `D_foil = median` persisted. **Never enters `C`'s verdict.**
- **CONFOUND DIAGNOSTIC (non-gating; the multi-pass-specific control):** `HDG_extended = AUC_test(pipeline[B, text_length, domain, C]) − AUC_test(pipeline[B, text_length, domain])`, paired on the same splits (domain one-hot; computed only here, never in the gating model). Reported alongside `HDG_primary = D`. Interpreted by the §6 `ε_confound` criterion.
- **Sensitivity panel (non-gating; pinned):** `flip_rate` = the fraction of the **valid** paraphrases (those clearing the cosine/Jaccard control — the **same valid set the spread is computed over**, so the two statistics are consistent; invalid paraphrases pollute neither) whose detector predicted class (`pred_para = 1[predicted_prob_ai ≥ 0.5]`) disagrees with the original text's predicted class — an alternate (binary) spread statistic, reported but never gating; plus error-class AP median.

---

## 5. Inherited cut points (frozen; verbatim from the calibration result)

From `../detector_truncation_ovp/detector_calibration_results.json` (locked `detector-ovp-calib-result`):

- **`τ_lo = 0.02458901317356486`**
- **`τ_hi = 0.06829080323934116`**

**Provenance (spec §1):** external — the separate, pre-lock, independently-locked calibration under seed `0xD37EC7`, never sourced from this candidate's run. **Runtime guard (pinned):** the judge asserts its hardcoded `TAU_LO`/`TAU_HI` byte-identical to the calibration result each run, aborting on drift; complemented by the lock-time manifest check.
*(Confirmed at the warm pass: both values byte-identical to the locked calibration JSON. ✓)*

---

## 6. Verdict rule (spec §6; pinned) + foil / quality / confound pre-commitments

The gating verdict for **`perturbation_spread`** is read from the scalar `D` against the inherited band:

- **Validated** — `D > τ_hi`.
- **Not-Validated** — `D < τ_lo`: mechanism-agnostic in v0.1.
- **Inconclusive** — `τ_lo ≤ D ≤ τ_hi`: closed band; abstention, recorded with parity.

All three pre-committed and published identically. Guards (any failure invalidates the run, amended under a new tag): inherited per-example-hash (§2), materialized-`C`-hash (§2), estimator-identity (§4), runtime cut-point assert (§5), v0.2 template guards (§8).

**Operative gate + scope-stamp (rev-2, pinned).** The **operative gate is per-text ≥ 3 valid of 5**; texts below it are **excluded from the analysis as substrate attrition**, and the verdict is **scope-stamped: "on the N_included of 2000 RAID examples for which the paraphrase-quality control produced ≥ 3 valid paraphrases."** That scope statement appears in the result-document headline and the judge output; the attrition is poetry/reddit-driven (Amendment Log domain table). The aggregate **set-level pass rate is reported only (no threshold)**. The anti-rescue logic is preserved: "the paraphraser was too weak" is foreclosed because fidelity (cosine/Jaccard) is the gate and excluded texts are disclosed, not hidden.

**Foil pre-commitment (non-gating, pinned).** Expected: `D_foil` below `τ_lo` (and ≤ 0) — `C_perm` is target-independent and cannot lift held-out AUC in expectation; the band must reject it (band-validity check). **CAVEAT:** if `D_foil ≥ τ_lo` (persisted `foil_clears_tau_lo`), that is a **methodological red flag** (permutation/independence bug, leakage, estimator/band pathology), not legitimate marginal structure — it **suspends interpretive trust** in the run pending investigation, though `C`'s gating verdict (foil non-gating) is formally unaffected.

**Confound criterion (non-gating, pinned; `ε_confound = 0.005` HDG-AUC units).** The gain is interpreted as **genuine perturbation-instability iff `HDG_primary − HDG_extended ≤ ε_confound`** (adding length+domain does not materially absorb `C`). If `HDG_extended` collapses toward 0 while `HDG_primary > 0`, the gain is length/domain-mediated and the **result document carries that caveat** — same epistemic level as `foil_clears_tau_lo`. Non-gating: it qualifies interpretation, not the verdict.

---

## 7. Outputs (persistence contract)

To `detector_perturbation_results.json`, the single run writes (and nothing beyond): the scalar **`D`** + **verdict**; echoed `τ_lo`/`τ_hi` + `band_relation`; the **full per-replication HDG arrays** for the real candidate, the **permuted-C foil**, and the **confound-extended** model, R=200, under `hdg_distribution`; non-gating support (real HDG mean/P5/P95; band fractions; **`D_foil` median + `foil_verdict` + foil band fractions + `foil_pre_commitment_met` + `foil_clears_tau_lo`**; **`HDG_extended` median + `confound_gap = D − HDG_extended` + `confound_genuine` boolean (gap ≤ ε_confound)**; flip-rate sensitivity median + verdict; error-class AP median); the **substrate scope** (`scope` string, `n_examples`, `n_errors`, `n_total_substrate`, `n_excluded_substrate_attrition`, `attrition_fraction`); full **`meta`** (candidate/baseline labels, master+foil seeds, `PARAPHRASE_SEED`, paraphraser id+revision, K, spread ddof, θ/δ, ε_confound, R, detector id+revision, dataset sha, inherited + materialized per-example shas, estimator descriptor, cut-point provenance tag, UTC). *(The paraphrase-quality descriptors — set-level pass rate, attrition composition, cosine/Jaccard means — live in the **separate** `detector_perturbation_quality_summary.json`, not the result JSON.)* Becomes the **fifth** OVP ledger row — **conditional on #3 (`predicted_prob_ai`) and #4 (`pred`) having cleared their result-document citation gates; if either is still open, recorded as pending until it clears.**

---

## 8. Build-and-smoke, cross-pass, lock, execution (ordered)

1. **Materialize `C` (pre-lock; structurally constrained from `y`).** No-peeking is enforced **structurally, not by intent**:
   - **(a) Derived input file.** An upstream filter step reads the inherited `detector_per_example.csv` and writes a **derived input `detector_perturbation_input.csv` containing only `(id, text, predicted_prob_ai)`** — no `y_correct`/`label`/`is_ai_generated`. The materialization script reads **only this derived file**, so the file it sees **literally does not contain `y`**. The derived file is hashed; the manifest verifies its provenance (its columns byte-identical to the corresponding inherited columns) and that it carries no label column.
   - **(b) Source-level check (narrowed — cold-pass #2 (b) fix).** The materialization script **MUST NOT read the inherited outcome/ground-truth columns** `y_correct` (the OVP target) or `is_ai_generated` (the true class) **as data** — verifiable by inspecting its CSV field accesses (the only `row[...]` reads are `id`/`text`/`predicted_prob_ai`). The generic substring "label" is **not** in scope: `id2label` is the *detector's own output-class metadata* (needed for AI-class resolution, unrelated to the OVP target), and "labels" appears innocuously in the fixed prompt text. The check targets the **outcome/ground-truth data-column reads**, not the substring "label"/"y".
   - The script emits `detector_perturbation_per_example.csv` + the paraphrase artifacts + the quality stats, all hashed. The paraphrase-quality gate (§2) is checked here; failure → re-materialize under a new tag.

   This converts the no-peeking guarantee from operator discipline to **structural impossibility** — the same intent→mechanism upgrade the v0.2-template arc codified.
2. **Build-and-smoke the judge on the adopted v0.2 template.** Judge = sealed-loader over the materialized `C` + inherited `B,y`; shared **compute-core = the standardized-logistic HDG**. **The judge's runtime guards (all via `ovp_guard`):** the **H1 git-object self-guard** over `SEALED_SOURCES = {judge, compute_core.py, ovp_guard.py, .gitattributes}` (`assert_locked_or_refuse`), **output-exists** (`output_exists_or_refuse`), **input-hash** over the inherited + materialized per-example (`verify_input_hashes` on `EXPECTED_INPUT_SHA256`), and the **runtime cut-point assert** (`verify_cut_points`). *(Accuracy note, cold-pass-2-class warm catch: `closed_world_io` is the **smoke harness's** B2 deny-by-default surface, **not** the judge's — the judge is H1-protected and reads its pinned inputs. `ovp_attest.py` is the v0.2 template's separate signed-additive-attestation utility, carried in the committed set and available to attest the locked run; it is **not** invoked by the judge.)* **No-peeking (heightened):** running the judge computes `C`'s real HDG and is NOT the smoke; the **HDG-beyond-confidence is sealed and not computed pre-lock**. The smoke is a **separate synthetic harness** (loads only `B`, `y`; never the real `C`) confirming: known-null → Not-Validated; known-meaningful continuous → Validated; **the foil mechanic — a synthetic meaningful feature's permutation lands Not-Validated**; and a **synthetic confound check** — a length-proxy feature collapses under `[B, length]` (the diagnostic fires). Then the output-conformance check.
3. **Cross-pass:** warm review (Descriptor Justification pre-commitments + the new materialization/no-peeking surface + the foil/confound constructions), then **two independent executing cold passes** (fix-author cannot clear; route the whole committed directory).
4. **Lock** (`detector-perturbation-ovp-lock`): this pre-reg + the judge (+ `compute_core.py`, `ovp_guard.py`, `ovp_attest.py`, `.gitattributes`) + `materialization_manifest_detector_perturbation.json` — `make_manifest.py` re-hashes the five committed artifacts and **aborts on**: inherited-per-example-hash, derived-input-hash, the derived input's **no-label-column header** (must be exactly `id,text,predicted_prob_ai`), materialized-per-example-hash, **cut-point identity** vs the calibration JSON, and **detector + paraphraser revision identity** vs the recorded summary. *(The materialized-hash and cut-points are **also** enforced by the judge at run — `EXPECTED_MATERIALIZED_SHA256` + `verify_cut_points`; the paraphraser revision is **also** checked at materialization; the dataset sha is **recorded as provenance**, enforced upstream at the detector-calibration lock — not re-hashed here, as the dataset file is not in this study dir.)*, one atomic commit + signed tag. **Mark in `OVP_DESIGN_HISTORY.md`: first real instantiation of the adopted v0.2 template; Layer second contact.**
5. **Run exactly once** (no flags) → inherit + hash-verify `(B, y)`; join + hash-verify `C`; compute the real `{D_r}`, `D`, verdict; the foil; the confound-extended; the flip-rate panel; persist §7.
6. **Write the result** (`RESULT_DETECTOR_PERTURBATION_OVP.md`), route its cold cross-pass (citation gate), record the fifth ledger row.

Single-execution: a technical failure is documented and amended under a new tag, never silently re-run.

---

## 9. What this establishes / does not

- **Does:** issue OVP's fifth real verdict — whether `perturbation_spread` adds HDG beyond folded confidence under the pinned linear estimator — resolving whether the detector's instability-under-paraphrase is confidence-orthogonal (**Validated** — the program's first real positive) or already confidence-encoded (Not-Validated); exercise the **adopted v0.2 template on first real science**; and give the Descriptor Justification Layer its second contact across a structurally new mechanism class (multi-pass aggregation).
- **Does not:** decide scientific interest/use; establish generalization beyond this substrate/estimator/metric; prove the magnitude is practically useful even if Validated; change the §6 rung (community-validation still needs an externally-authored candidate).

---

## 10. Cross-pass plan

Two independent executing verification passes, ≥1 cold reader with no design-conversation context, before lock; fix-author cannot clear; route the whole committed directory (the two modules must be present). A warm pass precedes the cold passes; materialization + build-and-smoke + output-conformance is a precondition. Both pass verdicts carried into the ledger row.

---

## 11. Discretionary pins (for explicit pre-lock sign-off)

1. **Paraphraser (rev-3 — uniquely pinned):** `Qwen2.5-7B-Instruct`, 4-bit bitsandbytes nf4, @ revision `a09a35458c702b33eeacc393d103063234e8bc28`; **single path, no fallback** (bitsandbytes required, revision-checked); engine = `transformers`; temp 0.5 / top_p 0.95 / `PARAPHRASE_SEED = 20260618` / fidelity-first prompt. Scientific object = the committed artifact (sha `ad5901b1…`); GPU generation is not bit-reproducible, so the committed bytes are authoritative.
2. **K = 5**; spread = `std(ddof=1)` of `predicted_prob_ai` over {original + valid paraphrases}; **flip-rate sensitivity panel** = fraction of the **valid** paraphrases whose predicted class disagrees with the original's (defined §4; same valid set as the spread).
3. **θ = 0.80** cosine under `all-MiniLM-L6-v2` (pinned revision).
4. **δ = 0.30** token-Jaccard distance.
5. **Gate (rev-2):** operative = per-text ≥ 3 valid of 5 (texts below excluded as substrate attrition; verdict scope-stamped to the included subset); set-level pass rate reported-only, no threshold.
6. **ε_confound = 0.005** (HDG-AUC units; non-gating confound caveat). Master seed `0x5B5EAD`; foil RNG `^0xF011`; R = 200; cut points inherited verbatim (§5).

*End of draft pre-registration. Six pins confirmed and four warm-pass sharpenings applied; next: materialization + build-and-smoke + two cold passes; not locked.*

---

## 12. Relationship to #1–#4 and the Layer

Inherits the calibration's cut points, estimator, and `(B, y)` from the locked detector arc; unlike #1–#4 it **materializes its candidate fresh** (paraphraser + detector re-runs). Generated by the Layer's mechanism-first rule (instability the single pass cannot see), with the correctness target fit-checked, a permuted-C foil pinned, and a length/domain confound diagnostic added for the multi-pass construction. Its verdict is OVP's fifth ledger row — and the first candidate whose structural argument gives a real prior of a **Validated** outcome, recorded with parity whichever way it lands. First real exercise of the adopted v0.2 template.

---

## 13. Amendment Log (pre-lock; decisions made on substrate-intrinsic, no-`y` properties)

Each entry records a pre-lock amendment and the diagnostic that motivated it. These touch only paraphrase **fidelity** (cosine/Jaccard by domain) and the materialization gate — never `y`; the HDG remains sealed. The trail exists so a cold reader can distinguish principled bar-decision from peeking-iteration.

**2026-06-19T11:53Z — rev-2: gate redefinition + paraphraser config (single revision).**
- *Trigger.* The first materialization (3B-Instruct, temp 0.7, fidelity-neutral prompt) finished at **set-level pass 0.8707**, below the original ≥ 95 % set-level gate (228 of 2000 texts < 3 valid).
- *Diagnostic (label-free; descriptive).* Failures are 98 % cosine-drift, not insufficient diversity (Jaccard median 0.73 vs 0.30 bar; only 0.2 % fail Jaccard). **Under this one paraphraser/prompt/temperature**, the drift concentrates by domain, not length (`corr(len, n_valid) = −0.16`) — descriptive context, not evidence of a paraphraser-invariant substrate limit:

  | domain | per-text pass | mean cosine | | domain | per-text pass | mean cosine |
  |---|---|---|---|---|---|---|
  | abstracts | 0.988 | 0.937 | | recipes | 0.920 | 0.919 |
  | wiki | 0.981 | 0.939 | | books | 0.899 | 0.900 |
  | news | 0.949 | 0.919 | | reviews | 0.842 | 0.891 |
  | | | | | reddit | 0.761 | 0.874 |
  | | | | | **poetry** | **0.631** | **0.853** |

- *Methodological basis for the change (NOT a claim of intrinsic unreachability).* The change does **not** rest on "95 % is unreachable" — that would be an empirical claim drawn from a single paraphraser/config, which the diagnostic does not support. It rests on a methodological point that holds **regardless of the observed value or the paraphraser**: the **≥ 95 % set-level gate was exploratory and not empirically calibrated, and it does not correspond to the study's scientific requirement.** The hypothesis test ("does perturbation-disagreement add information") needs each *analyzed* example to have adequate perturbation coverage (≥ 3 valid paraphrases); it does **not** need 95 % of the corpus to clear a fidelity bar. The aggregate pass rate is a **descriptive property of the materialization process**, not a necessary condition for the test.
- *Honest status — and the question a cold reader should ask.* This is an **amendment made after observing (label-free) materialization behavior**, not a pre-existing design decision. The fair challenge is: **was the bar moved because the run failed it?** **No.** The 0.87 observation **surfaced** a latent design flaw; it did not **justify** the change. The justification is that the set-level gate was a **category error** — an aggregate descriptor mis-cast as a per-unit necessary condition (see the `OVP_DESIGN_HISTORY.md` lesson of the same date) — and that diagnosis holds **independent of the observed value**. The decisive test: **had the first run instead landed at 0.96 and *passed*, the same demotion would have been equally warranted**, because the aggregate was never the test's necessary condition. Three further checks a cold reader can verify: no labels were accessed and the HDG is sealed; the operative requirement was **strengthened, not relaxed** (sub-threshold texts are now *excluded and disclosed* rather than silently absorbed by a high aggregate); and the first materialization is retained as evidence. A reader who accepts the would-still-demote-at-0.96 counterfactual can confirm the discipline held.
- *Amendments.* (a) **Gate redefined:** operative = per-text ≥ 3 valid of 5; set-level reported-only (no threshold — cannot trigger a recalibration loop). (b) **Verdict scope-stamped** to the *analyzed subset* (examples with ≥ 3 valid paraphrases; §6); excluded texts disclosed as substrate attrition (concentrated, descriptively, in poetry/reddit under this config). (c) **Interpretation pre-commitments** (§0.5) scoped to that subset. (d) **Paraphraser rev-2:** 7B-Instruct-4bit (bitsandbytes) if reachable else 3B-fp16; temp 0.5; fidelity-first prompt.
- *Discipline.* One revision materialization under the rev-2 config; whatever attrition it yields is the honestly-named substrate the candidate tests against. **No further re-tuning** without an explicit, separately-recorded decision.

**2026-06-19 — rev-3: materialization path uniquely pinned (cold-pass #1 (b) fix; NO re-materialization).**
- *Finding.* Cold reader #1 flagged a **(b) too-narrow disclosure**: the pre-reg/script described the materialization as "pinned" while actually admitting two paths (7B-bnb-4bit if available, else 3B-fp16) — two hosts could materialize different `C` from one pre-registration. The reader affirmed every other integrity mechanism; the design is sound, the disclosure was too narrow.
- *Fix (reader's options 1 + 2).* The auto-detect/3B fallback is **removed**; the single pinned path is the one the rev-2 run *actually used* (`Qwen2.5-7B-Instruct`, bnb nf4 4-bit, @ `a09a35458c702b33eeacc393d103063234e8bc28`); the materialization script now **requires bitsandbytes (`ImportError` aborts) and aborts on a resolved-revision mismatch**; and the disclosure (§2) states explicitly that the **scientific object is the committed artifact** (sha `ad5901b1…`), since GPU sampling is not bit-reproducible — the committed bytes are authoritative, the pin documents provenance.
- *No re-materialization.* The rev-2 artifact is **unchanged and stands** (it was produced under the now-pinned 7B path; the quality summary already records `paraphraser_id`/`paraphraser_4bit`/`resolved_revision` consistent with the pin). This is a spec/disclosure correction, not a new materialization.
- *Disposition.* (b) **resets** the cold-pass count. Changed bytes: `materialize_perturbation.py` (the pin) + §2/§11.1/§13. The corrected directory routes for fresh cold passes before lock.

**2026-06-19 — rev-4: two (b) disclosure/coverage fixes (cold-pass #2; NO re-materialization).**
- *Findings.* Cold reader #2 raised two **(b)** overstated-coverage items: (i) §8.4 claimed the manifest aborts on a bundle of identity checks `make_manifest.py` did not implement (it only hard-checked the inherited + derived hashes); (ii) §8.1(b)'s literal ban on the substring "label"/"y" is unpassable, because the materializer legitimately uses `id2label` (detector output-class metadata) and "labels" in the prompt — the substantive no-peeking (reads only `id`/`text`/`predicted_prob_ai`) holds, but the *grep-check* was mis-specified.
- *Fixes.* (i) `make_manifest.py` now genuinely aborts on inherited/derived/**materialized** hashes, the derived input's **no-label-column header**, **cut-point identity** vs the calibration, and **detector + paraphraser revision identity** vs the recorded summary — and §8.4 attributes each guarantee to its enforcement point (manifest / judge-at-run / materialization / upstream provenance). (ii) §8.1(b) is narrowed to ban the **outcome/ground-truth data-column reads** (`y_correct`, `is_ai_generated`), with `id2label`/prompt-"labels" explicitly out of scope; the materializer docstring is corrected to match.
- *Warm self-audit (iii).* Prompted by the two cold (b)'s, a warm re-audit found a parallel over-attribution in §8.2 — `closed_world_io` and signed-attestation were listed as *judge* runtime mechanisms; they belong to the smoke (B2) and the separate `ovp_attest` tool. §8.2 now lists only the judge's actual guards (H1 / output-exists / input-hash / cut-point assert). The same audit corrected **§7** (persistence contract), which had claimed the *result JSON* contains the paraphrase-quality summary (with a stale `quality_gate_met`) and a `derived-input sha` in meta — neither is written by the judge; §7 now lists the actual result fields, and notes the quality descriptors live in the separate quality-summary file. The other "code does X" claims (§2 id-set check, §5 cut-point assert, §6 guard list) were re-checked and conform.
- *No re-materialization.* Changed bytes: `make_manifest.py`, `materialize_perturbation.py` (docstring only — no behavior change), §7/§8.1(b)/§8.2/§8.4/§13. The materialized artifact is unchanged; `make_manifest.py` must be **re-run** to regenerate the manifest JSON under the new checks.
- *Disposition.* (b) **resets** the cold-pass count again; the corrected directory routes for fresh cold passes before lock.

**2026-06-19 — rev-5: single-execution made structural (cold-pass #3 — first (a)).**
- *Finding.* Cold reader #3 raised the first **(a)** (broken provable guarantee): `judge_perturbation.py` exposed `--seed`/`--reps`/`--out`, and the output-exists guard only blocks reuse of the *same* output path — so `--seed X --out other.json` permits another sealed computation under varied params, letting an operator run many configs and cherry-pick the verdict. The pre-reg's "run exactly once (no flags)" was a claim the code did not enforce.
- *Root cause.* The adopted v0.2 `judge_template` has **no** flag surface; the flags were copied from #4's pre-v0.2 `--seed/--reps/--out` pattern — an author deviation from the template, not a template defect. (It is also the *same* claim↔code gap class as the rev-4 (b)'s — the "no flags" execution-discipline claim went un-audited; the audit lesson now explicitly covers execution-discipline claims.)
- *Fix (structural).* The judge now takes **no arguments**: `if len(sys.argv) > 1: abort`; canonical `seed/reps/out` hardcoded; the output-exists guard then enforces once-per-checkout. Reproducibility verification is a fresh checkout of the lock tag + this canonical run, compared to the committed result tag — not a re-run with flags.
- *Grandfathering note.* The same flag surface exists in the locked #1–#4 judges (WARN-and-proceed); there it was enforced by operator discipline + visible commit history, not structurally. Those are locked and not re-opened; the v0.2 standard (structural, not operator-discipline) is why #5 closes it. Forward: future judges instantiate the template's **no-flag** structure.
- *Disposition.* (a) **resets** the cold-pass count. Changed bytes: `judge_perturbation.py` (+ §13). The corrected directory routes for fresh cold passes before lock.

**2026-06-19 — rev-6: flip_rate operational-definition disclosure fix (cold-pass #4 (b)).**
- *Finding.* Cold reader #4 found §4/§11.2 defined `flip_rate` as "fraction of the **K** paraphrases," but the materializer computes it over **valid** paraphrases only (`np.mean([pp != orig_pred for pp in valid_preds])`). Non-gating (a sensitivity panel) but a pinned reported statistic, so the disclosure must match.
- *Fix (disclosure → code).* §4/§11.2 now say "fraction of the **valid** paraphrases" — also the principled definition: the same valid set the spread is computed over, keeping the two statistics consistent and excluding non-faithful paraphrases from both.
- *Grounded operational-definition sweep.* Prompted by this being a *third* audit-miss class, every pinned formula was re-verified against the code **by grep, not memory**: `spread = std(ddof=1)` over {original + valid}; `flip_rate` over valid; `text_length = len(text)`; `valid = cos≥θ ∧ jd≥δ`; foil xor `0xF011`; confound `[B,Z,C]−[B,Z]`, gap `D−HDG_ext`, genuine `≤ε`; verdict `D>τ_hi / D<τ_lo`; seeds `0x5B5EAD`/`^0xF011`, `ε=0.005`, `K=5`, ddof 1 — all conform.
- *Disposition.* (b) **resets** the cold-pass count. Changed bytes: §4/§11.2 (+ §13). The corrected directory routes for fresh cold passes before lock.

**2026-06-19 — rev-7: `.gitattributes` filenames corrected (cold-pass #5 — first CLEAN; non-gating hygiene fix).**
- *Pass.* Cold reader #5 returned **CLEAN** (no (a)/(b)) on a static cross-check, verified against the code (not prose): structural no-peeking, the closed flag surface (rev-5), H1 covering the whole sealed path + running first + fail-closed, the inherited/derived/materialized/cut-point hash chain agreeing across judge/manifest/quality-summary, the estimator/foil/confound/spread/flip_rate formulas, and the scope-stamp arithmetic (1785/215/2000 = 0.1075). **Static only** — the reader could not mount the directory, so did not execute `py_compile`/smoke/`--verify` or re-hash the CSV bytes; pinned-value *agreement* was confirmed, on-disk *byte-hash* was not.
- *Non-gating observation → fixed.* The committed `.gitattributes` `-text`-marked the **template** filenames (`judge_template.py`/`smoke_template.py`), not this study's `judge_perturbation.py`/`smoke_perturbation.py` — an instantiation miss (template copied without filename substitution). The reader correctly judged it **not (a)/(b)**: SEALED_SOURCES enumerates the real filenames, so H1 still hashes byte-identity for the actual judge/smoke; the missing `-text` only removes a line-ending-normalization belt-and-suspenders (worst case redundant fail-closed, never fail-open). Corrected to the real filenames as pre-lock hygiene.
- *Disposition.* Reader #5's pass = **CLEAN #1** (the fix is reader-prescribed + guarantee-neutral — editorial-class). The corrected directory routes for a **second cold pass — ideally executing** (mounted), to confirm the on-disk CSV bytes hash to the pins (the gap the static pass left open). Two clean → lock. Changed bytes: `.gitattributes` (+ §13).
