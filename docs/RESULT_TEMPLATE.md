# Result Document Template — v1

**Template version:** v1.0
**Purpose:** Canonical structure for result documents published under the pre-registered evaluation methodology. Used for all locked outcome reports — public case studies and commercial customer deliverables alike.

**Source documents this template was distilled from:**

- `docs/RESULT_v3a_2026-05-04.md` (weather verification sub-test)
- `docs/RESULT_GW_v1_2026-05-04.md` (gravitational-wave blind detection)
- `docs/RESULT_GW_QUIETWELL_v1_2026-05-04.md` (within-segment differential)
- `docs/RESULT_DISTILBERT_SST2_v1_2026-05-06.md` (AI calibration audit)
- `docs/RESULT_TOXIC_BERT_v1_2026-05-06.md` (AI calibration audit)

The template specifies STRUCTURE and VOICE, not specific narrative wording. Each result document is authored individually within these conventions; the goal is consistent institutional presentation, not copy-paste reuse.

---

## How to use this template

Sections marked **REQUIRED** must appear in every result document, in the order specified. Sections marked **OPTIONAL** appear when applicable. Sections marked **CONDITIONAL** appear only under specific circumstances (described in their guidance).

Fields marked `[FILL]` are populated with engagement-specific values. Fields marked `[FILL or omit]` may be left out if not applicable.

The voice register is **third-person, declarative, factual.** Outcomes are stated as measurements, not as judgments. Numeric findings are reported with appropriate precision (4 decimal places for probabilities, 2 for percentages, scientific notation for values outside [10⁻⁴, 10⁴]). Customer-facing customer engagement deliverables follow the same voice as public case studies; the methodology's institutional tone is the product.

---

## Section 1 — Title and Metadata Block (REQUIRED)

Format:

```markdown
# [Test Name] — Outcome

**Test identifier:** `[FILL: kebab-case identifier]`
**Pre-registration:** `[FILL: path to pre-reg]` (locked under git commit `[FILL: 7-char hash]` on [FILL: ISO date])
**Run date:** [FILL: ISO date]
**Customer:** [FILL: organization name OR "Earl Dixon (self-audit, public demonstration)" for case studies]
**Auditor:** [FILL: auditing party]
**Status:** Locked outcome. Per pre-registration Section 11 (or equivalent), this result document is bound and not subject to revision.
```

If the run date differs from the lock date by more than one day (e.g., due to operational delays), include a parenthetical: `Run date: 2026-05-06 (lock-to-run gap of 2 days while resolving [reason]; documented in Implementation Observations below)`.

---

## Section 2 — Summary (REQUIRED)

One to three short paragraphs. The first paragraph leads with the outcome stated factually. Subsequent paragraphs (if any) provide one or two sentences of context establishing what makes the outcome meaningful or contested.

Voice rules:

- State the outcome in the first sentence or two.
- Use the exact outcome label registered in the pre-registration's decision criteria (e.g., `R = 52 of 100`, `Calibration drift detected`, `Not calibrated`, `Hypothesis falsified`).
- Cite the most informative single numeric finding (the rank, the BSS, the most striking per-bin observation).
- If the outcome contradicts what a casual reader would expect from accuracy or other adjacent metrics, surface the contradiction in this section. Do not bury it.

Length: typically 100–250 words. Resist over-summarizing — the document body has the specifics; the summary just orients the reader.

---

## Section 3 — Outcome per Pre-Registered Decision Criteria (REQUIRED)

A short recap of the pre-registered decision rules, followed by a table or list mapping each registered outcome tier to whether its criterion was met. The outcome is stated explicitly at the bottom of the section.

Standard format:

```markdown
The following decision rules were locked in advance (pre-registration Section 6.1):

| Outcome | Criterion | Met? |
|---|---|---|
| [tier 1] | [criterion 1] | [Yes / No] |
| [tier 2] | [criterion 2] | [Yes / No] |
| **[selected outcome]** | **[criterion]** | **[Yes]** |
| [tier 4] | [criterion 4] | [—] |

[Optional 1-2 sentences describing edge cases, threshold computations, or boundary conditions that
clarify why this specific tier was selected.]

**[Test name] outcome: [outcome label].**
```

The bolded row in the table is the selected outcome. The final declarative statement at the bottom is required and uses the exact outcome label registered in the pre-registration.

---

