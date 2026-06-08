# Pre-Registration — SST2_OVP_CALIB (cut-point calibration sub-study)

**Study type:** Substrate-specific cut-point calibration study — the OVP §1 "bootstrap path" instantiated on **real data**. It is **lock 1 of the two-lock arc** for OVP's first real candidate audit; it does **not** judge any real candidate.
**Governing spec:** OVP v0.1, locked at signed tag `ovp-v0.1-lock`. **Lock-status note:** OVP v0.1 was locked **tag-only / byte-exact** — the spec *body* retains its "working draft — not locked" line by design; the authoritative lock is carried by the signed tag, `OVP_v0.1_LOCK_NOTICE.md`, and `OVP_DESIGN_HISTORY.md` (verify via `git tag -v ovp-v0.1-lock`). This study conforms to the spec at that tag; the spec governs.
**Status:** DRAFT — not locked. (Review-progress is tracked outside this artifact, in the cross-pass record, not narrated here.)

---

## 0. Architectural framing (the two-lock arc) and what this study does NOT establish

OVP_POSCONTROL_v1 validated the decision rule **in a synthetic world**. It did **not** create universal cut points: HDG (ΔAUC) is scaled by the substrate's target distribution, feature geometry, and sample size, so the positive control's `τ_lo`/`τ_hi` do not transfer to real data. Per spec §1, a real candidate study needs its **own** externally-sourced cut points → a substrate-specific calibration. Hence two locks:

```
OVP_POSCONTROL_v1            → proves the validator can ring true (done; PASS)
SST2_OVP_CALIB  (this study) → freezes SST-2-specific τ_lo / τ_hi
SST2_NEGATION_OVP (lock 2)   → judges whether negation_count earns its existence beyond confidence
```

**The first execution of OVP's first real audit is this study — not the negation test.** This study answers: *what do null, redundant, and meaningful HDG distributions look like on the SST-2 confidence/correctness substrate?* Only once that is fixed can negation be judged.

**This study does NOT:** judge negation or any real candidate; validate OVP generally; establish anything about weather, descriptors, or any other domain; move the §6 maturity ladder. It only **sets the ruler** for one substrate. A v0.x reader should not read more into it.

---

## 1. Objective

Produce externally-sourced decision cut points (`τ_lo`, `τ_hi`) on the **SST-2 confidence/correctness HDG scale**, before the negation candidate study, by measuring what HDG known-null vs known-meaningful constructions produce on this real substrate — never from the candidate study's own run.

---

## 2. Substrate and materialization

- **Dataset (pinned):** the DistilBERT-SST2 validation set already materialized and hashed for the DistilBERT-SST2 calibration audit — `case_studies/distilbert_sst2/sst2_validation.csv` (872 examples; columns `idx, sentence, label`), `sst2_validation_sha256.txt`.
- **Model (pinned):** the **same pinned DistilBERT-SST2 model revision** as that audit (`PRE_REGISTRATION_DISTILBERT_SST2_v1.md` / its materialization manifest). Deterministic inference (no sampling), so per-example outputs are reproducible.
- **Per-example materialization (produced here and inherited by lock 2):** run the pinned model once over the 872 sentences to produce, per example: predicted probability, predicted label, **`B = confidence`** (max softmax probability), and **`y = correctness`** (`1` if predicted label == true label, else `0`). Written to `sst2_per_example.csv` with a SHA-256 persisted durably (`sst2_per_example_sha256.txt`, also recorded in the results meta — never stdout-only). `negation_count` is **not** computed here (it is the lock-2 candidate); the calibration uses only `B`, `y`, and the substrate size.

Note: `y` is expected to be **imbalanced** (DistilBERT-SST2 is ~90%+ accurate, so the "wrong" class is small — roughly 80–100 errors in 872). This is the central reason the calibration must be substrate-specific; see §6/§7.

---

## 3. HDG instantiation (pinned)

