# Cross-Pass Record — DETECTOR_TRUNCATION_OVP (candidate study, lock 2)

Tracks the two-pass review + lock progress for `PRE_REGISTRATION_DETECTOR_TRUNCATION_OVP.md`, per spec §7. This study produces **OVP's first real candidate-observable verdict**; both pass verdicts are carried into the ledger row (spec §5/§7).

**Lock bar:** two independent passes return **no lock-blocker on byte-identical artifacts**; a blocker resets the count; non-blockers queue without folding; the fix-author cannot clear.

## Current status: **CLEARED TO LOCK** — 2 of 2 clean cold passes (NO LOCK-BLOCKER) on byte-identical revision-2 artifacts. Remaining: operator §11 sign-off, then lock (`detector-truncation-ovp-lock`) + single run → first OVP ledger verdict. All non-blockers queued for v0.x, **not folded** — the locked bytes are exactly what both cold readers read.

## Revision-2 cold pass 2 (external, genuine fresh reader; verified mechanical claims in sandbox): NO LOCK-BLOCKER — BAR MET
Independent cold reader, no design context / no cross-pass record. All A–I conform; both weighted checks independently affirmed — **(D)** `D = np.median` over the full 200, verdict reads `D` alone; **(E)** cut points verbatim vs the calibration JSON (τ_lo = P95 `null_noise`, τ_hi = P5 `meaningful:1.5`), external provenance (seed `0xD37EC7` ≠ this study's `0x77C0DE`), recognized as the §1 bootstrap route; `verify_cut_points()` aborts on drift. Paired splits, hash-verified inheritance, output conformance, scope all confirmed. **VERDICT: NO LOCK-BLOCKER.**
**Cross-pass corroboration:** both cold readers independently verified the cut-point identity, the verdict-partition exhaustiveness, and the even-N type-7 median form *in sandbox*, and both affirmed the folded `verify_cut_points` guard and the honest no-peeking framing. Independent agreement on the load-bearing claims = the §7 signal working.
Two pass-2 non-blockers (queued un-folded): (a) `n_examples`/`n_errors`/`truncated_prevalence` placed under `support_nongating` rather than §7's distinct bullet — all present + non-gating, cosmetic location only; (b) `verify_cut_points` uses exact float equality — correct (same IEEE-754 double from the same literal), defensible as a strict drift guard; document as intentional.

## Revision-2 cold pass 1 (external, genuine fresh reader; verified mechanical claims in sandbox): NO LOCK-BLOCKER

## Revision-2 cold pass 1 (external, genuine fresh reader; verified mechanical claims in sandbox): NO LOCK-BLOCKER
Independent cold reader; confirmed cut-point identity (`==` digit-for-digit vs the calibration JSON), verdict-partition mutual-exclusivity/exhaustiveness with both boundaries in the closed Inconclusive band, and the even-N type-7 median form, in a sandbox. All A–I conform, including the folded items: **(G)** the `--seed/--reps` flags self-document they are not a no-peeking smoke; **(E)** `verify_cut_points()` re-asserts the literals against the calibration JSON each run and aborts on drift, recognized as the §1 bootstrap path (not prohibited self-sourcing). **VERDICT: NO LOCK-BLOCKER.**
Three non-blockers (queued un-folded — ordinary editorial, not integrity-critical):
1. `load_inherited()` secondary `..._sha256.txt` cross-check is `os.path.exists`-gated (soft-skip if absent) — harmless: the **unconditional hardcoded anchor** enforces integrity regardless. Tighten to require-present in a future revision.
2. A non-canonical run still writes the default `detector_truncation_results.json`, which could overwrite the working-copy result — cannot corrupt the ledger (canonical output is committed + signed-tagged, immutable in git); refuse-to-write-canonical-name under non-canonical params is optional defense-in-depth.
3. `band_relation`'s three booleans are redundant with the verdict string. Editorial.

## Revision 2 — NB1/NB2/NB3 folded (2026-06-08); bytes changed, count reset
Operator chose **fold** over the codified queue-default, on the basis that NB1 is not a clarity nit but a *documentation defect that invites a discipline breach on the foundational artifact of the OVP ledger* (a misleading "smoke-only" docstring on a script that always computes the real verdict). Fixes:
- **NB1 (no-peeking footgun):** `judge_truncation.py` docstring + `--seed`/`--reps` WARN messages rewritten to state plainly that these flags are determinism plumbing, that the script **always** computes `truncated`'s real HDG (NOT a no-peeking smoke), and that the §8 smoke is a **separate synthetic harness**. Pre-reg §8.1 reworded to match (the smoke is a separate harness loading only B,y; running `judge_truncation.py` is never the smoke).
- **NB2 (cut-point runtime assert):** added `verify_cut_points()` — asserts the hardcoded `TAU_LO`/`TAU_HI` are byte-identical to `detector_calibration_results.json` (`detector-ovp-calib-result`) at the start of every run, aborting on drift. Pinned in pre-reg §5/§6/§8.3/§11.4. Logic-tested: passes on the real JSON, aborts on a drifted value.
- **NB3:** pre-reg §7 meta list now itemizes `candidate`/`baseline` (already in the script's meta).
**Validation:** verdict logic (`judge`/`hdg_paired`) untouched → the synthetic-only smoke (known-null→Not-Validated, known-meaningful→Validated) still holds; `verify_cut_points` logic-tested separately. Script is complete on disk through `main()` (file-tool authoritative; bash mount serves a truncated copy — operator local `py_compile` is the definitive check). Per the lock bar, the byte change resets the cold-pass count to zero.

## Cold pass 1 (external, genuine fresh reader) — SUPERSEDED by revision 2 (operator folded NB1): NO LOCK-BLOCKER

## Cold pass 1 (external, genuine fresh reader): NO LOCK-BLOCKER
Verified code against pinned forms and cut points byte-for-byte. All A–I conform: measure form; baseline rule incl. the now-present Ancestry Statement; verdict rule (open/open/closed); **(D)** `D = np.median(d_auc)` over the full 200, no trimming, verdict reads `D` only, distribution persisted so the median is re-derivable; **(E)** cut points byte-match `detector_calibration_results.json` (τ_lo = `p95_null_noise`, τ_hi = `meaningful_P5_AUC["1.5"]`, gap 0.0437 ≥ δ), and the calibration's redundant-null being exactly 0 across 200 confirms the inherited band was built on the **same paired-split footing**; **(F)** paired splits + train-fit standardization; **(G)** hash-verified inheritance, abort on mismatch; **(H)** output conformance; **(I)** scope. **VERDICT: NO LOCK-BLOCKER.**
Three non-blockers (decision pending whether to fold-now or queue):
- **NB1 (no-peeking footgun)** — docstring calls `--seed`/`--reps` "smoke-only," but the script has no synthetic mode: any run computes `truncated`'s real HDG, so the misleading docstring invites accidental pre-lock peeking. Locked run unaffected (canonical, single execution); the genuine smoke was a separate synthetic harness. Fix: docstring states these are determinism plumbing, the script always computes the real candidate HDG, and the §8 smoke is a separate synthetic harness.
- **NB2 (cut-point runtime assert)** — hardcoded τ are verbatim-correct (verified) but not asserted against the calibration JSON at load. Optional hardening: read+assert at runtime (defense-in-depth vs transcription drift, complementing the manifest gate).
- **NB3** — `meta.candidate`/`meta.baseline` labels not itemized in §7's meta list; harmless.

## Pre-cold-pass steps (complete)
- **Build-and-smoke** (`judge_truncation.py`, `SCRIPT_BUILD_FINDINGS_DETECTOR_TRUNCATION_OVP.md`): built strictly to the pre-reg; compiles. **No peeking — the smoke did NOT compute `truncated`'s HDG;** it validated the verdict machinery on synthetic candidates only (loaded B, y; ignored the `truncated` column): known-null → D=−0.005 → **Not-Validated** (< τ_lo); known-meaningful → D=+0.290 → **Validated** (> τ_hi). Inherited-hash guard fires. The real verdict stays sealed until the locked run.
- **Output-conformance (check F):** every §7 pinned output produced by `judge()`+`main()`; nothing beyond the pinned set.
- **Manifest generator** (`build_manifest_detector_truncation.py`): aborts the lock on inherited per-example-hash, dataset-hash, 3-way model-revision-identity, **or cut-point-identity (script vs frozen JSON)** mismatch. All four gates verified PASS against the real files (per-example `24dac078…`, dataset `a29f8f2c…`, revision `d2b342c6…`, cut points `0.02458901317356486` / `0.06829080323934116`).
- **Operator local `py_compile`** of `judge_truncation.py`: **PASS (2026-06-08)**.

## Warm conformance audit (operator, full design context — NOT a §7 cold pass): ONE FINDING, FIXED
Adversarial A–I walk; all mechanical checks conform — measure form (§4 = spec §1), verdict rule (open/open/closed partition matching spec §3/§6), **(D)** `D = median(HDG_AUC)` over all 200, no trimming, verdict reads `D` only; **(E)** cut points verbatim across pre-reg/script/`detector_calibration_results.json`, external provenance `detector-ovp-calib-result`; **(F)** paired splits + train-fit standardization (no leakage); **(G)** no-peeking honored (smoke synthetic-only); **(H)** output conformance; **(I)** scope.
**Finding (borderline → fixed before cold passes):** spec §2 criterion 5 mandates an explicit, labeled **Ancestry Statement** ("baseline selection is not valid without this statement"). The pre-reg had the substance distributed across §1/§3 but no labeled statement, and §3's "all five criteria" walk had **mislabeled** criterion 5 (it restated criterion 2's no-more-complex clause). A strict cold reader could legitimately flag the missing Ancestry Statement as a blocker. **Fixed (warm-pass, cold-clock not started → free fold; pre-reg-only, script unaffected, no re-smoke):** §3 now carries a labeled Ancestry Statement (`truncated` extends `confidence`: an input-structural property the model may mishandle extends its internal certainty signal) and the five-criteria walk is corrected to match the spec verbatim (criterion 5 = Ancestry Statement).
**Non-blocker (no action — confirmed conformant):** the verdict regions are open-above-τ_hi / open-below-τ_lo / closed-`[τ_lo,τ_hi]`; a `D` landing exactly on a cut point is Inconclusive — matches spec §3's stated partition exactly.

## Remaining gates (revision-2 bytes)
- ~~Operator local `py_compile`~~ **PASS.**
- ~~Two cold passes~~ **DONE: 2 of 2 clean on byte-identical revision-2 artifacts — BAR MET.** All non-blockers queued for v0.x (not folded).
- **Operator §11 sign-off** on the 7 discretionary pins — the one open gate before lock.
- Lock: run `build_manifest_detector_truncation.py` (4 gates) → atomic commit of pre-reg + `judge_truncation.py` + `materialization_manifest_detector_truncation.json` → signed tag `detector-truncation-ovp-lock` → **single run** of `judge_truncation.py` (no flags) → commit outputs + signed tag `detector-truncation-ovp-result` → write `RESULT_DETECTOR_TRUNCATION_OVP.md` + route its result cross-pass → first OVP ledger row.

### Combined v0.x queue (both cold passes; un-folded)
1. `load_inherited()` `..._sha256.txt` cross-check `os.path.exists`-gated (anchor still unconditional). 2. Non-canonical run writes default results filename (cannot corrupt the tagged ledger record). 3. `band_relation` redundant with verdict. 4. §7 nesting: `n_examples`/`n_errors`/`truncated_prevalence` under `support_nongating`. 5. `verify_cut_points` exact-float-equality — document as intentional.

---
## (historical) earlier-revision gates
- **Warm pass** against the pinned pre-commitments (D=median form; inherited cut points verbatim; paired splits; no-peeking smoke discipline; verdict rule), then **two independent cold passes** (≥1 cold, fix-author cannot clear) on byte-identical artifacts.
- Operator §11 sign-off on the 7 discretionary pins.
- Lock (`detector-truncation-ovp-lock`: pre-reg + `judge_truncation.py` + `materialization_manifest_detector_truncation.json`, atomic commit + signed tag) → **single run** → verdict → `RESULT_DETECTOR_TRUNCATION_OVP.md` + its result cross-pass (citation gate) → **first OVP ledger row** (spec §5).