## Section 4 — Result Detail (REQUIRED)

Three subsections in this fixed order:

### 4.1 Sample summary

A small table summarizing what was tested. Domain-specific but always includes: model or system identifier, test data identifier and size, any pre-registered hashes (data, model revision, etc.), base rate or other relevant population statistic.

### 4.2 Aggregate metrics

A table of the aggregate metrics specified in the pre-registration. For probabilistic models: typically Brier score, Brier skill score, ECE, MCE, accuracy (auxiliary). For ranking-based tests: rank R, percentile, primary score. Each metric reported with a one-line interpretation alongside.

### 4.3 Per-bin / per-segment / per-subgroup table

The most detailed structured presentation. For calibration audits: per-bin reliability with Wilson CIs and pass/fail status. For ranking tests: top-N ranked entries with their scores. For weather verification: per-location or per-tier breakdown.

Format guidelines:

- Use markdown tables. Numerical columns right-aligned via `---:` separator.
- Probabilities to 4 decimal places.
- Percentages to 2 decimal places.
- Wilson intervals as `[lo, hi]` notation, same precision as their underlying metric.
- Fail/pass markers in last column, **fail** in bold where it stands out, `PASS` in uppercase where it doesn't.
- Excluded entries (e.g., bins with n < 30) shown explicitly with reason rather than dropped.

### 4.4 Reliability diagram (calibration audits only)

For audits whose primary subject is calibration of a probabilistic predictor, the per-bin table from 4.3 should be accompanied by a reliability diagram embedded in the result document. The diagram presents the same data in a visually scannable form and is the most direct communication of calibration drift to a reader who is not going to inspect every row of the table.

Standard convention:

- **X-axis:** predicted probability (0–1).
- **Y-axis:** observed frequency (0–1).
- **Dashed diagonal:** perfect calibration (y = x). Subdued gray.
- **One marker per bin** positioned at (mean_pred, observed_freq).
- **Marker area scales as sqrt(bin sample count)** — larger bins are visually weighted, smaller bins are visible but don't dominate.
- **Color encodes the bin's pass/fail status under the Wilson criterion** (Section 6.1):
  - Passing bins: deep navy.
  - Failing bins: burnt rust.
  - Excluded bins (n < `MIN_BIN_N`): subdued gray, semi-transparent.
- **Wilson 95% CI** shown as a vertical error bar on each non-excluded bin's observed frequency.
- **Title:** model name. **Subtitle:** revision · n · outcome.
- **Legend:** include only the marker categories actually present in the data, plus the perfect-calibration diagonal.

Generated using `tools/render_reliability_diagram.py`, which reads the case study's `calibration_summary.json` and writes both PNG and SVG. The diagram is committed alongside the JSON and CSV outputs as an additional artifact, not as part of the locked analysis-script output. PNG is embedded inline in the result document; SVG is committed for high-quality print or web use.

Embed in the result document directly below the per-bin table:

```markdown
![Reliability diagram](reliability_diagram.png)

*Reliability diagram for `<model>` on `<test data>`. Marker size proportional to bin sample count. Vertical bars are Wilson 95% confidence intervals on observed frequency. Passing bins shown in navy, failing in burnt rust, excluded in gray. Dashed line is perfect calibration.*
```

For audits whose primary subject is not calibration (e.g., ranking tests, weather verification), reliability diagrams may still be useful but are not required by the template.

---

## Section 5 — Diagnostic Reading (REQUIRED)

The most authored section. One to three subsections explaining what the per-bin or per-segment pattern means substantively. Required because the numbers in Section 4 don't speak for themselves; this is where the document explains what the result actually tells us.

Subsection conventions (use whichever apply):

- `### The [primary pattern observed]` — names the dominant feature of the result. E.g., "The model is bimodal and overconfident at both extremes" or "The chirp track produces no localized coherence elevation."
- `### [Specific finding worth highlighting]` — calls out a single observation that's particularly informative. E.g., "The bin-0 finding is the largest-volume issue."
- `### Comparison to prior tests` — when the current result connects meaningfully to prior tests in the same methodology family. (See Section 6 below for full guidance on this.)

Voice in this section: explanatory but not sales-y. The document is reporting findings, not arguing for a viewpoint. Avoid editorializing about the model's authors or about deployment decisions. Stick to "the data shows X; X means Y in operational terms."

---

