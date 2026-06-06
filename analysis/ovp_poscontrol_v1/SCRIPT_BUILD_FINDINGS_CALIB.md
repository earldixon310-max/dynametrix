# Script-build findings — calibrate_cutpoints.py vs the calibration pre-reg

Per the standing discipline (`OVP_DESIGN_HISTORY.md`, §7 interpretation): the script is written strictly to the pre-reg; where building it hit an under-specified choice that affects results, it is logged here as a finding and returned to the pre-reg to be pinned, **not** silently encoded in code. Findings classified as the cold-reader rubric would: blocker (returns to pre-reg before lock) vs non-blocker (queued).

## Blocker-class (must be pinned in the pre-reg before lock — affects the produced numbers)

**F1 — Percentile interpolation method unspecified (affects `τ_lo`, `τ_hi`).**
§6 uses P95 (nulls) and P5 (meaningful). With `R_cal = 200`, these quantiles fall *between* order statistics, so the interpolation method (numpy `'linear'`/type-7 vs `'lower'`/`'higher'`/`'nearest'`) shifts `τ_lo` and `τ_hi` by small amounts that directly move the gated arms' pass rates. The method is a result-affecting pin and must be on the record.
→ Proposed pin: numpy default **`'linear'` (type-7)**. Script uses this. Returned to pre-reg §6/§12.

**F2 — Estimator completeness: `max_iter` value, feature standardization, intercept (affects determinism/values).**
§3 says "`max_iter` fixed" without a value, and does not state whether features are standardized or whether the estimator fits an intercept. These are determinism- and value-affecting.
→ Proposed pins: **`max_iter = 1000`** (ample for convergence; result insensitive once converged), **features NOT standardized** (raw `B`, `C`), **`fit_intercept = True`** (sklearn default; the data-generating intercept is 0, so the estimator will estimate ≈0). Script uses these. Returned to pre-reg §3/§12.

## Non-blocker (queued; implementation notes that do not change the marginal distributions)

**F3 — Per-replication seeding shared across constructions.** Implemented as one `SeedSequence` child per replication; within a replication the substrate `(s1,s2,y,B)` is drawn once and shared across all constructions, then each construction's `C` is drawn in a fixed construction order (nulls → meaningful grid → partial grid). Faithful to "one child per replication." Pairing constructions on shared substrate does **not** change any construction's marginal HDG distribution (what the percentiles use), so it does not affect the cut points. Noted for the record; no pre-reg change required.

**F4 — `γ` tiebreak for "median closest to midpoint."** Tiebreak unspecified; script uses **smallest `γ`** on an exact tie. Probability of an exact tie in continuous HDG medians is negligible. Queued, not blocking.

**F5 — Split RNG derivation.** The stratified 50/50 split needs a random_state; the script draws it from the per-replication rng (so it is deterministic under the master seed and consumes the rng in fixed order). Consistent with the pinned seeding; noted.

## Disposition

F1 and F2 are returned to the calibration pre-reg now (before the second independent pass), because pinning them changes the pre-reg bytes — and per the §7 two-pass bar, the second pass must run on the final bytes. Folding them now (rather than after) is correct: they are not "non-blocker notes that queue," they are gaps a cold reader could legitimately have called, so they belong in the artifact before its two clean passes. F3–F5 queue as documented implementation notes.
