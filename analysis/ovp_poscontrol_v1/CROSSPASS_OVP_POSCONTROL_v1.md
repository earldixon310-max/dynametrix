# Cross-Pass Record — OVP_POSCONTROL_v1 (positive control)

Tracks the two-pass review and lock progress for the **positive-control** pre-registration (`PRE_REGISTRATION_OVP_POSCONTROL_v1.md`), per spec §7 and the §7 two-pass interpretation in `OVP_DESIGN_HISTORY.md`. The pre-reg deliberately does **not** narrate its own review-progress (that text goes stale and was itself the finding in two consecutive passes); this file is the single home for the mutable status.

**Lock bar:** two independent passes return **no lock-blocker on byte-identical artifacts**; a blocker resets the count to zero; non-blockers queue without folding; the fix-author cannot clear.

## Current status: COMPLETE. Locked, run (**PASS**), and the result cleared **two independent cold passes** — the citation gate is MET. **OVP v0.1 is self-validated** (spec §6, rung 1), citably, on the public record.

## Pass history

- **Pass A (external cold):** found one **blocker** — §10 step 5 pre-declared the cold pass "— now complete —", contradicting the Status line ("awaits its two independent cold passes"). Design otherwise fully conformant. → Fixed; count reset.
- **Pass B (external cold, on the post-fix bytes):** **no blocker**; full conformance confirmed (verdict rule, provenance/bootstrap, strict band, baseline rule, per-arm bars, ladder claim, internal arithmetic). One **non-blocker**: §12(b) stale ("not now… structurally TBD") now that the cut points are frozen — same *class* as Pass A's blocker (self-referential review-status going stale).

## Root-cause fix (applied after Pass B)

Two consecutive passes flagged the same class — the document narrating its own review-progress, which goes stale as the process advances, and which different readers classify as blocker vs non-blocker. Rather than queue-and-risk-a-third-reset, the **mutable process-status was removed from the pre-reg** (Status line, §10 steps, §12), mirroring the spec's own discipline (lock status lives in the notice, not the body). The pre-reg now describes only the study; this file holds the status. Bytes changed → **count reset to zero**; two fresh clean passes are required on the de-narrated pre-reg.

## De-narrated cycle (the bytes that will lock)

- **Pass 1 (external cold, on the de-narrated bytes):** **no lock-blocker.** Full conformance confirmed — lock authority, cut-point provenance/bootstrap, verdict rule + strict band, AUC higher-is-better orientation, arms/bars/baseline, and the internal arithmetic (Arm 1 margin +0.0104; τ_hi clears τ_lo+δ; Arm 4 near-zero null). Independence: fresh reader, no design-conversation context, given pre-reg + spec body + lock notice only; the fix-author did not serve. One non-blocker (below).
- **Pass 2 (external cold, byte-identical to pass 1):** **no lock-blocker.** Independently re-confirmed full conformance and the internal arithmetic, and **independently raised the same §11 non-blocker** — corroboration, no verdict divergence. Independence: fresh reader, no design-conversation context, given pre-reg + spec body + lock notice only; the fix-author did not serve.

**Two-pass result: CLEARED TO LOCK.** Two independent passes returned no lock-blocker on byte-identical artifacts; the §11 non-blocker is corroborated by both and queued for the v0.x revision (not folded — held the byte-identity bar). Remaining before lock: operator §13 sign-off, then the single atomic lock commit + signed tag (`ovp-poscontrol-v1-lock`) + single run.

## Queued non-blockers (fold at the first post-lock revision; NOT before lock — holding the byte-identity bar)

- **§11 "the rungs are unnumbered" is inaccurate.** §11 reads "spec §6, rung 1 — the rungs are unnumbered," but spec §6 numbers the ladder (1. Self-validated / 2. Operational / 3. Community-validated). Substance unaffected (self-validated is the first rung either way; the §-preamble cedes "the spec governs"). It was introduced while fixing an earlier reviewer's "§6.1" note — that reviewer had wrongly asserted the rungs were unnumbered. v0.x fix: "(spec §6, rung 1 — *Self-validated*)". **Deliberately not folded now**: folding would change the bytes and reset the two-pass count, so it is queued per the bar.

## Result cross-pass (spec §7 / §10 step 8) — gates CITATION of the PASS

The positive control ran (PASS) and the result is recorded at tag `ovp-poscontrol-v1-result`. Per spec §7, the **result document** earns two independent passes before the PASS may be *cited* as establishing the self-validated rung. (The result document is **not** edited between passes — byte-identity preserved.)

- **Result pass 1 (external cold):** **no defect.** All three result-review checks passed: (1) every figure in `RESULT_OVP_POSCONTROL_v1.md` reconciles to `poscontrol_results.json` — seed `0xFACADE`, R=100, cut points, per-arm tallies (95/0/5, 0/100/0, 4/5/91, 0/93/7), setup controls all true, baseline AUC median 0.6444; (2) reports exactly what pre-reg §7/§8 require (arms 1/2/4 gated, Arm 3 full distribution non-gated, §8.2(a) correctly inherited not re-run); (3) no overclaim (confined to rung 1; disclaims operational/community-validated). The reviewer's "blocks citation: yes" refers **only** to the two-pass gate being incomplete (this being pass 1), not to any document defect. Non-blocking observations: the locked script's VERDICT string reads "sec 6.1" vs the result's "§6, rung 1" (both denote self-validated); JSON `generated` timestamp not cited in the result. Independence: fresh reader, no design context, given result + raw JSON + pre-reg.
- **Result pass 2 (external cold, byte-identical to pass 1): no defect.** Independently reconciled every figure to `poscontrol_results.json`, confirmed reporting per pre-reg §6/§7/§8 (gates arms 1/2/4, Arm 3 full distribution non-gated, §8.2(a) inherited), and confirmed no overclaim (rung 1 only). Same self-referential "citing blocked — gate not yet complete" note as pass 1, now resolved: this clean pass *completes* the gate. Independence: fresh reader, no design context, given result + raw JSON + pre-reg.

**Both result passes returned no defect on byte-identical artifacts.** The spec §7 / §10-step-8 citation gate is **MET**. The PASS is now established and citable: **OVP v0.1 is self-validated.** The "Citation gate" conditional in `RESULT_OVP_POSCONTROL_v1.md` ("may not be cited until those [two passes] clear") is hereby satisfied; this record is the authoritative evidence that the two independent clean passes occurred.

## Remaining gates

1. Two fresh independent cold passes on the de-narrated pre-reg, ≥1 cold, fix-author cannot clear, recorded here with each reader's sourced independence.
2. Operator sign-off on the §13 discretionary pins.
3. Then the positive-control lock (`ovp-poscontrol-v1-lock`): pre-reg + `validate_ovp.py` + materialization manifest, single atomic commit + signed tag; then the single run.
