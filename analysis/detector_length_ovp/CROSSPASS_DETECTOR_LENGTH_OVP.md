# Cross-Pass Record — DETECTOR_LENGTH_OVP (candidate study, OVP real candidate #2)

Tracks the two-pass review + lock progress for `PRE_REGISTRATION_DETECTOR_LENGTH_OVP.md`, per spec §7. Produces OVP's **second** real candidate verdict; both pass verdicts carried into the ledger row.

**Lock bar:** two independent passes return **no lock-blocker on byte-identical artifacts**; a blocker resets the count; non-blockers queue without folding; the fix-author cannot clear.

## Current status: **EXECUTED — verdict NOT-VALIDATED.** Locked at `detector-length-ovp-lock` (2/2 clean cold passes); single run under seed `0x73C0DE`; outputs at `detector-length-ovp-result`. **`D = −0.011778 < τ_lo` → Not-Validated** (199/200 reps below τ_lo; cross-check `1[text_length>512]==truncated` passed). **OVP real verdict #2 → 2 of 3 toward operational** (`OVP_DESIGN_HISTORY.md`). Outcome doc: `RESULT_DETECTOR_LENGTH_OVP.md`. **CITATION GATE MET — 2 of 2 result cold passes clean; verdict #2 citable.** v0.x non-blockers remain queued.

## Result-review (citation gate; two independent cold passes on the OUTCOME DOCUMENT)
- **Result cold pass 1: NO BLOCKER.** Fresh reader recomputed every gating figure exactly over the frozen 200-element arrays (D=−0.011778 median, mean −0.013545, P5/P95, min/max, 199/200 below τ_lo, AP median −0.003193, text_length 38/313/3510), independently reproduced the **integrity guard** (`1[text_length>512]==truncated`, 0 mismatches / 2000 rows) and the **marginal** (r=0.0903; quartile hump 0.634/0.740/0.701/0.637). Verdict derivation mechanical, cut-points verbatim+external, median≈mean, estimator-conditional caveat + mechanism-agnostic framing correctly stated. Two non-blockers, **queued (not folded):** (1) Q2 quartile accuracy 0.741 vs 0.740 — sub-0.001 tie-handling at the text_length=313 boundary, illustrative/non-gating; post-citation tidy: pin binning or round to 2dp. (2) verdict-#1 D=+0.029 and the length-file sha aren't in the review packet — give pass 2 the truncation results JSON + the real `detector_length_per_example.csv` to close both.
- **Result cold pass 2: NO BLOCKER — CITATION GATE MET.** Second independent fresh reader recomputed D to 15 digits, mean/P5/P95/min/max, the band fractions (199/200 below τ_lo), AP median, text_length range, r=0.090275, quartile hump (0.634/0.742/0.700/0.636), and re-ran the cross-check (0 mismatches) — all faithful. Same two cosmetic notes as pass 1 (both "no action required"): the quartile tie-handling (±0.001, convention-dependent), and the out-of-scope verdict-#1 cross-references (covered by #1's own cross-pass). **`RESULT_DETECTOR_LENGTH_OVP.md` is citable.**
- **v0.x cosmetic queue (post-citation, batched — NOT applied to the cleared artifact):** pin the quartile binning convention (or round to 2dp) so the 0.741/0.740/0.742 tie ambiguity disappears. (Both result passes independently raised it; both waved it through.)

## Cold pass 2 (external, genuine fresh reader): NO LOCK-BLOCKER — BAR MET
Independent fresh reader confirmed every weighted guarantee in the locked artifacts: continuous-parent `text_length` definition; hash-verified inherited B/y/truncated (not re-derived); the abort-on-mismatch `1[text_length>512]==truncated` cross-check (validates tokenizer determinism + 512 window + id alignment); `D=median` over 200 no trimming; verdict open/open/closed vs the verbatim inherited band with `verify_cut_points()` called before materialization; paired leakage-free standardized splits; estimator/seed/R identity; no-peeking; Ancestry Statement; output/pin/scope conformance. **VERDICT: NO LOCK-BLOCKER. "I would clear it for lock."**
Two non-blockers (queued un-folded): (a) §2/§7 use shorthand `B, y` for the columns the code writes as `B_confidence, y_correct` (internally consistent — the inherited CSV uses those names; no value/hash/verdict effect); (b) scope note — the manifest generator + synthetic smoke harness were not in the reviewer's packet (their lock-time gates duplicate in-script guards the reviewer verified directly).

