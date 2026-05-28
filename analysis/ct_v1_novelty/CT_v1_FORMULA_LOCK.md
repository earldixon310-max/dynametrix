# CT-v1 Formula Lock

**Status:** LOCKED at this commit. No subcomponent formula, parameter value, normalization rule, or classifier coefficient may be modified post-commit. Any change becomes CT-v2 with its own lock.

**Operator:** Earl Dixon, Avenridge Institute
**Lock date:** 2026-05-25
**Successor of:** CT (Coherence Tension) as instantiated in Dynametrix v1, v2, v3 (formula unchanged across these versions per `backend/app/services/feature_builder_v3.py:226-243`). The predecessor formula was effectively falsified by the v3a verification result (`docs/PRE_REGISTRATION_v3a.md`, `docs/RESULT_v3a_2026-05-04.md`) at 100 km radius.

This lock document specifies CT-v1's subcomponent formulas, normalization rule, phase classifier, and circularity guardrails prior to any computation of CT-v1 on dynametrix atmospheric data. It is referenced by the companion document `CT_v1_NOVELTY_REPRESENTATION_DIAGNOSTIC_PROTOCOL.md`, which governs the pre-lock viability gate that determines whether CT-v1 advances to full AEPF lock as a confirmatory study.

---

## 1. Master formula

$$
CT_{v1} = \frac{I \times C}{\sqrt{P + \epsilon}}
$$

with $\epsilon = 10^{-6}$.

## 2. Subcomponents

### 2.1 Instability term

$$
I = 0.6 \cdot T + 0.4 \cdot S
$$

where $T$ = storm transition score, $S$ = storm intensity score. Both normalized to $[0, 1]$ per Section 4.

Differs from predecessor CT (which used $0.50 \cdot \text{phase\_transition} + 0.30 \cdot \text{storm\_transition} + 0.20 \cdot \text{storm\_intensity}$). CT-v1 drops `phase_transition_score` from the instability term.

### 2.2 Competition term

$$
C = 0.7 \cdot E + 0.3 \cdot M
$$

where $E$ = phase probability entropy, $M$ = phase mix score. Both defined in Section 3.

Differs from predecessor CT (which used `phase_prob_entropy` computed as a rolling variance of CAPE/dewpoint/pressure — not a true phase entropy — and `phase_mix_score_3h` computed from precipitation flag and temperature flip). CT-v1 uses true Shannon entropy of explicit phase probabilities and a max-based mix score.

### 2.3 Persistence term

$$
P = 0.5 \cdot A + 0.3 \cdot R + 0.2 \cdot Q
$$

where $A$ = atmospheric stability proxy, $R$ = reliability proxy, $Q$ = data quality proxy.

Differs from predecessor CT (which used `stability` from CAPE/pressure changes, `reliability` from lag-1 autocorrelation, and `ci_confidence` = $1 - \text{phase\_prob\_entropy}$). The substitution of $Q$ for `ci_confidence` removes a structural circularity in the predecessor where the same quantity appeared in both Competition and Persistence with opposite signs.

## 3. Phase probability classifier (locked)

CT-v1 requires explicit phase probabilities $p_{\text{rain}}, p_{\text{snow}}, p_{\text{ice}}, p_{\text{none}}$ summing to 1. These are computed from atmospheric_observations inputs via the locked classifier below. The classifier is deterministic; reading from atmospheric inputs already present in the pipeline; introducing no new external data dependencies; and pre-committed before any CT-v1 computation on dynametrix data.

### 3.1 Wet-bulb temperature (Stull simple approximation)

$$
T_w \approx T - \frac{T - T_d}{3}
$$

where $T$ = `temperature_2m` (°C), $T_d$ = `dewpoint_2m` (°C). Stull approximation; typical error ±0.5°C. Pre-committed for reproducibility over accuracy.

### 3.2 Snow probability (Koistinen-Saltikoff sigmoid)

