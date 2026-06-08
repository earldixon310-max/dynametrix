# Script-build findings — judge_length.py vs the DETECTOR_LENGTH_OVP pre-reg (candidate #2)

Build-and-smoke precondition. Built strictly to the pre-reg with the truncation-arc hardening lessons applied **from the start** (honest no-peeking docstring; `verify_cut_points()` runtime cut-point assert; the `1[text_length>512]==truncated` materialization cross-check). **No-peeking honored:** the smoke is a separate synthetic harness that loads only `B`, `y` and never materializes `text_length`.

## Build conformance
`judge_length.py` + `build_manifest_detector_length.py` compile clean. Pins verified: candidate `text_length` (full token count under the pinned tokenizer) / baseline confidence; `D = np.median` over all 200, no trimming; verdict open/open/closed; standardized train-fit pipeline (identical to the calibration); paired splits; error-class AP non-gating; seed `0x73C0DE`; R=200. Cut points hardcoded verbatim `τ_lo=0.02458901317356486`, `τ_hi=0.06829080323934116`, asserted at runtime + lock.

## Materialization (runs only at the locked execution)
`B,y,truncated` inherited from `../detector_truncation_ovp/detector_per_example.csv`, hash-verified vs anchor `24dac078…`. `text_length` materialized via the pinned tokenizer (`truncation=False`, token count) over the hash-verified RAID test set, aligned by `id`. **Integrity cross-check:** `1[text_length>512]` must equal the inherited `truncated` column elementwise or the run aborts (validates tokenizer determinism + the 512 window + row alignment in one shot). Requires `transformers` (tokenizer only; no model inference / no torch). The sandbox lacks transformers, so the cross-check fires at the operator's locked run; the logic is built to the pinned definition.

## Smoke results (synthetic candidates only; real B/y from the inherited CSV; non-canonical seed 0xBEEF)
- Manifest gates all PASS vs real files: inherited per-example hash, dataset hash, 3-way model-revision identity, cut-point identity (script == frozen calibration result).
- `verify_cut_points()` logic: hardcoded == calibration JSON (would abort on drift).
- **Known-null** (continuous `N(0,1)`): `D=+0.0065` → **Not-Validated** (< τ_lo). ✓
- **Known-meaningful** (`y + 0.5·N(0,1)`): `D=+0.331` → **Validated** (> τ_hi). ✓
- `text_length` was never materialized in the smoke (inherited CSV has no such column) — the real candidate stays sealed.

## Output-conformance (check F)
Every §7 pinned output produced by `judge()`+`main()` (incl. the `text_length` summary `min/median/max`, `length_per_example_sha256`); nothing beyond the pinned set.

## Disposition
Built, compiles, manifest gates verified, synthetic-smoke clean, check F clean, no peeking; hardening present from draft 1. Ready for warm pass + two cold passes (after operator local `py_compile`). The numpy-mirror smoke is directional; the locked sklearn run under `0x73C0DE` is the single citable execution → OVP's second real ledger verdict.
