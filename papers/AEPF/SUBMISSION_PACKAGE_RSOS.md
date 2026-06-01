# RSOS Submission Package — AEPF paper

**Target:** *Royal Society Open Science* (RSOS), research article.
**Submission system:** ScholarOne Manuscripts — https://royalsocietypublishing.org/rsos/pages/submit
**Initial-submission format:** format-free. Upload the compiled `AEPF.pdf` as the main document. Source files (`AEPF.tex`, `references.bib`/`.bbl`) are required only at final revision.
**Review model:** single-anonymized, **open peer review mandatory** (referee reports + author responses published with the paper).

> **Items that still need you:** your **ORCID iD** (§2). The Zenodo DOI (§6.3) and the AI-use (§6.2) and competing-interests (§6.4) statements are now finalized. Nothing else is blocking.

---

## 1. Title

**The Avenridge Evaluation and Publication Framework: A Framework for Locked Evaluation, Calibration Assessment, and Reproducible Verification in Evaluation-Intensive Computational Domains**

*(Exact title as set in `AEPF.tex` and the compiled PDF — enter verbatim in ScholarOne so the form matches the manuscript.)*

## 2. Author and affiliation

- **Earl Dixon**, Avenridge Institute. Sole author and corresponding author.
- ORCID: `0009-0000-7197-1080`

## 3. Abstract (≤200 words — RSOS limit; matches the manuscript)

> We introduce the Avenridge Evaluation and Publication Framework (AEPF), an operationalized methodology for evaluation-intensive computational domains. AEPF integrates established disciplines—clinical-trial pre-registration, high-energy-physics blind analysis, machine-learning calibration assessment, and open-science null reporting—into a single workflow with concrete operational consequences: cryptographic anchoring of methodology to a public commit chain, calibration assessment as a standing pre-registration requirement, null-result publication parity, constrained-interpretation reporting, and a pre-specification viability gate that retires structurally over-determined studies. We illustrate the framework with four case studies—spanning cosmological residual analysis, transformer calibration auditing, framing-robustness testing of an open-weight language model, and a viability-gate disposition—together with a methods-level validation of the calibration-audit instrument against synthetic ground truth. The instrument validation establishes that the audit is sound: zero false-acceptance of broken calibration across the tested miscalibration families, so that a null verdict reported under AEPF reflects the evaluated system rather than an artifact of the tool. The novelty claimed is in the integration and artifact-level operationalization, not in any individual component.

## 4. Keywords (RSOS wants 3–10)

pre-registration; research reproducibility; calibration assessment; null-result publication; blind analysis; research integrity; open science; evaluation methodology

---

## 5. Cover letter (paste into ScholarOne / upload)

> Dear Editors,
>
> I am pleased to submit "The Avenridge Evaluation and Publication Framework: An Operationalized, Cryptographically-Anchored Methodology for Pre-Registered Evaluation with Null-Result Parity" for consideration as a research article in *Royal Society Open Science*.
>
> The paper introduces AEPF, a methodology that integrates four established disciplines—clinical-trial pre-registration, high-energy-physics blind analysis, machine-learning calibration assessment, and open-science null reporting—into a single, artifact-level operational workflow in which a study's methodology, analysis code, and data fingerprints are bound to a public git commit chain before any outcome is observed. The contribution is not any individual component but their integration into a reproducible, cryptographically-anchored procedure, illustrated across four substantively different domains (cosmology, transformer calibration auditing, open-weight language-model evaluation, and a pre-specification viability gate) and supplemented by a methods-level validation showing the calibration-audit instrument is sound against synthetic ground truth.
>
> The work is an unusually literal instance of the open-science principles *Royal Society Open Science* champions: every pre-registration, analysis script, materialization manifest, and result document is publicly available, content-hashed, and lock-tagged, so that any reader can re-execute each study against exactly the inputs evaluated. The paper practices the discipline it proposes. I therefore believe it is well suited to a journal committed to transparency and reproducibility, and I welcome the journal's open peer-review model.
>
> I confirm that this manuscript is original, is not under consideration elsewhere, and has not been published previously. I am the sole author. I have disclosed my use of AI-assisted tools and my competing interests in the statements provided. As a self-funded independent researcher with no institutional Read-&-Publish agreement, I intend to request consideration under the journal's discretionary article-processing-charge waiver should the paper be accepted.
>
> Thank you for considering this submission.
>
> Sincerely,
> Earl Dixon
> Avenridge Institute

---

## 6. End-section statements (entered into the ScholarOne form — NOT in the manuscript)

### 6.1 Ethics
> This research did not involve human participants, human tissue, or animals. No ethical approval was required. All evaluated models and datasets are publicly available; the language-model and cosmological case studies use published, licensed public artifacts only.