$$
p_{\text{snow}}^{\text{raw}} = \frac{1}{1 + \exp\left(\frac{T_w - 1.16}{0.66}\right)}
$$

Parameters $a = 1.16$°C, $b = 0.66$°C from Koistinen, J. and Saltikoff, E. (2006), "Experience on Customer Products of Accumulated Snow, Sleet and Rain," Geophysical Publications. **Citation-anchored, pre-committed.**

### 3.3 Ice phase probability (Gaussian, narrow band)

$$
p_{\text{ice}}^{\text{raw}} = \exp\left(-\frac{(T_w - (-1.0))^2}{2 \cdot 1.0^2}\right) \cdot 0.3
$$

Gaussian centered at $T_w = -1.0$°C, $\sigma = 1.0$°C, amplitude factor 0.3 (caps maximum ice probability at 0.3 to avoid dominating the snow/rain split). **Operator choice from meteorological reasoning; pre-committed before any CT-v1 computation.** The freezing-rain regime is the most uncertain of the four phases; this conservative narrow-band Gaussian is more defensible than a wide formulation that would attribute ice to broader temperature ranges.

### 3.4 Precipitation activity factor

$$
\alpha = \text{clip}\left(\frac{\text{precipitation} - 0.1}{1.0}, 0, 1\right)
$$

where `precipitation` is from `atmospheric_observations.precipitation` (mm in the past hour). $\alpha = 0$ when precip < 0.1 mm/h (no meaningful precipitation); $\alpha = 1$ when precip $\geq$ 1.1 mm/h (active precipitation). **Operator choice; pre-committed.** Threshold of 0.1 mm/h chosen to match typical instrument noise floors for precipitation observation.

### 3.5 Final phase probabilities (normalized)

$$
\begin{aligned}
p_{\text{none}} &= 1 - \alpha \\
p_{\text{snow}}^* &= \alpha \cdot (1 - p_{\text{ice}}^{\text{raw}}) \cdot p_{\text{snow}}^{\text{raw}} \\
p_{\text{rain}}^* &= \alpha \cdot (1 - p_{\text{ice}}^{\text{raw}}) \cdot (1 - p_{\text{snow}}^{\text{raw}}) \\
p_{\text{ice}}^* &= \alpha \cdot p_{\text{ice}}^{\text{raw}}
\end{aligned}
$$

By construction, $p_{\text{rain}}^* + p_{\text{snow}}^* + p_{\text{ice}}^* + p_{\text{none}} = 1$.

### 3.6 Disclosure on classifier design

The Koistinen-Saltikoff coefficients are citation-anchored from published meteorological literature. The ice-phase Gaussian parameters and the precipitation-activity threshold are operator choices made from meteorological reasoning prior to any CT-v1 computation on dynametrix atmospheric data. These choices may produce different phase distributions than would emerge from a learned classifier; the classifier is intended to provide reproducible non-degenerate phase probabilities specifically in transition-zone conditions, which is where the entropy term $E$ carries discriminative information.

The classifier's parameters are not informed by any observed CT-v1 outputs, any v3a evaluation results, or any other downstream computation. This temporal order is documented to preempt the post-hoc-tuning concern.

## 4. Normalization rule

All component inputs to CT-v1 subcomponents (and to the phase classifier where applicable) must be scaled to $[0, 1]$ before being used in the master formula.

Method:

$$
x_{\text{norm}} = \text{clip}\left(\frac{x - x_{\min}}{x_{\max} - x_{\min}}, 0, 1\right)
$$

Critical constraints:

- $x_{\min}$ and $x_{\max}$ are learned from the **training subset only**.
- Training subset is defined as all `atmospheric_observations` rows with `observed_at < 2026-05-15 00:00 UTC`, per the companion diagnostic protocol's Section 5.
- Comparison subset (used in the diagnostic and any subsequent CT-v1 computation) uses the training-set-learned scaling values.
- Values that fall outside $[x_{\min}, x_{\max}]$ at evaluation time are clipped to $[0, 1]$.
- Scaling parameters are computed once from the training subset and frozen for all subsequent CT-v1 computations.

