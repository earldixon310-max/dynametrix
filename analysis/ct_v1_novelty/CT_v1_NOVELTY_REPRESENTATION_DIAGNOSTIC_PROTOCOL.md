# CT-v1 Novelty + Representation Diagnostic Protocol

**Status:** LOCKED at this commit. EXPLORATORY DIAGNOSTIC. NOT A LOCKED RESULT. NOT PRE-REGISTERED AS A CONFIRMATORY STUDY.

**Operator:** Earl Dixon, Avenridge Institute
**Lock date:** 2026-05-25
**Companion document:** `CT_v1_FORMULA_LOCK.md` (this directory)
**Framework component:** AEPF Conditional Diagnostic Layer, second worked instance (after Dynametrix-HRRR independence diagnostic).

This protocol does NOT test CT-v1 predictive validity. Its sole purpose is to determine whether CT-v1 is sufficiently distinct from the predecessor CT formula (Dynametrix v2/v3, unchanged across those versions) to justify advancing to a full locked AEPF audit. No confirmatory claims may be made from this diagnostic. If findings turn out to be substantively interesting in their own right, they must be re-derived under proper AEPF lock discipline before publication.

---

## 1. Motivation

Prior Dynametrix coherence-tension implementations (v1, v2, v3 — formula unchanged across versions per `backend/app/services/feature_builder_v3.py:226-243`) returned falsifying outcomes under prior verification audits, most recently v3a at 100 km radius (`docs/RESULT_v3a_2026-05-04.md`). CT-v1 (`CT_v1_FORMULA_LOCK.md`) is a refined formulation of the same underlying coherence-tension hypothesis with substantive changes documented in Section 10 of the formula lock.

This diagnostic addresses the re-emergence concern: a candidate study testing a refined version of a previously-falsified hypothesis may, by its structure, produce another falsification for the same reasons the original was falsified. The viability question is whether CT-v1's specific formula changes (true phase entropy, circularity removal in persistence, explicit phase classifier, dropped phase-transition term in instability) produce outputs that meaningfully differ from the predecessor formula on the same atmospheric data — or whether CT-v1 numerically tracks the predecessor closely enough that the new structural content is doing no work.

If CT-v1 numerically differs from predecessor CT on shared atmospheric inputs, the new structural content is doing work and CT-v1 advances to full AEPF lock as a genuine successor audit. If CT-v1 tracks predecessor CT closely, CT-v1 is archived as considered-but-deferred with documented rationale.

## 2. Procedural boundaries

This diagnostic:

- **Does not** evaluate predictive validity of CT-v1.
- **Does not** confirm the coherence-tension hypothesis.
- **Does not** supersede the v3a falsification.
- **Does not** produce confirmatory evidence about CT-v1's operational utility.
- **Cannot** be cited as confirmatory evidence in any subsequent published audit.
- **Does not** modify the formula lock at `CT_v1_FORMULA_LOCK.md`.

Its sole purpose is determining whether CT-v1 is sufficiently novel and representationally distinct from predecessor CT to justify a locked confirmatory evaluation.

## 3. Diagnostic structure

Five diagnostic measurements, organized into one gating diagnostic and four characterization diagnostics:

| ID | Diagnostic | Role | Output disposition |
|---|---|---|---|
| D1 | Structural similarity (Pearson correlation) | **GATE** | PROCEED / PROCEED_WITH_DISCLOSURE / ARCHIVE |
| D2 | Representation-equivalence stress test | Characterization | INFORMATIVE_FOR_DISCLOSURE |
| D3 | Entropy + mix ablation | Characterization | INFORMATIVE_FOR_DISCLOSURE |
| D4 | Normalization control | Characterization | INFORMATIVE_FOR_DISCLOSURE |
| D5 | Least-tuned-region comparison | Characterization | INFORMATIVE_FOR_DISCLOSURE |

D1 alone determines whether CT-v1 advances to full AEPF lock. D2-D5 produce characterization outputs that get attached to the eventual pre-registration's required disclosures section but do not gate the lock decision. If D1 returns ARCHIVE, D2-D5 do not run.

## 4. Historical comparison window

The diagnostic comparison runs over the existing `atmospheric_observations` data range, with the training/comparison split defined in Section 5.