## Section 6 — Cross-Test Consistency or Comparison (OPTIONAL)

Include this section when the current result connects meaningfully to one or more prior tests in the same methodology family. Skip when the test stands alone or when comparison would dilute the document's focus.

When included, a comparison table is the canonical format:

```markdown
## Comparison to [prior test identifier]

| Aspect | [Prior test] | [Current test] |
|---|---|---|
| Outcome tier | [...] | [...] |
| [Key metric 1] | [...] | [...] |
| [Key metric 2] | [...] | [...] |
| Distribution shape | [...] | [...] |
| Failure direction | [...] | [...] |

[1-2 paragraph methodological reflection on what the comparison reveals. The point of the section
is the pattern-or-divergence finding, not the table itself.]
```

This section earns its place when it produces a methodological insight (e.g., "the same protocol surfaces qualitatively different failure modes in different models"). If it would only restate "this also failed," omit.

---

## Section 7 — What This Test Does and Does Not Falsify (REQUIRED)

Two subsections in fixed order:

### 7.1 Falsified

A short list of what the test outcome falsifies. Stated narrowly. Each item references the specific pre-registered claim or implicit assumption.

Format:

```markdown
### Falsified

- The pre-registered [type of] claim: [verbatim or summarized claim from pre-reg]. [Fact pattern]
  at [specific values].
- [Additional explicit claim]: [details].
- The implicit assumption that [what was assumed]. [Verb phrase] under the registered protocol.
```

### 7.2 Not falsified

What the test does NOT say. Critical for institutional credibility — overclaiming on what a single result establishes is the most common failure mode of independent evaluation.

Format:

```markdown
### Not falsified

- The model's accuracy on [test data] ([specific number], [whether matches public claims]).
- The model's [other adjacent metric] (still positive at [value]).
- The model's fitness for [specific use case where this audit doesn't apply].
- The model's behavior on out-of-distribution data (not in scope for v1).
- Any claim that a [recalibration / reformulation] could not improve the outcome. Such a v2 test
  would be useful and is straightforward to design.
```

### 7.3 Cumulative implications (OPTIONAL — when applicable)

Include this third subsection only when the current result, taken with prior results in the same methodology family, produces a meta-finding that neither result alone would support. Examples: a pattern of repeated failures across implementations of a single conceptual claim; consistency across model architectures.

When the current result is the first or second of its class, this subsection is usually omitted.

---

## Section 8 — Implications for Users (OPTIONAL — typical for customer-facing audits)

Include for evaluations of models or systems that have identifiable downstream users. Omit for pure-research evaluations (gravitational waves) and for forecasting verifications without a single deployment context (severe weather verification of an unfinished model).

Format: a bulleted list addressing different user use cases, each item naming the use case and the specific operational impact derived from the result.

```markdown
If you are using [model/system] and your application:

- **[Use case 1]:** [What the audit says about this use case. Specific operational
  implications. What threshold adjustment or compensating measure is recommended.]
- **[Use case 2]:** [...].
- **[Use case 3]:** [...].

A v2 audit could test [specific extension]. That would be a separately pre-registered test.
```

This section is the single most operationally valuable part of a customer-facing deliverable. It's the "what do I do with this finding" answer. Resist the temptation to write it generically; tie each implication to specific numbers from Section 4.

---

## Section 9 — Implementation Observations (OPTIONAL — when methodologically noteworthy)

Include when the audit's execution surfaced something worth recording for transparency or for future engagements: a non-obvious decision rule application, an environment quirk, an operational gap between lock and run, a methodological choice that future v2 work might revise.

Numbered subsections for separability:

```markdown
### 9.1 [Observation 1]

[Single paragraph explaining what was observed and why it's worth recording.]

### 9.2 [Observation 2]

[As above.]
```

When the audit ran cleanly with no operationally interesting events, omit this section.

When inference environment is methodologically relevant (e.g., recording torch version drift between lock and run dates), include a small environment table:

```markdown
| Field | Value |
|---|---|
| Python | [version] |
| [Key library] | [version, source] |
| [Other] | [...] |
```

---

## Section 10 — Lock and Provenance (REQUIRED)

The legal/methodological closing section. Always a table mapping artifacts to their lock state. Always followed by a one-paragraph statement summarizing the methodology's binding sequence.

Format:

