# Instrument Validation — AEPF calibration audit (operating characteristics)

**Replications:** 100  |  **N per arm:** 4000  |  **K bins:** 10  |  **master seed:** 0x1dea
**Decision rule:** AI-calibration template §5-6 (verbatim).

## Verdict: **FAIL**

A pre-committed criterion was not met (see table).

| arm | kind | % Calibrated | % Rejected | mean bins passed (/10) | mean BSS |
|---|---|---|---|---|---|
| calibrated_uniform | POSITIVE | 100 | 0 | 9.6 | 0.333 |
| calibrated_asym | POSITIVE | 89 | 11 | 7.5 | 0.127 |
| calibrated_bimodal | POSITIVE | 100 | 0 | 9.5 | 0.501 |
| noisy_sigma_0.25 | TOLERANCE | 100 | 0 | 9.4 | 0.326 |
| noisy_sigma_0.5 | TOLERANCE | 82 | 18 | 7.5 | 0.301 |
| noisy_sigma_1.0 | TOLERANCE | 0 | 100 | 2.6 | 0.218 |
| noisy_sigma_2.0 | TOLERANCE | 0 | 100 | 1.8 | 0.006 |
| overconfident_T0.5 | NEGATIVE | 0 | 100 | 2.6 | 0.287 |
| underconfident_T2.0 | NEGATIVE | 0 | 100 | 2.1 | 0.287 |
| shift_pos_b+0.5 | NEGATIVE | 0 | 100 | 1.3 | 0.301 |
| shift_neg_b-0.5 | NEGATIVE | 0 | 100 | 1.2 | 0.302 |

### Outcome breakdown (counts over 100 replications)

| arm | strong | acceptable | drift | not-calibrated |
|---|---|---|---|---|
| calibrated_uniform | 95 | 5 | 0 | 0 |
| calibrated_asym | 0 | 89 | 11 | 0 |
| calibrated_bimodal | 90 | 10 | 0 | 0 |
| noisy_sigma_0.25 | 87 | 13 | 0 | 0 |
| noisy_sigma_0.5 | 19 | 63 | 17 | 1 |
| noisy_sigma_1.0 | 0 | 0 | 1 | 99 |
| noisy_sigma_2.0 | 0 | 0 | 0 | 100 |
| overconfident_T0.5 | 0 | 0 | 1 | 99 |
| underconfident_T2.0 | 0 | 0 | 0 | 100 |
| shift_pos_b+0.5 | 0 | 0 | 0 | 100 |
| shift_neg_b-0.5 | 0 | 0 | 0 | 100 |

*Methods-level instrument validation, not a locked AEPF study. Negative controls cover temperature-scaled and logit-shift miscalibration families only.*