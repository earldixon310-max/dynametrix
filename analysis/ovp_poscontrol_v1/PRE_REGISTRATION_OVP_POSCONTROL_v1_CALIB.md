# Pre-Registration — OVP_POSCONTROL_v1 Cut-Point Calibration Study

**Study type:** Pre-lock cut-point calibration study for OVP_POSCONTROL_v1 (the §1 "bootstrap path for the first study under a new measure").
**Governing spec:** OVP v0.1, locked at signed tag **`ovp-v0.1-lock`** (verified-good SSH signature). **Note on the lock (important for verification):** OVP v0.1 was locked **tag-only / byte-exact** — by a deliberate, recorded decision the spec *body* retains its "working draft — not locked" status line so that the locked artifact is byte-identical to the version its own cold reader cleared. The authoritative lock state is carried by the **signed tag**, `OVP_v0.1_LOCK_NOTICE.md`, and `OVP_DESIGN_HISTORY.md` — **not** by the body's status line. A reader verifying this citation should check the tag (`git tag -v ovp-v0.1-lock`) and the lock notice, not the body text, which is stale by design. This study conforms to the spec at that tag without modification; the spec governs.
**Relationship to the positive control (one-directional):** This study runs and locks **first**, under its **own seed `0xCA11B`** and **own lock tag `ovp-poscontrol-v1-calib-lock`**. It is **self-contained** — every value needed to run and verify it is stated in this document or its locked code artifact (`calibrate_cutpoints.py`, which implements the prose-specified per-replication seeding of §3) — and it is the **authority on the shared HDG instantiation and the cut points**: it *sets* the ruler. The positive control (a separate, later study) **inherits** this study's instantiation (§3) and frozen outputs (`τ_lo`, `τ_hi`, Arm 1 `σ_C`, Arm 3 `σ₃`, §8). Nothing here depends on the positive control, so the dependency is **acyclic** (calibration → positive control only). This study's own lock/run ordering is in §9; it does not rely on any external document to run or be verified.
**Status:** DRAFT for review. **Not locked.** No code is run and no value is fixed until this pre-registration passes its own cold pass and is locked.

---

## 1. Objective

Produce externally-sourced decision cut points (`τ_lo`, `τ_hi`) on the HDG scale, and the two band-relative arm parameters (Arm 1 `σ_C`, Arm 3 `σ₃`), **before** the positive control runs and **without** using the positive control's own arm data. Per spec §1, cut points may not be set from the study they govern (in particular never from the positive control's noise arm); the admissible route for a brand-new measure with an empty ledger is exactly this — a separate calibration study measuring what HDG known-null vs known-meaningful constructions produce.

This study sets the ruler. It does not validate OVP and does not judge any candidate.

---

## 2. Why this is the bootstrap, not circularity (conformance note)

The calibration constructions below are the same *forms* as the positive control's arms (null-redundant ↔ Arm 2, null-noise ↔ Arm 4, meaningful ↔ Arm 1, partial ↔ Arm 3). They are **separate runs under a separate seed** (`0xCA11B`, vs the positive control's `0xFACADE`), on independent data draws. Spec §1 sanctions precisely this ("measuring what HDG a known-meaningful vs a known-null construction produces") and forbids only using the positive control's **own arm data — the same run** — to set the bar that run must then clear. Separate seed + separate run = not the same data, so `τ_lo` being set from null-construction siblings of Arms 2/4 is the sanctioned bootstrap, not the prohibited self-vindication.

---

## 3. HDG instantiation (defined here; the positive control inherits it)

This study **sets** the HDG scale on which the cut points live, so it pins the instantiation directly and authoritatively here. The positive control inherits these identical values (it does not redefine them); the dependency runs calibration → positive control only. Pinned:

