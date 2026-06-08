# Script-build findings — judge_truncation.py vs the DETECTOR_TRUNCATION_OVP pre-reg (lock 2)

Build-and-smoke precondition. Script built strictly to the pre-reg; smoke run on a non-canonical seed **before** cold-pass routing. **Discipline constraint honored: the smoke does NOT compute `truncated`'s HDG** — the real verdict is the locked single-execution output and must stay sealed pre-lock. The smoke exercised the verdict machinery on **synthetic candidates only**, loading `B` and `y` and explicitly ignoring the `truncated` column.

## Build conformance

`judge_truncation.py` compiles (`py_compile` OK). Pins verified against the pre-reg: candidate `truncated` / baseline confidence; `D = median(HDG_AUC[1..200])` ordinary median over all 200 (`np.median`, no trimming); verdict `D>τ_hi→Validated`, `D<τ_lo→Not-Validated`, else `Inconclusive`; estimator `Pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000, fit_intercept=True, lbfgs))` train-fit; **paired** baseline/candidate splits (same train/test rows per replication); error-class AP non-gating; seed `0x77C0DE`; R=200. Cut points hardcoded verbatim: `τ_lo = 0.02458901317356486`, `τ_hi = 0.06829080323934116`. Materialization inherited: `detector_per_example.csv` read + sha256-verified against the pinned anchor `24dac078…01afc643` and the recorded hash file (abort on mismatch) — no model re-run.

## Smoke results (synthetic candidates only, real B/y, non-canonical seed 0xBEEF)

- **Inherited-hash guard:** `detector_per_example.csv` sha256 matches the pinned anchor. ✓
- **Known-null** (random binary, prevalence-matched ~0.116, independent of `y`): `D_median = −0.00512` → **Not-Validated** (< τ_lo), as expected for junk. ✓
- **Known-meaningful** (binary 85%-correlated with `y`): `D_median = +0.28991` → **Validated** (> τ_hi), as expected. ✓

The verdict rule correctly classifies a clear null below the band and a clear meaningful above it; the machinery (paired standardized HDG, median scalar, band comparison) is sound. `truncated` was not loaded — the real first-verdict remains unknown until the locked run.

## Output-conformance (check F)

Every §7 pinned output is produced by `judge()` + `main()`: `D_median_HDG_AUC`, `verdict`, echoed `tau_lo`/`tau_hi`, `band_relation`; full per-replication AUC and error-class AP arrays under `hdg_distribution`; non-gating support (HDG mean/P5/P95, fractions above/below/in-band, AP median, n_examples, n_errors, truncated_prevalence); full meta (candidate, baseline, canonical+used seed, canonical+used R, model id+revision, dataset sha, inherited per-example sha, estimator descriptor, cut-point provenance tag, UTC). Nothing computed beyond the pinned set.

## Revision 2 (2026-06-08) — cold-pass-1 non-blockers folded (operator decision)

Cold pass 1 returned NO LOCK-BLOCKER; operator folded its three non-blockers (vs queue) because NB1 is a no-peeking footgun on the foundational ledger artifact. (1) docstring + `--seed`/`--reps` WARN rewritten — honest that the script always computes the real verdict and is not a smoke; the §8 smoke is a separate synthetic harness. (2) `verify_cut_points()` added — runtime assert that hardcoded `TAU_LO`/`TAU_HI` are byte-identical to `detector_calibration_results.json`, abort on drift (logic-tested: passes real JSON, aborts on drift). (3) §7 meta itemizes candidate/baseline. Verdict logic untouched → synthetic-smoke validation still holds. Count reset; re-route two fresh cold passes.

## Disposition

Script built, hash guard fires, verdict machinery validated on synthetic ground truth, check F clean, runtime cut-point guard added and logic-tested — **no implementation defect; no peeking at the candidate.** Manifest generator `build_manifest_detector_truncation.py` built (aborts on inherited per-example-hash, dataset-hash, or 3-way model-revision-identity mismatch). Ready for the warm pass + two cold passes. The numpy-mirror smoke is directional only; the locked sklearn run under `0x77C0DE` is the single, citable execution that produces OVP's first real ledger verdict.