- Window start: 2026-04-20 (earliest atmospheric_observation in the database).
- Window end: most recent atmospheric_observation as of execution time (currently 2026-05-29).
- Locations: all 12 distinct location_ids with atmospheric_observations data in the window.
- Cells included: each (location_id, observed_at) pair with sufficient inputs (per the formula lock's 75% completeness rule).

## 5. Training / comparison split (LOCKED)

**Split boundary:** 2026-05-15 00:00 UTC.

- **Training subset:** all `atmospheric_observations` rows with `observed_at < 2026-05-15 00:00 UTC`. Approximately 3,600 records spanning 25 days.
- **Comparison subset:** all `atmospheric_observations` rows with `observed_at >= 2026-05-15 00:00 UTC`. Approximately 4,320 records spanning 15 days.

The training subset is used exclusively for learning min/max normalization parameters per Section 4 of the formula lock. The comparison subset is used for all five diagnostic measurements.

Date selected from sample-balance analysis (train/comp ratio = 0.83, closest to 1.0 among candidates; training includes both pre-transition 6-location regime and post-transition 12-location regime; comparison entirely in stable 12-location regime).

**Disclosure:** the May 4-7 2026 window contains a data-collection gap likely attributable to task #92 (Celery worker instability). The 75% completeness rule in the formula lock partially handles this; some cells near the gap may have rolling-window features computed from incomplete histories. Affected cells will be excluded by the missing-data rule if completeness falls below 75%.

## 6. D1 — Structural similarity (gating diagnostic)

### 6.1 Purpose

Determine whether CT-v1 values numerically track predecessor CT (v2/v3 unchanged formula) outputs on the same atmospheric data.

### 6.2 Procedure

For each cell in the comparison subset:

1. Compute predecessor CT using the existing implementation at `backend/app/services/feature_builder_v3.py:226-243` (which is unchanged from v2 per the docstring), with min/max scaling learned from the training subset.
2. Compute CT-v1 using the formula stack at `CT_v1_FORMULA_LOCK.md`, with min/max scaling learned from the training subset.
3. Pair the resulting (CT_predecessor, CT_v1) values at each cell.

Compute:

$$
r = \text{Pearson}(\text{CT}_{\text{predecessor}}, \text{CT}_{v1})
$$

across all matched cells. Spearman correlation reported as secondary/exploratory only.

### 6.3 Bootstrap

Bootstrap 95% confidence interval via percentile method:
- $B = 10{,}000$ resamples
- Random seed: `0x1DEA` (reuse of HRRR diagnostic seed for reproducibility convention)
- Stratified by cell (not by event/non-event, since no event labels enter D1)

### 6.4 Decision rule (LOCKED)

Disposition determined by the **point estimate** of $r$:

| Correlation range | Verdict | Action |
|---|---|---|
| $r < 0.50$ | PROCEED | CT-v1 advances to full AEPF cross-model review and lock. The new structural content is doing work distinct from predecessor formula. |
| $0.50 \leq r \leq 0.85$ | PROCEED_WITH_DISCLOSURE | CT-v1 advances to lock, but the pre-registration's §9 (required disclosures) must explicitly state the partial correlation with predecessor formula and bound the informational content of the eventual audit accordingly. |
| $r > 0.85$ | ARCHIVE | Do not proceed with locked CT-v1 audit. Document the diagnostic result. Archive CT-v1 alongside the Dynametrix-HRRR pre-registration as considered-but-deferred. |

The bootstrap CI is reported for transparency but does not affect disposition. Thresholds are pre-committed at this lock and may not be adjusted post-result.

## 7. D2 — Representation-equivalence stress test (characterization)

### 7.1 Purpose

Determine whether CT-v1's response to representational perturbations differs from predecessor CT's response. A CT-v1 that is genuinely different in structure (not just in surface formulation) should respond to representation-preserving perturbations differently than the predecessor.

### 7.2 Perturbation set (LOCKED)

Five enumerated perturbations applied to the comparison subset:

| ID | Perturbation | Description |
|---|---|---|
| P1 | Alternate normalization | Re-compute both CT_predecessor and CT-v1 using z-score normalization (training-set learned mean/std) instead of min-max |
| P2 | Phase probability uniform shift | Add +0.02 to each of $p_{\text{rain}}, p_{\text{snow}}, p_{\text{ice}}, p_{\text{none}}$ (deterministic, not random), then renormalize so they sum to 1. Applies only to CT-v1 (predecessor does not use explicit phase probabilities) |
| P3 | Temperature change aggregation window | Replace 3-hour temperature change with 4-hour temperature change in $T$ and $A$ |
| P4 | Missing-data handling | Replace "drop incomplete windows" with linear interpolation across gaps (still subject to 75% threshold) |
| P5 | Alternate equivalent phase encoding | Define $p_{\text{rain}}$ as $1 - p_{\text{snow}}^{\text{raw}} - p_{\text{ice}}^{\text{raw}} - p_{\text{none}}$ instead of computed directly (mathematically equivalent under exact arithmetic; tests numerical stability) |

### 7.3 Measurement

For each perturbation $p_i \in \{P1, P2, P3, P4, P5\}$, compute the median absolute change in CT values across the comparison subset:

$$
\Delta_{v1}(p_i) = \text{median}\left( |CT_{v1}^{\text{perturbed}}(p_i) - CT_{v1}^{\text{baseline}}| \right)
$$

$$
\Delta_{\text{pred}}(p_i) = \text{median}\left( |CT_{\text{pred}}^{\text{perturbed}}(p_i) - CT_{\text{pred}}^{\text{baseline}}| \right)
$$

(For P2, $\Delta_{\text{pred}}$ is undefined because predecessor doesn't use explicit phase probabilities; that perturbation produces a CT-v1-only measurement.)

Then compute rank correlation of perturbation sensitivities across the available P1-P5 pairs:

$$
\rho = \text{SpearmanRankCorr}\left( \{\Delta_{v1}(p_i)\}_i, \{\Delta_{\text{pred}}(p_i)\}_i \right)
$$

over $i$ for which $\Delta_{\text{pred}}(p_i)$ is defined (i.e., excluding P2).

### 7.4 Interpretation

- High rank correlation ($\rho > 0.7$): CT-v1 and predecessor respond to perturbations in the same ordinal sensitivity profile. Representational sensitivity is similar; the structural differences in formula are not driving meaningfully different perturbation responses.
- Low rank correlation ($\rho < 0.3$): CT-v1 and predecessor respond to perturbations in different ordinal sensitivity profiles. Structural differences are producing distinct representational sensitivities.
- Intermediate: partial sensitivity overlap; report magnitude and rank-order for disclosure.

This is a characterization output. It does not affect the lock decision. Output text attaches to the pre-registration's disclosure section as the "representational sensitivity profile" finding.

## 8. D3 — Entropy + mix ablation (characterization)

### 8.1 Purpose

Determine whether the new entropy ($E$) and phase-mix ($M$) terms specifically contribute to CT-v1's behavior, or whether the formula's behavior is driven by other components.

### 8.2 Procedure (LOCKED ablation convention)

Compute four CT-v1 variants on the comparison subset:

1. **Full CT-v1** — baseline per formula lock.
2. **CT-v1 without $E$** — replace $E$ with training-set median of normalized $E$ values. Preserves operating regime while removing information content.
3. **CT-v1 without $M$** — replace $M$ with training-set median of normalized $M$ values.
4. **CT-v1 with uniform weights** — recompute with $I = 0.5T + 0.5S$, $C = 0.5E + 0.5M$, $P = 0.33A + 0.33R + 0.33Q$. Tests sensitivity to the locked weighting choices.

Median replacement (not zero, not 0.5, not renormalization) is the locked ablation convention.

### 8.3 Measurement

For each variant, compute Pearson correlation with full CT-v1:

$$
r_{\text{ablate}, v} = \text{Pearson}\left( CT_{v1, v}, CT_{v1, \text{full}} \right)
$$

over $v \in \{$no-$E$, no-$M$, uniform-weights$\}$.

### 8.4 Interpretation

- $r_{\text{ablate}} \approx 1.0$ for a given variant: that variant's removed/modified component contributes little to the full CT-v1 behavior.
- $r_{\text{ablate}} < 0.95$: that component is doing meaningful work.

Output text attaches to the pre-registration's disclosure section as the "component-contribution profile" finding.

## 9. D4 — Normalization control (characterization)

### 9.1 Purpose

Determine whether CT-v1's novelty relative to predecessor CT is driven by structural formula differences or by the normalization rule alone.

### 9.2 Procedure

Compute CT-v1 under three normalization schemes:

1. **Locked min-max** (per formula lock Section 4) — baseline.
2. **Z-score** with training-set learned mean/std, capped at $[\mu - 3\sigma, \mu + 3\sigma]$ and rescaled to $[0, 1]$.
3. **Quantile** (training-set learned 5th/95th percentiles instead of min/max).

For each scheme, compute Pearson correlation of CT-v1 with predecessor CT on the comparison subset.

### 9.3 Interpretation

- All three schemes produce similar correlation values: novelty is driven by structural formula difference, not by normalization.
- Schemes produce substantially different correlations: at least part of CT-v1's apparent novelty is normalization-rule-dependent rather than structural.

Output text attaches to the pre-registration's disclosure section as the "normalization sensitivity" finding.

## 10. D5 — Least-tuned-region comparison (characterization)

### 10.1 Purpose

Determine whether CT-v1's novelty generalizes across regions or is specific to regions with heavy parameter-tuning history.

### 10.2 Operational definition of "least-tuned region"

Per the Conditional Diagnostic Layer's procedural boundary on "held-out" claims (no truly held-out region exists in the dynametrix codebase as of this lock date), this diagnostic uses the **least-tuned region** criterion:

For each location, count the number of git commits in the `analysis/` and `backend/app/services/feature_builder*` paths that reference the location's identifier or were authored during a window where that location's data informed a tuning decision. The location with the lowest count is designated the least-tuned region for this diagnostic.

If multiple locations tie at the minimum count, the location whose data entered the system most recently (by min `observed_at`) is selected. The selection criterion is deterministic and computed before the diagnostic runs.

### 10.3 Procedure

Compute D1's structural similarity correlation $r$ separately for:

1. All locations pooled (matches the main D1 output).
2. The least-tuned region only.
3. The complement: all locations EXCEPT the least-tuned region.

Compare the three correlations.

### 10.4 Interpretation

- Similar correlations across all three subsets: CT-v1's novelty generalizes across regions.
- Substantially different correlation in the least-tuned region: CT-v1's apparent novelty in the main D1 result may be region-specific (potentially tuning-influenced).

Output text attaches to the pre-registration's disclosure section as the "regional generalization" finding.

**Caveat (LOCKED disclosure):** even the least-tuned region is not a true held-out region in the methodological sense. All locations have been in continuous evaluation since some point in the dynametrix operational history. The "least-tuned" criterion is the best available approximation given the data record; the diagnostic's regional-generalization claim is bounded accordingly.

## 11. Composition rule

D1 alone determines the lock disposition:

- D1 returns PROCEED ($r < 0.5$) → CT-v1 advances to full AEPF pre-registration and cross-model review for a confirmatory locked audit. D2-D5 outputs attach as characterization disclosures.
- D1 returns PROCEED_WITH_DISCLOSURE ($0.5 \leq r \leq 0.85$) → CT-v1 advances to lock with required disclosure of bounded informational content. D2-D5 outputs strengthen and contextualize the disclosure.
- D1 returns ARCHIVE ($r > 0.85$) → CT-v1 is archived as considered-but-deferred. D2-D5 do not run.

D2-D5 produce characterization outputs that attach to the eventual pre-registration but do not gate the lock decision under any disposition.

## 12. Edge-case framing

This protocol's five-diagnostic structure is unusually heavy for a Conditional Diagnostic Layer instance. Most candidate studies will trigger one or two diagnostics from the layer (the Dynametrix-HRRR diagnostic triggered only the independence check). CT-v1 triggers five because it sits in the specific territory of "refined formulation of previously-falsified hypothesis under explicit re-emergence concern."

This protocol's full five-diagnostic structure is the appropriate form for this case and should not be read as the AEPF default. The Conditional Diagnostic Layer accommodates variability: protocols include only the diagnostics whose trigger conditions apply, and most protocols will be shorter than CT-v1's.

## 13. Protocol lock

This protocol is locked at the commit containing this document and the companion `CT_v1_FORMULA_LOCK.md`. Subsequent modifications to the Conditional Diagnostic Layer framework may revise the protocol template, but the CT-v1 application uses this locked version of the protocol. No edits to decision thresholds, perturbation specifications, ablation conventions, normalization schemes, or composition rules are permitted after the lock commit.

## 14. Output deliverable

A single markdown summary committed alongside the diagnostic script outputs, naming convention:

`DIAGNOSTIC_CT_v1_NOVELTY_<date>.md`

Containing:

- Diagnostic date and operator.
- Training subset size, comparison subset size, included cells, excluded cells.
- D1 Pearson correlation point estimate and 95% bootstrap CI.
- D1 disposition (PROCEED / PROCEED_WITH_DISCLOSURE / ARCHIVE).
- D2-D5 characterization outputs (if D1 disposition is PROCEED or PROCEED_WITH_DISCLOSURE).
- Explicit "EXPLORATORY DIAGNOSTIC, NOT A LOCKED RESULT" footer.

Commit message convention: "exploratory diagnostic; not a locked result; CT-v1 novelty + representation verdict."

---

*End of CT-v1 Novelty + Representation Diagnostic Protocol.*