- Discrimination metric: ROC AUC on held-out test (higher-is-better).
- Estimator: L2 logistic regression (`solver='lbfgs'`, `C=1.0`, `max_iter=1000`, `fit_intercept=True`); features are **not** standardized (raw `B`, `C`). (`max_iter=1000` is ample for convergence on this 1–2 feature problem, so the result is insensitive to it once converged; `fit_intercept=True` is the sklearn default and estimates ≈0 since the data-generating intercept is 0.)
- Split: stratified 50/50 train/test per replication.
- `D = AUC_test(logistic[B,C]) − AUC_test(logistic[B])`.
- `N = 4000` per replication; **`R_cal = 200`** replications per construction (more than the positive control's 100, for stable percentile estimates).
- Master seed `0xCA11B`; per-replication seeds derived from it via NumPy `SeedSequence` (one spawned child per replication, in index order), as implemented in the locked `calibrate_cutpoints.py`. This fixes the full seeding at lock (spec §1).

---

## 4. Substrate and generative model (identical form to the positive control §3)

Per replication: `s1, s2 ~ Normal(0,1)` independent; `y ~ Bernoulli(sigmoid(β1·s1 + β2·s2))`; baseline `B = s1 + Normal(0, σ_B²)`. Pinned constants: `β1 = 1.0`, `β2 = 1.0`, `σ_B = 1.0` (`β2` = scalar weight on `s2`, not a product with `y`).

---

## 5. Calibration constructions (own seed `0xCA11B`)

- **Null-redundant:** `C = 2·B − 0.5` (deterministic affine of `B`). HDG centers at/just below 0.
- **Null-noise:** `C = Normal(0,1)`, independent of everything. HDG centers cleanly at 0.
- **Meaningful sweep:** `C = s2 + Normal(0, σ_C²)`, `σ_C` over the pinned grid **{0.25, 0.5, 1.0, 1.5, 2.0, 3.0}** (smaller `σ_C` = cleaner view of `s2` = stronger candidate). Maps HDG vs. candidate strength.
- **Partial sweep (Arm-3 form):** `C = B + s2 + Normal(0, σ₃²)` — a redundant copy of `B` plus a **noise-attenuated** view of `s2` — swept over the noise level `σ₃` on the pinned grid **{1.5, 2.0, 3.0, 4.0, 5.0, 6.0}**. The increment's strength is controlled by *noise*, not scale: a scale parameter on a clean `s2` would **not** control HDG, because the linear estimator is scale-invariant (it recovers `C − B = scale·s2` and absorbs the scale into the coefficient), so only noise actually attenuates the recoverable signal. As `σ₃ → 0` the model recovers `s2` cleanly (HDG → the Arm-1 ceiling); as `σ₃ → ∞` the increment is buried and `C → B + noise` (HDG → 0); intermediate `σ₃` gives a monotone gradient that can target the band. The small-increment HDG is thus measured directly in the Arm-3 functional form, not extrapolated.

Each construction / grid point is run for `R_cal = 200` replications.

---

## 6. Cut-point rules (pinned here; values produced by the run)

All percentiles below (`P95`, `P5`) use numpy's default **`'linear'` (type-7)** interpolation. With `R_cal = 200` these quantiles fall between order statistics, so the interpolation method is a result-affecting pin and is fixed here.

- **`τ_lo` = `max( P95(HDG | null-redundant), P95(HDG | null-noise) )`** — the higher of the two null types' 95th percentiles (not a pooled 95th), so `τ_lo` clears the 95th percentile of *each* null separately. Must be strictly positive.
- **`τ_hi`** and **Arm 1 `σ_C`**: from the meaningful sweep, select the smallest-signal (largest `σ_C`) grid point whose `P5(HDG) > τ_lo` by a margin of at least `δ = 0.01` AUC; set `τ_hi = P5(HDG)` at that point and pin **Arm 1 `σ_C`** to that grid point. (Choosing the *weakest* meaningful point that still clears keeps `τ_hi` as low as separability allows.)
- **Arm 3 `σ₃`**: from the partial sweep, select the `σ₃` whose **median HDG** is closest to the band midpoint `(τ_lo + τ_hi)/2` (tiebreak: smallest `σ₃` = strongest increment). Pin **Arm 3 `σ₃`** to that grid point.

**On what the tail placement delivers — an expectation, not a guarantee.** `τ_lo` at P95 of the nulls and `τ_hi` at P5 of the chosen meaningful point place Arms 4 and 1 with roughly 95% of their *calibration-distribution* mass on the correct side of the band. This is an **expectation, not a guarantee**: the positive control draws fresh data under a different seed (`0xFACADE`), so a ~95%-expected arm still carries real sampling probability of landing short of its `≥ 90/100` bar (spec §4). That residual risk is precisely why near-misses are reported as near-misses (spec §4) and why interpretation is constrained to what the locked rule supports (spec §8). This study sets a ruler with ~95% expected margin; it does **not** promise the positive control will pass.

---

## 7. Separability check (calibration setup control — failure invalidates the study)

After the run, **all** must hold; otherwise the design is mis-specified and is documented + revised under a **new** lock, never fudged into a band:

1. `τ_lo > 0`.
2. `τ_lo < τ_hi` with a gap `≥ δ = 0.01` AUC (a usable band exists).
3. **Monotonicity / generator sanity:** mean HDG on the meaningful sweep increases as `σ_C` decreases (the instrument detects more gain for stronger signal, oriented higher-is-better), and both null constructions produce mean HDG `≤ ~0`.
4. **Band-targetable `σ₃` exists:** at least one partial-sweep `σ₃` has median HDG inside `[τ_lo, τ_hi]`.

---

## 8. Outputs frozen into the positive-control pre-registration

`τ_lo`, `τ_hi`, Arm 1 `σ_C`, Arm 3 `σ₃` — plus the supporting HDG distributions and the separability-check results — are written to a results file and frozen into `PRE_REGISTRATION_OVP_POSCONTROL_v1.md` (§4/§5 placeholders → numbers) before that study's cold pass and lock.

The freeze also records, **as explicit numbers**, the spec §4 "pinned margin" that is otherwise left implicit in `σ_C`: **Arm 1's margin above `τ_hi`** (its calibration median HDG minus `τ_hi`) and **Arm 4's margin below `τ_lo`** (`τ_lo` minus the noise-null median HDG). This makes the positive-control pre-reg state each gated arm's distributional margin as a figure, per spec §4 ("expected `D` above `τ_hi` by a pinned margin"), rather than leaving it derived from the construction.

---

## 9. Materialization, lock, execution (this study's ordered steps)

1. **Cross-pass** this pre-registration (§11) — two independent passes, ≥1 cold; fix-author cannot clear.
2. **Lock** (`ovp-poscontrol-v1-calib-lock`): this pre-registration + `calibrate_cutpoints.py` + materialization manifest, one atomic commit + signed tag.
3. **Run exactly once** → produce `τ_lo`, `τ_hi`, Arm 1 `σ_C`, Arm 3 `σ₃`, the supporting HDG distributions, and the §7 separability check.
4. **Freeze** those outputs into the positive-control pre-registration, which then proceeds through its own ordering.

Single-execution: a technical failure is documented and amended under a new tag, never silently re-run. Outputs are recorded regardless of whether a usable band emerges — a no-band outcome is a published finding that returns the design to revision, not a result massaged into a band. (The full cross-study sequence, of which these are the front steps, is restated for context in the positive-control pre-reg §10; this study does not depend on that document to run or be verified.)

---

## 10. What this establishes / does not

- **Does:** fix the HDG decision cut points and the two band-relative arm parameters, on the same scale and instantiation the positive control will use, sourced independently of the positive control's run.
- **Does not:** validate OVP (that is the positive control), judge any candidate observable, or establish anything on the §6 maturity ladder. This is infrastructure for the positive control.

---

## 11. Cross-pass plan

Although this calibration study produces no verdict and no ledger row, it adopts the spec §7 discipline **in full** rather than relying on a loose "not really an OVP study" reading: **two independent verification passes, at least one a cold reader** with no design-conversation context, **before** it is locked. The fix-author (including the AI collaborator) cannot be a clearing reader. Divergences are recorded. (Strict-over-loose: where the spec's scope is genuinely ambiguous for an infrastructure study, this pre-registration takes the stricter obligation rather than the convenient one.)

**Where the record lives.** This study produces no verdict and no ledger row, so the two-pass record — both readers' findings, any divergence, and how each reader's independence was sourced (spec §6) — is committed with the study as `CROSSPASS_OVP_POSCONTROL_v1_CALIB.md`, not a ledger entry.

---

## 12. Discretionary pins (pinned as written; for explicit pre-lock sign-off)

Every value in this document is **pinned as written**. This section merely gathers the *discretionary* ones — those chosen by judgment rather than fixed by the spec or by construction — for explicit operator sign-off before lock. Confirming them changes nothing in the text; amending one is an ordinary pre-lock edit. **This section is struck at lock**, at which point nothing remains open.

1. Meaningful `σ_C` grid {0.25, 0.5, 1.0, 1.5, 2.0, 3.0} and partial `σ₃` grid {1.5, 2.0, 3.0, 4.0, 5.0, 6.0}.
2. Percentile rules (P95 max-of-nulls for `τ_lo`; P5 of the weakest-clearing meaningful point for `τ_hi`) and margin `δ = 0.01` AUC.
3. `R_cal = 200`, `N = 4000`.
4. Generative constants `β1 = 1.0, β2 = 1.0, σ_B = 1.0` and seed `0xCA11B` (constants match the positive control; only the seed differs).
5. Percentile interpolation method: numpy `'linear'` (type-7). (Added from the script-build findings, F1 — affects `τ_lo`/`τ_hi`.)
6. Estimator completeness: `max_iter = 1000`, `fit_intercept = True`, features not standardized. (Added from F2.)

*End of draft calibration pre-registration. Awaiting its own cold pass; not locked.*
