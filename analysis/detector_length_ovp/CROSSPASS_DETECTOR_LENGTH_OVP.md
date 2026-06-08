# Cross-Pass Record — DETECTOR_LENGTH_OVP (candidate study, OVP real candidate #2)

Tracks the two-pass review + lock progress for `PRE_REGISTRATION_DETECTOR_LENGTH_OVP.md`, per spec §7. Produces OVP's **second** real candidate verdict; both pass verdicts carried into the ledger row.

**Lock bar:** two independent passes return **no lock-blocker on byte-identical artifacts**; a blocker resets the count; non-blockers queue without folding; the fix-author cannot clear.

## Current status: **CLEARED TO LOCK** — 2 of 2 clean cold passes (NO LOCK-BLOCKER) on byte-identical artifacts. Remaining: operator §11 sign-off, then lock (`detector-length-ovp-lock`) + single run → OVP ledger verdict #2 (→ 2 of 3 toward operational). All non-blockers queued for v0.x, **not folded** — the locked bytes are exactly what both cold readers read.

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