- **Primary discrimination metric:** ROC **AUC** on a held-out split — pinned for **consistency with OVP_POSCONTROL_v1**, so a verdict's interpretation matches across the two studies.
- **Sensitivity panel (reported, not gating):** **average precision (AP)**, area under the precision–recall curve, which focuses on the rare-positive (error) class. **Implementation (pinned):** the AP panel treats **error as the positive class** — it relabels `1 − y` (so `1` = error) and scores the model's predicted error probability `1 − P(correct)`, i.e. AP for *detecting errors*. (This is the result-affecting choice that makes AP serve its imbalance-robustness purpose; AUC, being class-symmetric, is unaffected by the relabel.) AP is reported alongside every HDG figure as an imbalance-robustness check; it does **not** set the cut points in v1. (A future *pre-registration* may pin AP as primary; that would be a new **locked study under the same OVP version** — a per-study metric instantiation, not a new OVP *version* — per spec §1/§6.)
- **Estimator / function class:** L2 logistic regression (`solver='lbfgs'`, `C=1.0`, `max_iter=1000`, `fit_intercept=True`), features not standardized — identical to OVP_POSCONTROL_v1.
- **`D = AUC_test(logistic[B, C]) − AUC_test(logistic[B])`** on the held-out test split.
- **Resampling scheme (the key real-data pre-commitment):** because the dataset is **fixed** (872 examples), "replications" are **repeated stratified 50/50 train/test splits** of the same 872, stratified on `y` (correctness) so each half carries a comparable error rate. This is the **single resampling scheme used in this version** (no bootstrap is run — see the estimand note). *What the HDG distribution represents:* the variance of HDG over alternative partitions of this fixed dataset — i.e., "given these 872 labelled examples, how stable is the candidate's incremental gain across train/test partitions." **This partition-variance estimand is the question this study cares about.** A bootstrap targeting the broader-population estimand (how HDG would vary across resamples of the SST-2 *population* — a weaker, dependency-laden quantity) is a **different question and is deliberately not run in this version** — a scope decision, not a computation we were unable to perform. (Should a population-estimand sensitivity panel ever be wanted, it is a new pre-registration with its own pinned bootstrap mechanics.)
- **Replications:** `R_cal = 200` stratified splits per construction. **Master seed `0x55712`** (distinct from the lock-2 candidate study's seed). *Seed derivation (pinned mechanism):* NumPy `SeedSequence(master).spawn(R_cal)` — **one child per replication, index order**. Within a replication, each construction draws its noise and then its own split seed from the same advancing child stream, so **constructions are not split-paired within a replication**; each construction still receives `R_cal` valid, fully master-seed-determined stratified splits. This is sound because the cut-point rules use each construction's **marginal** HDG distribution only — no cross-construction contrast is computed, so pairing is not required. (Lock 2, which *does* compare a candidate against cut points, pins its own split structure explicitly.) Implemented in the locked `calibrate_sst2_cutpoints.py`.

---

## 4. Calibration constructions (synthetic candidates on the real substrate)

Computed on the real `(B, y)` per-example data; same forms as OVP_POSCONTROL_v1's calibration, adapted because real data has no controllable latent — the meaningful construction is built from the target `y` itself:

- **Null-redundant:** `C = 2·B − 1` (deterministic affine of confidence) — recoverable from `B`, carries no incremental information about `y`. HDG ≈ 0.
- **Null-noise:** `C = Normal(0,1)` per example, independent of everything. HDG ≈ 0.
- **Meaningful sweep:** `C = y + Normal(0, σ_m²)` — a **noisy copy of the correctness target**, which by construction carries genuine correctness signal beyond `B`. Swept over `σ_m` on the pinned grid **{0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0}** — uniform 0.5 spacing across the full range (larger `σ_m` = noisier = weaker). As `σ_m → 0`, `C → y` (HDG → ceiling); as `σ_m → ∞`, `C → noise` (HDG → 0); intermediate `σ_m` maps the gradient. (`y + noise` is a legitimate synthetic *calibration* construction, exactly analogous to the positive control's `s2 + noise` meaningful arm; it leaks the target *by design* to establish what a meaningful gain looks like, and is never used in the candidate study.)

Each construction / grid point is evaluated over `R_cal = 200` stratified splits.

---

## 5. Cut-point rules (pinned here; values produced by the run)

All percentiles use numpy default `'linear'` (type-7) interpolation (result-affecting; fixed).

- **`τ_lo` = `max( P95(HDG | null-redundant), P95(HDG | null-noise) )`** — the higher of the two nulls' 95th percentiles, placing `τ_lo` above the 95th percentile of *each* null type. Must be strictly positive.
- **`τ_hi`** — from the meaningful sweep, by an explicit three-step rule: **(1)** identify the sweep points whose `P5(HDG) > τ_lo + δ` (margin `δ = 0.01` AUC); **(2)** among those, choose the one with the **largest `σ_m`** (the weakest meaningful signal that still clears); **(3)** set `τ_hi = ` that point's `P5(HDG)`. This keeps `τ_hi` as low as separability allows. *Grid-resolution note:* "weakest clearing point" is bounded by the sweep grid's spacing. The grid is pinned at **uniform 0.5 spacing across the full range** — refined from an earlier grid that was coarser (1.0 gaps) precisely past `σ_m = 2.0`, which is the high-`σ_m` region where the weakest-clearing-point rule operates by construction; the added `2.5` and `3.5` are the most likely "weakest clearing" candidates, so the refinement puts fine resolution exactly where `τ_hi` is determined. A residual discretization at the 0.5 quantum remains (a continuous sweep could place `τ_hi` between grid points); the design accepts the band the **pinned** grid produces, and this reduced dependency is a documented limitation.

(No arm-placement parameters are frozen here: unlike the positive control, the lock-2 candidate study judges a **single real candidate**, not synthetic arms, so only `τ_lo` and `τ_hi` are produced.)

---

## 6. Separability check / **mis-specification exit (a pre-committed outcome, not a failure)**

After the run, **all** must hold; otherwise the design is declared **mis-specified** and is documented + revised under a **new** lock, never fudged into a band:

1. `τ_lo > 0`.
2. `τ_lo < τ_hi` with a gap `≥ δ = 0.01` AUC — **a valid band exists.**
3. Monotonicity: mean HDG on the meaningful sweep increases **non-strictly** (`≤` between adjacent points, weakest→strongest) as `σ_m` decreases, over **8** sweep points — a longer monotone sequence than a 6-point grid would require, a slightly stronger generator sanity check; both nulls have mean HDG `≤ ~0`, **encoded in the locked script as `mean ≤ 1e-9`** (a strict near-zero tolerance whose only failure direction is the conservative, pre-committed MIS-SPECIFIED exit).

**Pre-committed possibility (named in advance):** because correctness is imbalanced, the error class is small, so HDG sampling variance is wide, the null distribution is wide, and `τ_lo` is pushed up. It is therefore a **real possibility** that the null and meaningful HDG distributions overlap such that **no valid band exists (`τ_lo ≥ τ_hi`)**. If that happens, this study returns **MIS-SPECIFIED** — and that is **the discipline working, not a failure**: it is an honest finding that *the SST-2 confidence/correctness substrate does not support clean HDG separation at this `N`* — a statement about the **substrate**, not about negation (which is never reached). The negation candidate study does not proceed in that case; options would be a larger substrate, a different metric instantiation (e.g., AP-primary, which the corrected error-class AP panel here would inform), or abandoning this substrate — each a new pre-registration.

---

## 7. Outputs frozen into the candidate study

**Persistence contract:** under single-execution discipline, anything the one locked run does not persist is unrecoverable without a forbidden re-run — so the run must write **everything needed to audit it**, and **nothing beyond this pinned set**.

**Pinned output set, written to `sst2_calibration_results.json`:**

- `τ_lo`, `τ_hi`, and the `σ_m` at `τ_hi`;
- the **full per-replication HDG arrays** — all `R_cal` values per construction, **AUC and AP** — under `hdg_distributions` (keys: `null_redundant`, `null_noise`, `meaningful:<σ_m>`);
- summary support: the null P95s; the **null means** (the §6-check-3 inputs, persisted so check 3 is auditable from the frozen artifact); the meaningful-sweep P5s and means; the AP sensitivity-panel means; `baseline_auc_median_nullnoise_splits` — the median held-out baseline `AUC(B→y)`, which is construction-independent and sampled over the null-noise splits (a context diagnostic, not gating); `n_examples`; `n_errors`;
- the §6 separability-check booleans and the verdict string;
- meta: canonical and used seed, canonical and used replication count, `δ`, model id + revision, the per-example CSV SHA-256, and a UTC timestamp.

**Durable materialization records:** `sst2_per_example.csv` plus `sst2_per_example_sha256.txt` (the hash is also recorded in the results meta — it must not live only in transient stdout, since lock 2 inherits it).

If a valid band exists: `τ_lo`, `τ_hi` (with the supporting distributions above) are frozen into `PRE_REGISTRATION_SST2_NEGATION_OVP.md` (lock 2) before *its* lock. The per-example materialization + hash are inherited by lock 2 (the candidate study reuses the same `B`, `y`, and adds `negation_count`).

---

## 8. Materialization, lock, execution (this study's ordered steps)

1. **Cross-pass** this pre-registration (warm review against the three pinned pre-commitments, then **two independent cold passes**, ≥1 cold, fix-author cannot clear).
2. **Lock** (`sst2-ovp-calib-lock`): this pre-reg + `calibrate_sst2_cutpoints.py` (which also materializes `sst2_per_example.csv` from the pinned model) + materialization manifest, one atomic commit + signed tag.
3. **Run exactly once** → materialize per-example `(B, y)`; produce `τ_lo`, `τ_hi`, the HDG distributions (AUC + AP), and the §6 separability result — **persisting exactly the §7 pinned output set** (full per-replication arrays, summaries incl. null means, durable hashes), so the run is auditable from the frozen artifacts alone.
4. **Freeze** outputs into the candidate study (or, if MIS-SPECIFIED, publish that finding and stop).

Single-execution: a technical failure is documented and amended under a new tag, never silently re-run. The outcome is recorded regardless of whether a band emerges.

---

## 9. What this establishes / does not (restated)

- **Does:** fix the SST-2-specific HDG cut points (or honestly report that no valid band exists at this `N`), on the same instantiation the candidate study will use, sourced independently of the candidate run.
- **Does not:** judge negation; validate OVP; move the §6 ladder; generalize beyond this substrate.

---

## 10. Cross-pass plan

Two independent verification passes, ≥1 cold reader with no design-conversation context, before lock; the fix-author (including the AI collaborator) cannot be a clearing reader. A warm pass against the three pinned pre-commitments precedes the cold passes; it does not substitute for them. Recorded in `CROSSPASS_SST2_OVP_CALIB.md`.

---

## 11. Discretionary pins (pinned as written; for explicit pre-lock sign-off)

1. Primary metric AUC; sensitivity panel AP, computed on the **error class** (relabel `1 − y`, score `1 − P(correct)`).
2. Resampling: repeated stratified 50/50 splits — the single scheme; **no bootstrap in this version** (deliberate scope decision; the partition-variance estimand is the target, not the population estimand).
3. `R_cal = 200`; full 872 examples re-split each replication.
4. Meaningful sweep `σ_m` grid {0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0} (uniform 0.5 spacing — refined from {0.5, 1.0, 1.5, 2.0, 3.0, 4.0} to remove the coarse high-`σ_m` resolution where the `τ_hi` rule operates); null forms (`2B−1`, `N(0,1)`); percentile rule (max-of-95ths `τ_lo`, P5-of-weakest-clearing `τ_hi`); margin `δ = 0.01` AUC.
5. Estimator: L2 logistic, `C=1.0`, `max_iter=1000`, `fit_intercept=True`, unstandardized.
6. Seed `0x55712`; numpy `'linear'` percentile interpolation.
7. Pinned model revision: the DistilBERT-SST2 revision from the calibration audit's manifest (recorded exactly at materialization).

*End of draft pre-registration. Awaiting warm pass + two cold passes; not locked.*