## Cold pass 1 (external, genuine fresh reader): NO LOCK-BLOCKER
Reviewed pre-reg + `judge_length.py` + spec + lock notice + `detector_calibration_results.json` + `detector_per_example.csv`. Confirmed all weighted deltas: **text_length = full untruncated token count** (the continuous parent, `truncated = 1[text_length>512]`, not a proxy); the **materialization cross-check** is hard-aborting and B/y/truncated are inherited byte-identically (independently corroborated: the calibration result's `meta.detector_per_example_sha256` == the script anchor `24dac078…`, so B/y are provably the calibrated bytes); D=median over 200 no trimming; verdict open/open/closed vs the verbatim inherited band with `verify_cut_points` runtime assert; paired standardized splits no leakage; no-peeking honored; Ancestry Statement present; estimator/seed/R/output-conformance/scope all conform. **VERDICT: NO LOCK-BLOCKER.**
Three non-blockers (queued un-folded — editorial, none integrity-critical):
1. `str(t)` cast vs the pre-reg's literal `tokenizer(text,…)` — **actually consistency-correct** (the calibration materialized `truncated` from `df["text"].astype(str)`), so it makes text_length match the calibration's treatment; one-line §2 note.
2. `add_special_tokens=True` default not explicitly pinned — same default the calibration used, and the cross-check abort enforces any mismatch; pin explicitly in a future revision.
3. Error-class AP never enters the verdict — add a one-line note in the result document.

## Pre-cold-pass steps (complete)
- **Build-and-smoke** (`judge_length.py`, `SCRIPT_BUILD_FINDINGS_DETECTOR_LENGTH_OVP.md`): hardening present from draft 1 (honest no-peeking docstring; `verify_cut_points`; `1[text_length>512]==truncated` cross-check). **No peeking** — smoke synthetic-only (B,y), `text_length` never materialized: known-null → Not-Validated, known-meaningful → Validated. ✓
- **Output-conformance (check F):** every §7 output produced; nothing unpinned.
- **Manifest generator** (`build_manifest_detector_length.py`): aborts on inherited per-example-hash, dataset-hash, 3-way model-revision-identity, or cut-point-identity mismatch — all verified PASS vs the real files (inherited `24dac078…`, dataset `a29f8f2c…`, revision `d2b342c6…`, cut points byte-match the frozen calibration).
- **Operator local `py_compile`** of `judge_length.py`: pending (definitive).

## Remaining gates
- ~~Operator local `py_compile`~~ **PASS.**
- ~~Two cold passes~~ **DONE: 2 of 2 clean on byte-identical artifacts — BAR MET.** All non-blockers queued for v0.x.
- **Operator §11 sign-off** on the 7 discretionary pins — the one open gate before lock.
- Lock: `build_manifest_detector_length.py` (4 gates) → atomic commit of pre-reg + `judge_length.py` + `materialization_manifest_detector_length.json` → signed tag `detector-length-ovp-lock` → **single run** of `judge_length.py` (materializes text_length + cross-check + judge) → commit outputs + `detector-length-ovp-result` → `RESULT_DETECTOR_LENGTH_OVP.md` + result cross-pass → **ledger verdict #2**.

### Combined v0.x queue (both cold passes; un-folded)
1. `str(t)` cast vs literal `tokenizer(text,…)` — consistency-correct (matches calibration's `.astype(str)`); §2 note. 2. `add_special_tokens=True` default not explicitly pinned (cross-check abort enforces it). 3. AP-never-enters-verdict note for the result doc. 4. §2/§7 `B,y` shorthand vs code `B_confidence,y_correct`. 5. (process) manifest + smoke not in cold-reader packets — consider including next time.
- Lock (`detector-length-ovp-lock`: pre-reg + `judge_length.py` + manifest, atomic commit + signed tag) → **single run** (materializes text_length via tokenizer, cross-checks vs truncated, judges) → verdict → `RESULT_DETECTOR_LENGTH_OVP.md` + its result cross-pass → **second OVP ledger row** (→ 2 of 3 toward operational).

## Note
The verdict is sealed: `text_length`'s HDG has not been computed pre-lock (build-and-smoke used a separate synthetic harness; the materialization that creates `text_length` runs only at the locked execution). Read against verdict #1 (`truncated` Inconclusive), this study characterizes how far the detector's confidence-as-sufficient-statistic property extends across the full length range.