### 6.2 Use of AI and AI-assisted technologies  *(finalized by the author)*
> Large language model tools (Anthropic's Claude) were used substantially during this work: for drafting and editing the manuscript, for drafting and reviewing analysis code, for critique and exploratory discussion, and as a participant in the cross-model review process that the manuscript itself describes as a methodological component (and whose limitations it documents). All research questions, experimental designs, hypotheses, interpretations, conclusions, and final manuscript content were determined, reviewed, and approved by the author, who assumes full responsibility for the work. No AI system is listed as an author.

### 6.3 Data, code and materials
> All pre-registrations, analysis scripts, materialization manifests, and result documents supporting this article are publicly available in the project repository at https://github.com/earldixon310-max/dynametrix, with each study bound to a signed git lock tag (e.g. `rc-v1-lock`, `rc-v1-calibrated`, `rc-v1-result`) recording the exact frozen state evaluated. A permanently archived snapshot is deposited at Zenodo under DOI https://doi.org/10.5281/zenodo.20490326 (concept DOI, resolving to the latest version; the specific v1.0 snapshot archived for this article is https://doi.org/10.5281/zenodo.20490328). No data are withheld; nothing is "available from the author on request."
>
> *(For the reference list, RSOS requires the dataset to be cited: e.g. "Dixon E. 2026 Dynametrix: Pre-registered Evaluation Repository (v1.0). Zenodo. https://doi.org/10.5281/zenodo.20490328")*

### 6.4 Competing interests  *(finalized by the author)*
> The author developed the AEPF methodology described in this work, and also developed the Dynametrix forecasting system that is itself evaluated in one of the case studies (the Dynametrix-HRRR viability gate). The author may explore future research, consulting, or evaluation applications related to the AEPF methodology. No commercial services based on AEPF are currently offered in connection with this manuscript, and no revenue has been derived from the results reported here. The author declares no other competing interests.

### 6.5 Authors' contributions (CRediT)
> **Earl Dixon:** Conceptualization, Methodology, Software, Formal analysis, Investigation, Data curation, Visualization, Writing – original draft, Writing – review & editing, Project administration. (Sole author.)

### 6.6 Funding
> This research received no external funding. The work was conducted by the author without grant support.

---

## 7. APC discretionary waiver request (submit per the journal's waiver process if accepted; the request is assessed independently of peer review)

> I request consideration for a discretionary article-processing-charge waiver. I am an independent, self-funded researcher with no external grant support and no institutional affiliation participating in a Royal Society Read-&-Publish agreement, and I lack funds to cover the standard APC. I would be grateful for a full or partial waiver so that this work can be published open access. I understand this request is assessed independently of the editorial decision on the manuscript.

---

## 8. Media summary (≤100 words — requested at final-files stage)

> Scientific results are easy to misread when the methods behind them can change after the data are seen. This paper presents a practical workflow that locks an evaluation's methods, code and data to a public, tamper-evident record *before* any result is known, treats "no effect" findings with the same rigor as positive ones, and requires calibration—whether stated probabilities are trustworthy—to be checked routinely. It is demonstrated across four fields and includes a test confirming the calibration check itself works correctly. Everything needed to reproduce the studies is publicly archived. The aim is verifiable, honestly reported evaluation.

---

## 9. Pre-submission checklist

- [ ] **`[YOU]` Register/confirm ORCID** and put it in §2.
- [ ] **`[YOU]` Archive the repo to Zenodo for a citable DOI.** Link the GitHub repo to Zenodo, cut a release at the current state (commit `002f152` / the `rc-v1-*` tags), let Zenodo mint a DOI, and paste it into §6.3. (GitHub satisfies "public repository," but Zenodo gives the permanent, versioned DOI the data policy prefers and lets the dataset be cited in the reference list, which RSOS requires.)
- [x] §6.2 (AI use) and §6.4 (competing interests) — finalized and confirmed by the author.
- [x] Zenodo DOI minted and recorded in §6.3 (concept `10.5281/zenodo.20490326`).
- [ ] Upload `AEPF.pdf` as the main document (format-free initial submission — no reformatting needed now).
- [ ] Enter title, ≤200-word abstract (§3), and keywords (§4) in the form.
- [ ] Enter the six end-section statements (§6) in the form.
- [ ] Add the cover letter (§5).
- [ ] Confirm sole authorship; no co-author ORCIDs needed.
- [ ] After acceptance only: submit the APC waiver request (§7); provide source files (`.tex` + `.bbl`); provide the ≤100-word media summary (§8); supply figures as separate files if any are added.

### Deferred to revision/copyediting (not blocking initial submission)
- British English spelling (the manuscript currently uses US spelling; RSOS converts at copyediting, but I can do a pass if you want it clean up front).
- RSOS uses the *Open Biology* reference style file at final revision; the current `unsrtnat` numbered-by-appearance style already matches Vancouver structure, so this is a final-stage swap, not a rewrite.

---

*Prepared as a submission aid. The manuscript itself (`AEPF.pdf`) is the authoritative artifact; this package supplies the surrounding materials ScholarOne asks for.*