```markdown
| Item | Reference |
|---|---|
| Pre-registration document | [path] |
| Pre-registration / pipeline lock commit | git `[short-hash]` ([ISO date]) |
| Analysis script | [path] (frozen at `[short-hash]`) |
| Test data | [path] (SHA-256 `[16-char prefix]…`) |
| [Other relevant artifact] | [reference] |
| [Score vector commit] | [path] (committed at `[short-hash]`, [ISO date]) |
| This result document commit | (recorded after committing) |

Per pre-registration Section [N], the methodology was bound at lock commit `[short-hash]` before
any [inference / scoring / data inspection] was run; the [score vector / analysis output] was
committed at `[short-hash]` before this result document was drafted; the test outcome is published
irrespective of whether it is favorable to the [system / model / framework] being evaluated.
```

The "(recorded after committing)" placeholder for the result document's own commit hash is filled in via a small follow-up commit *after* the result document lands. This is the same lock-then-record pattern used for the pre-reg's status line.

---

## Section 11 — End-of-Document Signature (REQUIRED)

Always:

```markdown
---

*End of [Test Name] Outcome.*
```

Italics intentional. Marks the document as bound. No further content below this line.

---

## Voice and tone reference

A handful of specific patterns characterize the institutional voice. Use them.

**Use:**

- Third-person framing. *"This audit is conducted on..."*, *"The test ranked..."*, *"The methodology was bound at..."*. Avoid first-person plural ("we") except in operational descriptions.
- Specific numbers, not generalities. Say *"5 of 10 bins"*, not *"about half the bins"*. Say *"R = 52"*, not *"in the middle of the distribution"*.
- Falsified/not falsified framing rather than success/failure framing. The outcome is what it is; framing it as "the test failed" or "the test succeeded" makes the test sound like the subject. The system is the subject; the test is the instrument.
- Active voice for findings. *"The model produces..."* rather than *"It is found that the model..."*.
- Citation by section number when reachable. *"Per pre-registration Section 6.1..."* rather than *"As specified earlier..."*.

**Avoid:**

- Marketing voice. *"breakthrough"*, *"cutting-edge"*, *"revolutionary"*, *"powerful"*, *"robust"*. None of these belong in a result document.
- Hedging that softens the outcome. *"Results suggest..."*, *"It appears that..."*, *"The model may be..."*. The outcome is what was measured. Say it.
- Editorializing about model authors. *"The authors should consider..."*, *"This indicates the team..."*. The audit reports findings, not advice.
- Implications framed as universal claims. *"This means that probabilistic models cannot be trusted..."* — no, this means a specific finding about a specific model. Stay narrow.
- Comparisons to other audits not in the methodology family. The document is about this test; broader claims belong in standalone methodology papers, not in result documents.

---

## Numerical formatting reference

| Quantity type | Convention | Example |
|---|---|---|
| Probability | 4 decimals | `0.4422` |
| Percentage | 2 decimals + `%` | `91.06%` |
| Wilson CI | Match underlying precision, brackets | `[0.0181, 0.0269]` |
| Skill scores (BSS, R, etc.) | 4 decimals if probability-like, integer if rank-like | `+0.6664` / `R = 52` |
| Time (GPS, dates) | ISO date for calendar, native units for GPS | `2026-05-06`, `1126259446.4` |
| Counts | Integer with thousands separator if ≥ 1,000 | `5,000`, `872` |
| Hashes | 7-character short hash for git, 16-character prefix + ellipsis for SHA-256 | `dffd06a`, `647436da227d2231…` |
| Scientific notation | Use for values outside [10⁻⁴, 10⁴]; lowercase `e`, two decimals | `1.30e-44`, `2.50e+05` |

---

## When this template does NOT apply

The template is designed for **single-test result documents** in the pre-registered evaluation methodology. It does NOT apply to:

- **Methodology papers** or theoretical writeups (different format conventions; longer, more discursive).
- **Pre-registration documents** (different content; commitment to methodology, not reporting of outcomes).
- **Retrospective surveys** of multiple completed audits (different voice; explicitly comparative).
- **Customer scoping documents** (different audience; pre-engagement rather than post-engagement).
- **Marketing or sales material** (different purpose; the result documents under this template explicitly avoid that voice).

If a deliverable is being authored that doesn't match the "single-test, post-execution, locked outcome" pattern, use a different format conversation rather than forcing this template.

---

*End of Result Document Template.*