## 5. Subcomponent definitions

### 5.1 Storm transition score ($T$)

$$
T = \text{mean}\left( |\Delta\text{temp}_{3h}|, |\Delta\text{pressure}_{3h}|, |\Delta\text{wind}_{3h}|, |\Delta\text{humidity}_{3h}|, \text{phase\_change}_{3h} \right)
$$

Each input normalized to $[0, 1]$ via Section 4 before averaging. `phase_change_3h` defined as the 3-hour change in `max(p_rain, p_snow, p_ice, p_none)` (i.e., the change in dominant phase confidence over 3 hours).

### 5.2 Storm intensity score ($S$)

$$
S = \text{mean}\left( \text{precipitation\_rate}, \text{wind\_speed}, \text{pressure\_drop}_{6h}, \text{humidity}, \text{cloud\_cover} \right)
$$

Each input normalized to $[0, 1]$ via Section 4 before averaging. `cloud_cover` is not directly available in `atmospheric_observations`; this term is computed as $1 - \text{dewpoint\_depression}_{\text{normalized}}$ as a proxy (low dewpoint depression implies high cloud cover; pre-committed substitution).

### 5.3 Phase probability entropy ($E$)

$$
E = -\frac{\sum_{i \in \{rain, snow, ice, none\}} p_i \cdot \log(p_i + \epsilon)}{\log(4)}
$$

with $\epsilon = 10^{-6}$. The phase probabilities come from Section 3.5. $E \in [0, 1]$; $E \approx 0$ when one phase dominates; $E$ approaches 1 when all four phases are equally probable.

### 5.4 Phase mix score ($M$)

$$
M = 1 - \max(p_{\text{rain}}, p_{\text{snow}}, p_{\text{ice}}, p_{\text{none}})
$$

$M = 0$ when one phase dominates completely; $M$ rises as the distribution becomes more uniform.

### 5.5 Atmospheric stability proxy ($A$)

$$
A = 1 - \text{mean}\left( |\Delta\text{temp}_{3h}|, |\Delta\text{pressure}_{3h}|, |\Delta\text{wind}_{3h}|, |\Delta\text{humidity}_{3h}| \right)
$$

Each change term normalized via Section 4 before averaging. High $A$ means the system is relatively stable.

### 5.6 Reliability proxy ($R$)

$$
R = 1 - \text{mean}\left( \text{std}(\text{temp}_{6h}), \text{std}(\text{pressure}_{6h}), \text{std}(\text{wind}_{6h}), \text{std}(\text{humidity}_{6h}) \right)
$$

Each standard deviation term normalized via Section 4 before averaging. High $R$ means recent 6-hour observations are internally consistent.

### 5.7 Data quality proxy ($Q$)

$$
Q = 1 - \text{missing\_fraction}_{6h}
$$

where `missing_fraction_6h` is the fraction of expected hourly observations missing in the preceding 6-hour window. $Q = 1$ when all 6 hourly observations are present; $Q = 0$ when none are present. Replaces the predecessor's `ci_confidence` (which was circular with $E$).

## 6. Circularity guardrails

CT-v1 must NOT use:

- Event labels (any column derived from `ground_truth_events` or `storm_reports`).
- Future-time observation data relative to the computation timestamp.
- Post-event observations.
- Model confidence values derived from CT-v1 itself.
- Human-labeled storm outcomes.
- Any feature whose computation includes the target label.

If a feature cannot be computed without label leakage, it must be excluded. Lookback windows (3h and 6h in the formulas above) are applied to past observations only, never to future observations relative to the cell's computation timestamp.

## 7. Missing data rule

