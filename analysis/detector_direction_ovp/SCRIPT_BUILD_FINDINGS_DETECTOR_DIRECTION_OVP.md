# Script-build findings — judge_direction.py vs the DETECTOR_DIRECTION_OVP pre-reg (candidate #3)

Build-and-smoke precondition with the full hardening baked in from draft 1 (honest no-peeking docstring; `verify_cut_points()`; hash-guarded inheritance). **No-peeking, heightened:** the directional marginal (accuracy-by-predicted-class) is close to the HDG, so it is **not computed pre-lock**; the smoke is a separate synthetic harness loading only `B`, `y` (never `predicted_prob_ai`/`pred`).

## Build conformance
`judge_direction.py` + `build_manifest_detector_direction.py` compile clean. Pins verified: candidate `predicted_prob_ai` (raw directional probability) / baseline confidence (folded); `D = np.median` over all 200, no trimming; verdict open/open/closed; standardized train-fit pipeline (identical to the calibration); paired splits; error-class AP non-gating; seed `0xDEC0DE`; R=200. Cut points hardcoded verbatim `τ_lo=0.02458901317356486`, `τ_hi=0.06829080323934116`, asserted at runtime + lock. **No materialization** — `B`, `y`, `predicted_prob_ai`, `pred` are all read from the inherited `detector_per_example.csv` (hash-verified vs anchor `24dac078…`; confirmed the file contains the `predicted_prob_ai` and `pred` columns). The simplest candidate study in the arc.

## Smoke results (synthetic candidates only; real B/y; non-canonical seed 0xBEEF)
- Manifest gates all PASS vs real files: inherited per-example hash, dataset hash, 3-way model-revision identity, cut-point identity (script == frozen calibration result).
- `verify_cut_points()` logic: hardcoded == calibration JSON (aborts on drift).
- **Known-null** (`N(0,1)`): `D=+0.0064` → **Not-Validated** (< τ_lo). ✓
- **Known-meaningful** (`y + 0.5·N(0,1)`): `D=+0.327` → **Validated** (> τ_hi). ✓
- `predicted_prob_ai`/`pred` were never loaded in the smoke — the real verdict stays sealed, and the directional marginal was not computed.

## Output-conformance (check F)
Every §7 pinned output produced by `judge()`+`main()` — incl. the non-gating **per-predicted-class diagnostics** (`accuracy_given_pred1/pred0`, `n_pred1/pred0`) for the §9 slope-vs-intercept interpretation; nothing beyond the pinned set.

## Disposition
Built, compiles, manifest gates verified, synthetic-smoke clean, check F clean, heightened no-peeking honored. Ready for warm pass + two cold passes (after operator local `py_compile`). The locked sklearn run under `0xDEC0DE` is the single citable execution → OVP real ledger verdict #3 → **operational rung**.
