# RESULT — SST2_OVP_CALIB (cut-point calibration sub-study, lock 1)

**Study:** SST2_OVP_CALIB — substrate-specific HDG cut-point calibration on the DistilBERT-SST2 confidence/correctness substrate (lock 1 of the two-lock arc for OVP's first real candidate audit).
**Governing spec:** OVP v0.1 @ signed tag `ovp-v0.1-lock`.
**Lock:** signed tag `sst2-ovp-calib-lock` (pre-reg + `calibrate_sst2_cutpoints.py` + `materialization_manifest_sst2_calib.json`; two clean cold passes on byte-identical artifacts).
**Execution:** single run, master seed `0x55712`, `R_cal = 200`, 2026-06-08 UTC; outputs at signed tag `sst2-ovp-calib-result`.
**Citation gate:** this result is citable only after its own cold cross-pass (spec §7); see `CROSSPASS_SST2_OVP_CALIB.md`.

---

## Outcome: **MIS-SPECIFIED** — via §6 check 1 (`τ_lo > 0` failed; `τ_lo = 0.0` exactly)

| §6 separability check | Result |
|---|---|
| 1. `τ_lo > 0` | **FAIL** — `τ_lo = max(P95_redundant, P95_noise) = max(0.0, −0.0862) = 0.0` |
| 2. valid band, gap ≥ δ=0.01 | pass — `τ_hi = 0.01613` (σ_m = 0.5), gap 0.0161 |
| 3. monotonicity + nulls non-positive | pass — 8-point sweep monotone; both null means ≤ 0 |

This is the **pre-committed mis-specification exit** (pre-reg §6): a finding about the substrate–instrument pair, not a failure of the protocol. **Per the locked pre-registration, the negation candidate study (lock 2) does not proceed on this calibration.** Any continuation is a **new pre-registration under a new lock** — nothing is fudged into a band.

## The numbers (auditable from the frozen artifacts without a re-run — `sst2_calibration_results.json` unless noted; all percentiles below use the pinned numpy `'linear'` rule)

- Substrate: n = 872, errors = 78 (accuracy 0.911). Baseline `AUC(B→y)` median **0.860**.
- **Confidence is extremely compressed** (source: `sst2_per_example.csv`, sha256 `e9e5b12a…b7bec1c7` per the results meta — these three figures are *not* derivable from the results JSON): median `B` = 0.9995, IQR [0.9968, 0.9998], 84.4% of examples above 0.99.
- **Noise null (`C ~ N(0,1)`): negative in 200/200 replications** — mean −0.240, max −0.011, P95 −0.086.
- Redundant null (`2B−1`): HDG exactly 0.0 in all 200 replications (monotone affine of `B`; ranking-invariant).
- Meaningful sweep: only σ_m = 0.5 clears (P5 +0.01613, **positive in 199/200 replications** — the single exception −0.0070); σ_m ≥ 1.0 has **negative mean HDG** (−0.092 … −0.235), monotone in σ_m.
- Error-class AP panel shows the same shape: noise null −0.154 mean, **P95 −0.0399, 100% ≤ 0** (max −0.0025); only σ_m = 0.5 positive (+0.338).

## Mechanism (why the exit fired here, and why it fired through this door)

The pre-registration named the anticipated failure mode: class imbalance widening the null's **positive** tail and pushing `τ_lo` up into the meaningful range (band collapse, check 2). **The actual failure was the opposite.** On this substrate the null upper tail is not fat — it is entirely **below zero**, so the max-of-95ths rule returns exactly 0 and strict positivity (check 1) fails.

The substrate geometry explains it: `B` is compressed into a sliver below 1.0, so under the pinned **unstandardized** L2 logistic, `B` needs a very large coefficient to express its tiny dynamic range, while an `N(0,1)` feature needs almost none — any nonzero weight on a junk feature scrambles the compressed ranking out-of-sample. Junk features don't merely fail to help here; they reliably hurt. A floor rule built from null *upper tails* cannot produce a strictly positive floor on a substrate where nulls strictly hurt. (Note the structural corollary: the deterministic-affine null is identically zero by ranking invariance, so under max-of-95ths, `τ_lo = 0` exactly whenever the stochastic null's P95 is non-positive.)

The pinned "unstandardized features" choice — inherited faithfully from the synthetic positive control, where scales were controlled — interacts badly with a real compressed confidence scale. That interaction is the central design lesson of this study.

## What this result does and does not establish

- **Does:** establish that the SST-2 confidence/correctness substrate, under *this* HDG instantiation (unstandardized L2 logistic, AUC, stratified 50/50 splits, n = 872), does not admit a strictly positive null floor via the max-of-95ths rule — and therefore no valid decision band. The instrument itself is not dead: a strong known signal (σ_m = 0.5) was detected in 199/200 replications.
- **Does not:** say anything about `negation_count` (never reached); invalidate OVP (the exit firing *is* the protocol working); generalize to other substrates, estimators, or metric instantiations; move the spec-§6 maturity ladder (this study yields no ledger verdict, as pre-registered).

## Paths forward (each a new pre-registration; none is a continuation of this lock)

1. **Decompress the feature scale** — standardize features, or transform `B` (e.g., logit/rank) before the logistic. Directly addresses the identified mechanism; departs from positive-control parity on the one pin shown to interact badly with real data.
2. **Revise the floor rule** for substrates with strictly-harmful nulls (e.g., a floor from the null distribution's magnitude rather than its upper tail). Requires care not to become an arbitrary ε-fudge.
3. **AP-primary instantiation** — *contra-indicated by this run's own panel*: the error-class AP noise null is also 100% ≤ 0, so the same degeneracy is expected.
4. **Larger substrate** (more errors → less overfitting punishment) — does not address the compression mechanism by itself.
5. **Abandon this substrate** for the first real candidate audit.

## Provenance

Dataset `sst2_validation.csv` sha256 `a0b4a680…2588376d` (verified at lock and at run); model `distilbert-base-uncased-finetuned-sst-2-english` @ `714eb0fa89d2f80546fda750413ed43d93601a13` (3-way identity enforced at lock); per-example materialization `sst2_per_example.csv` sha256 `e9e5b12a…b7bec1c7` (durable file + results meta); environment per `materialization_manifest_sst2_calib.json` (Python 3.12.10, numpy 2.1.2, scikit-learn 1.8.0, transformers 5.9.0, torch 2.12.0+cpu). Full per-replication HDG distributions (AUC and AP, 10 constructions × 200) persisted under `hdg_distributions` per the §7 persistence contract — every claim above is checkable from the frozen artifacts alone.

*Lock-convention note:* the locked pre-registration's body retains its "Status: DRAFT — not locked" line; per the project's tag-only/byte-exact convention (as with the OVP v0.1 spec itself), the lock is carried by the signed tag `sst2-ovp-calib-lock` and the cross-pass record, not by a status edit that would have broken byte-identity with the artifacts the cold readers cleared. Verify via `git tag -v sst2-ovp-calib-lock`.
