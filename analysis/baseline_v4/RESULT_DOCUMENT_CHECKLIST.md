# v4-baseline result document — required disclosures checklist

**Purpose.** This file is a durable note to whoever drafts the v4-baseline result document (expected around 2026-08-15, or whenever the 90-day window from lock commit `07c5b43` closes). It enumerates specific items that must be included in the result document for honesty and methodological completeness. These items emerged during the lock-fit phase and represent known limitations or required diagnostics that would otherwise be easy to forget.

This file is not part of the locked pre-registration. It is a working aid for the eventual result document, sitting alongside the locked artifacts.

---

## Required disclosures in the v4-baseline result document

### 1. Lock retirement history

The result document MUST cite the full lock history of the baseline:

- `pre-registration-v4-baseline-v1` locked at commit `16aa167` (2026-05-17), retired due to logistic regression convergence failure on unscaled features.
- `pre-registration-v4-baseline-v2` locked at commit `07c5b43` (2026-05-17), supersedes v1, adds StandardScaler preprocessing, model converged cleanly.

Both commits remain in git history. The result document's outcome refers to v2; v1's model artifacts are not used in any reported metric.

### 2. C-grid boundary selection

The result document MUST disclose, in a *Methodology limitations* section:

> *The regularization parameter C was selected at the lower boundary of the searched grid. LogisticRegressionCV's `Cs=10` default generates 10 values logarithmically spaced from 1e-4 to 1e4; the cross-validation selected C = 1e-4. A CV preference for the boundary indicates the true CV-optimal regularization may lie below the searched range. The baseline's behavior at C values < 1e-4 was not characterized. Conclusions drawn from this baseline's performance should therefore be understood as reflecting the most-regularized logistic regression within the searched grid, not necessarily a global CV optimum across all regularization levels.*

This disclosure is required because the grid-boundary selection introduces a structural ambiguity in the comparison: if v3.0 outperforms the baseline by a margin larger than ΔBSS = 0.05, a critic can reasonably ask whether a more-regularized baseline (smaller C) would have matched v3.0's performance. The disclosure foregrounds this limitation rather than burying it.

### 3. Coefficient diagnostic

After loading the locked primary model, examine and report the actual feature weights. Pseudocode for the result document author:

```python
import joblib
import numpy as np

primary = joblib.load("analysis/baseline_v4/baseline_v4_primary_model.joblib")
clf = primary.named_steps["clf"]
# clf.coef_[0] is the 120-element coefficient vector
# Note: coefficients are on the STANDARDIZED feature scale (post-StandardScaler)
# so they are directly comparable in magnitude

magnitudes = np.abs(clf.coef_[0])
# Get the feature names from get_feature_columns() in baseline_v4_dumb_model.py
# Print top 10 features by |coefficient|
```

Report findings:

- **If** the top features by |coefficient| are concentrated on CAPE plus its rolling means and standard deviations (3-10 of the top features being CAPE-derived), then the baseline can be characterized as a "CAPE-dominated predictor" and the heavily-regularized fit reflects CAPE doing the predictive work with weak contributions from other features.

- **If** the top features are diffusely distributed across many atmospheric variables (no single variable family dominating), then the baseline should be characterized as "a heavily-regularized 120-feature model whose individual feature contributions are not uniquely identifiable from this sample size." In this case, the headline metric reflects the model's aggregate behavior rather than a clear story about which atmospheric variables drive predictions.

Both characterizations are valid; honesty requires reporting which is true rather than asserting the more flattering interpretation in advance.

### 4. Forward-performance expectation

The result document MUST contextualize the in-sample CV ROC-AUC (0.91) against the realistic forward-window expectation:

> *The training-phase cross-validated ROC-AUC of 0.91 represents an upper bound on forward-window performance, not a forecast of it. Cross-validation on temporally-clustered severe-weather data produces optimism larger than typical because storm outbreaks span multiple consecutive hours and cross fold boundaries. The realistic forward-window AUC is expected in the 0.65 to 0.80 range. Forward results landing within or below that range should be characterized as expected calibration rather than as underperformance.*

This framing matters most when interpreting close comparisons. If the forward AUC for both v3.0 and the baseline lands at approximately 0.74, that is within the expected range for both and should not be characterized as v3.0 "matching" the baseline in a surprising way; both are performing within their expected forward range.

### 5. Unpopulated atmospheric columns (cross-reference)

The pre-registration already enumerates this in Section 3.3, but the result document SHOULD restate the limitation in its own *Methodology limitations* section:

> *The baseline (and v3.0, by virtue of consuming the same `atmospheric_observations` table) operates on 10 atmospheric variables. Eight additional columns declared in the schema (lifted_index, convective_inhibition, three upper-level temperatures, precipitable_water, two 180m wind variables) are not populated by the current ingestion pipeline and were therefore unavailable to both the baseline and v3.0. Expanding the ingestion to populate these variables would constitute a separate v4-baseline-v3 evaluation rather than a modification of this one.*

### 6. Comparison verdict scope (cross-reference)

The result document MUST reproduce the interpretive constraints from `PRE_REGISTRATION_v4_BASELINE.md` Section 7.3. Specifically, regardless of which comparison verdict is reached, the result document MUST observe the explicit bounds on what the verdict establishes and does not establish — most importantly, that a positive verdict does not establish any specific physical or conceptual interpretation of the framework's vocabulary (coherence, structural commitment, MCC/CI), only that v3.0's transformations extracted predictive structure under the registered conditions.

### 7. Operational disclosures (continuous-window observations)

Standard operational disclosures, to be filled in based on what happened during the accumulation window:

- Any outages or dormancies in the v3 pipeline that produced missing prediction-outcome pairs (with duration and approximate scope, per pre-reg Section 7).
- Any operational fixes (dependency updates, ingestion robustness improvements) applied during the window that did not alter methodology.
- Any disproportionate effect of outages on one regime versus the other.
- The verified-pair count per regime, with a flag if either falls below 100 (which would make the comparison underpowered per pre-reg Section 7.3).

---

## Format guidance

The result document should follow the existing `RESULT_TEMPLATE.md` structure used by prior result documents in this repository. The disclosures above should appear in:

- *Methodology limitations* section: items 2, 4, 5.
- *Lock provenance and chain of custody*: item 1.
- *Diagnostic findings*: item 3.
- *Comparison verdict*: cross-reference to item 6 from `PRE_REGISTRATION_v4_BASELINE.md` Section 7.3.
- *Implementation observations*: item 7.

---

## Provenance of this checklist

This checklist was drafted on 2026-05-17, the same day as the v4-baseline-v2 lock at commit `07c5b43`. It captures methodology limitations identified during the lock-fit phase, including those surfaced through cross-model review. It is not normative and may be revised or extended; the result document's actual content remains the responsibility of whoever drafts it, and any item in this checklist may be omitted if the result document's author has a defensible reason for doing so (with the reason itself disclosed).

*End of checklist.*