If fewer than 75% of required inputs are available in a 6-hour window (i.e., fewer than 5 of the 6 expected hourly observations), CT-v1 is **not computed** for that time step (returns NaN, excluded from downstream computations).

If at least 75% are available:

- Compute available terms.
- Use $Q$ to penalize missingness in the persistence term.
- Do not impute from future values.

## 8. Locked CT-v1 expression

Combining all subcomponents:

$$
CT_{v1} = \frac{(0.6T + 0.4S) \times (0.7E + 0.3M)}{\sqrt{(0.5A + 0.3R + 0.2Q) + 10^{-6}}}
$$

with $T, S, E, M, A, R, Q$ defined per Sections 5.1 through 5.7, with all inputs normalized per Section 4, with phase probabilities computed via Section 3 classifier, and with missing-data rule per Section 7.

## 9. Disclosures on inherited and new design choices

| Component | Source | Status |
|---|---|---|
| Master formula structure ($I \cdot C / \sqrt{P}$) | Inherited from predecessor CT | Carried forward unchanged |
| Subcomponent weights (0.6/0.4, 0.7/0.3, 0.5/0.3/0.2) | Operator pre-committed | Locked at this draft; not learned |
| Phase classifier — snow term | Koistinen & Saltikoff (2006), citation-anchored | Literature-anchored |
| Phase classifier — ice term | Operator pre-committed | Locked at this draft; not literature-anchored |
| Phase classifier — precipitation activity threshold | Operator pre-committed | Locked at this draft; not literature-anchored |
| Wet-bulb approximation | Stull simple form | Citation-anchored |
| Cloud cover proxy via dewpoint depression | Operator pre-committed substitution | Locked at this draft |
| Training-split boundary (2026-05-15 00:00 UTC) | Operator pre-committed from sample-balance analysis | Locked |
| Normalization method (min-max, training-only) | Pre-committed | Locked |
| Missing-data threshold (75%) | Operator pre-committed | Locked |
| Decision-threshold bands in companion diagnostic protocol | Pre-committed at protocol draft | Locked via companion protocol |

## 10. Status and successor relationship

CT-v1 is locked at this commit. No subsequent edit to this document is permitted. Any modification to formula, parameter, threshold, or classifier coefficient becomes CT-v2 and requires a new lock document and a new diagnostic protocol.

CT-v1 supersedes CT as instantiated in Dynametrix v1, v2, and v3 (formula unchanged across those versions, falsified by v3a verification at 100 km radius). CT-v1 differs from those instantiations in:

- Instability: drops `phase_transition_score` term.
- Competition: replaces variance-proxy "phase_prob_entropy" with true Shannon entropy of explicit phase probabilities (Section 5.3); replaces precip-flag-based phase mix with max-based phase mix (Section 5.4).
- Persistence: replaces circular `ci_confidence` with non-circular data-quality proxy $Q$ (Section 5.7); replaces CAPE/pressure-based stability with multi-variable change-based stability (Section 5.5); replaces lag-1-autocorrelation reliability with 6-hour standard-deviation-based reliability (Section 5.6).
- Phase classifier: introduces explicit Koistinen-Saltikoff-based phase probability computation absent in predecessors.

If CT-v1 advances to AEPF lock after the companion diagnostic, the resulting confirmatory study tests whether CT-v1 produces values that, used as a probabilistic forecast for severe weather events at the registered locations and time windows, demonstrate Brier Skill Score against climatology $> 0$ with 95% bootstrap CI excluding zero. That hypothesis is NOT tested by the present formula lock; it is the subject of the eventual locked CT-v1 audit if the diagnostic returns PROCEED.

If CT-v1 returns NULL under the eventual locked audit, it joins the prior falsifications. If it returns POSITIVE, the prior falsifications are reframed as instantiation-specific rather than concept-specific. Either outcome is published under AEPF discipline.

---

*End of CT-v1 Formula Lock.*
