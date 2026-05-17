# AEPF v0.1 Working Draft — Evidence Preservation Format Specification

**Status of this document:** Public Working Draft v0.1. Issued for review and comment. A v1.0 final specification will be published following community input and revision.
**Publisher:** Avenridge Institute (working designation).
**License:** Released under CC-BY 4.0. Implementations and tooling MAY use any license.
**Date:** 2026-05-16.
**Summary:** Public draft specification for evidence preservation and attestation workflows associated with probabilistic evaluation artifacts.

---

## Abstract

This document specifies AEPF, a format for preserving cryptographic and procedural evidence that a probabilistic evaluation was conducted under a methodology committed in advance and not modified during or after execution. AEPF makes a single property externally verifiable: that the methodology, parameters, analysis code, and (where applicable) test data of an evaluation were fixed at a specific moment in time, and that no element of that fixed state was altered before the outcome was recorded.

AEPF does not specify the methodology to be evaluated, the metrics to be computed, the decision criteria to be applied, or the format of the outcome record. It specifies only how the artifacts of any such methodology are preserved in a way that supports third-party reproduction and verification.

AEPF is an evidence-preservation specification, not a certification framework.

---
## How to cite this document

When citing the AEPF v0.1 Working Draft, use the following form.

**Plain text:**

` ` `
Dixon, E. (2026). AEPF v0.1 Working Draft — Evidence Preservation Format
Specification. Avenridge Institute (working designation). Commit 65c8035.
https://github.com/earldixon310-max/dynametrix/blob/65c8035/docs/standards/AEPF_v0.1_WORKING_DRAFT.md
` ` `

**BibTeX:**

` ` `bibtex
@techreport{aepf_v0_1_2026,
  title       = {{AEPF} v0.1 Working Draft --- Evidence Preservation Format Specification},
  author      = {Dixon, Earl},
  institution = {Avenridge Institute (working designation)},
  year        = {2026},
  month       = may,
  url         = {https://github.com/earldixon310-max/dynametrix/blob/65c8035/docs/standards/AEPF_v0.1_WORKING_DRAFT.md},
  note        = {Commit 65c8035}
}
` ` `

The commit hash `65c8035` anchors this version of the specification. The citation URL resolves to the same commit content for any reader at any future time, consistent with the version-binding discipline in §11. When a DOI is later minted for this version (e.g., via Zenodo), the canonical citation form will lead with the DOI; the commit hash will remain the underlying binding.

---

## 1. Introduction

### 1.1 Motivation

Evaluations of probabilistic models — calibration audits, blind detection tests, predictive-skill assessments — produce results whose credibility depends in large part on whether the methodology was specified before, and unchanged during, the production of those results. Post-hoc methodology revision, parameter tuning informed by partial results, and selective publication of favorable outcomes are documented failure modes in evaluation work. They are also difficult for a third party to detect from the outcome record alone.

AEPF addresses this by specifying a format for evidence preservation that allows a third party to verify, cryptographically and procedurally, that the methodology and inputs of an evaluation were bound to a specific historical state, and that the outputs were produced by executing that bound state. The format does not require the third party to trust the evaluator; it requires only that the third party trust standard cryptographic primitives and a public version-control history.

### 1.2 Scope

AEPF SPECIFIES:

- The set of artifacts that MUST be present in an evidence bundle.
- The procedural ordering of those artifacts' commits.
- The cryptographic primitives used to attest to artifacts not committed directly.
- The verification procedure a third party performs to validate an evidence bundle.

AEPF DOES NOT SPECIFY:

- The methodology being evaluated. Calibration, detection, forecasting, fairness, robustness, and other evaluation classes are all in scope of AEPF as a format but out of scope of this specification.
- The metrics, statistical procedures, or decision criteria. These are documented in the methodology being evaluated, not in this format.
- The format of the outcome record, beyond requiring its existence as a committed artifact.
- The infrastructure for executing the evaluation. Any compute environment that can produce reproducible outputs from the locked inputs is acceptable.

### 1.3 Conformance terminology

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL in this document are to be interpreted as described in BCP 14 (RFC 2119, RFC 8174) when, and only when, they appear in all capitals.

---

## 2. Terminology

**Evidence bundle.** A version-controlled repository (typically a git repository) containing all artifacts required by this specification.

**Lock commit.** A single commit in the evidence bundle's version history that simultaneously introduces the pre-registration document, the analysis code, and (where applicable) the test data hash and any sealed-artifact hashes. The lock commit defines the moment at which the methodology and inputs become bound.

**Sealed artifact.** An artifact whose contents MUST NOT be visible to the evaluator during execution (e.g., the mapping from blinded IDs to true labels in a blind detection test). AEPF specifies how the cryptographic fingerprint of a sealed artifact is committed at the lock commit while the artifact itself is held in escrow until unbinding.

**Unbinding.** The act, performed after all outputs have been committed, of revealing previously sealed artifacts and verifying that they match the hashes committed at the lock commit.

**Outcome Record.** A document, committed to the evidence bundle, that records the outcome of the evaluation under the decision criteria specified in the pre-registration. The outcome record is bound at its commit and MUST NOT be modified thereafter.

**Verifier.** Any third party performing the AEPF verification procedure (Section 6) against an evidence bundle.

---

## 3. Required Artifacts

### 3.1 The pre-registration document

The evidence bundle MUST contain a pre-registration document committed at the lock commit. The pre-registration document MUST specify, at minimum:

(a) The system or model under evaluation, identified to a precision sufficient for unambiguous reproduction (e.g., model name plus revision hash, dataset name plus version, configuration parameters).

(b) The test data to be used, identified by reference (Section 3.4).

(c) The analysis methodology, including all metrics, statistical procedures, and decision criteria.

(d) The conditions under which each possible outcome would be recorded.

(e) The provenance of any sealed artifacts (Section 3.5), including the cryptographic fingerprint(s) committed at the lock commit.

The pre-registration document MUST be in a format that preserves under version control (typically Markdown, plain text, or PDF).

### 3.2 The analysis code

The evidence bundle MUST contain the complete analysis code committed at the lock commit. The analysis code MUST be sufficient, together with the test data and any pinned dependencies, to reproduce the outputs of the evaluation.

The analysis code MUST refer to the test data via a stable identifier that includes a cryptographic fingerprint of the data, OR via a path within the evidence bundle if the data is committed directly. At runtime, the analysis code MUST verify the test data's fingerprint matches the value committed at the lock commit, and MUST refuse to proceed if the verification fails.

The analysis code's external dependencies (libraries, models, datasets fetched at runtime) MUST be pinned to specific versions or revisions. Where the dependency itself supports cryptographic versioning (such as git commit hashes, package lockfiles, or container digests), the pinned identifier SHOULD be the cryptographic form.

### 3.3 The requirements file

The evidence bundle SHOULD contain a requirements file specifying the runtime environment, including library versions and any other reproducibility-relevant configuration. The requirements file SHOULD be pinned to specific versions.

### 3.4 The test data

Test data MUST be either:

(a) Committed directly to the evidence bundle, in which case its presence in the lock commit constitutes its preservation; OR

(b) Made available at a public, persistent reference, with its SHA-256 fingerprint committed at the lock commit and verified by the analysis code at runtime.

(b) is REQUIRED for test data that is too large to commit directly, or that is subject to terms of use that prohibit redistribution. (a) is RECOMMENDED for test data that is small (e.g., < 100 MB) and freely redistributable.

When the test data is fetched from an external source at runtime, the source URL or identifier MUST be specified in the pre-registration document.

### 3.5 Sealed artifacts (when applicable)

For evaluations that involve concealed information whose later revelation is required for outcome interpretation (most commonly, blind tests), AEPF specifies:

**At the lock commit:**

- The SHA-256 fingerprint of each sealed artifact MUST be committed to the evidence bundle as a separate plain-text file. The file format MUST be the lowercase hexadecimal representation of the SHA-256 digest, followed by a newline.

- The artifact itself MUST NOT be committed at the lock commit.

- The pre-registration document MUST describe where the sealed artifact is held during the binding period and the conditions under which it may be revealed.

**During the binding period:**

- The sealed artifact MUST be held in a location that the evaluator commits not to access, modify, or destroy.

- A practical implementation involves storing the sealed artifact in a directory outside the evidence bundle's working tree, with the file path documented in the pre-registration.

**At unbinding:**

- The sealed artifact MAY be committed to the evidence bundle.

- A verifier MUST recompute the SHA-256 fingerprint of the revealed artifact and verify that it matches the fingerprint committed at the lock commit. Any mismatch invalidates the evidence bundle's claim to preservation.

### 3.6 The output artifacts

After execution, the evidence bundle MUST contain the output artifacts produced by the analysis code. The output artifacts MUST be committed at a commit prior to the outcome record commit.

Output artifacts SHOULD include, at minimum:

- The per-example or per-record predictions produced during evaluation.
- The aggregate metrics computed by the analysis code.
- A machine-readable summary suitable for later analysis (e.g., JSON, CSV).

The output artifacts MAY be regenerated by re-running the analysis code against the locked inputs; this regeneration is the primary form of third-party verification (Section 6.4).

### 3.7 The outcome record

The evidence bundle MUST contain a outcome record committed after the output artifacts. The outcome record records the outcome of the evaluation under the decision criteria specified in the pre-registration document.

The outcome record MUST cite:

- The lock commit's cryptographic identifier (typically the git commit hash).
- The output artifacts' commit identifier.
- The SHA-256 fingerprints of any sealed artifacts, both as committed at the lock commit and as verified at unbinding.

The outcome record MUST NOT be modified after its commit. Corrections, addenda, or supplementary analysis MUST be published as new commits or new documents that reference (but do not replace) the original outcome record.

---

## 4. The Lock Commit

### 4.1 Atomicity

The lock commit MUST introduce, in a single commit:

- The pre-registration document (Section 3.1).
- The analysis code (Section 3.2).
- The test data, if committed directly (Section 3.4(a)).
- The SHA-256 fingerprint files for any sealed artifacts (Section 3.5).
- The SHA-256 fingerprint file for the test data, if held externally (Section 3.4(b)).

The atomicity of the lock commit is the central guarantee AEPF provides: all elements of the methodology become bound simultaneously, and any one of them changing thereafter is detectable by inspection of the commit history.

### 4.2 Status convention

The pre-registration document SHOULD include a status field that is updated immediately following the lock commit to reference the lock commit's identifier. A recommended convention:

Before the lock commit:
```
Status: Draft pending lock commit.
```

After the lock commit, in a follow-up commit:
```
Status: Locked at commit <hash>.
```

The follow-up commit MAY modify the status line and MUST NOT modify any other field in the pre-registration.

### 4.3 Identifying the lock commit

The lock commit is identified by its cryptographic hash in the underlying version-control system. For git, this is a 40-character SHA-1 hash (or 64-character SHA-256 hash in newer git installations). The lock commit's hash MUST be cited in the outcome record.

---

## 5. Ordering and Constraints

AEPF requires the following ordering of commits:

```
[ ... prior history ... ]
    ↓
LOCK COMMIT  ──  pre-registration, analysis code, test data (or hash), sealed-artifact hashes
    ↓
[ optional: status-update commit; small build fixes that do not alter
  methodology or analysis logic, each in a separate commit and disclosed ]
    ↓
OUTPUT COMMIT  ──  output artifacts produced by analysis code
    ↓
OUTCOME COMMIT  ──  outcome record
    ↓
[ optional: unbinding commit revealing sealed artifacts ]
```

The following are explicitly required or permitted:

(a) The output commit MUST occur after the lock commit and before the outcome commit.

(b) Multiple output commits MAY occur if execution produces artifacts incrementally; in this case, the outcome commit MUST occur after the last output commit.

(c) Between the lock commit and the output commit, the evidence bundle MAY receive commits that do not modify the methodology or analysis logic. Examples: documentation typo fixes, build configuration changes, dependency-installation issue workarounds. Any such commit MUST be disclosed in the outcome record's implementation observations.

(d) The outcome record MUST NOT modify the pre-registration, the analysis code, or the test data.

(e) Unbinding commits revealing sealed artifacts MUST occur after the outcome commit.

The following are explicitly prohibited:

(a) Modifying the pre-registration document, the analysis code, or the test data fingerprint after the lock commit.

(b) Force-pushing or rewriting git history of the evidence bundle. The commit hashes cited in the outcome record MUST resolve to the same content for any verifier at any future time.

(c) Committing or revealing a sealed artifact before all output artifacts have been committed.

(d) Modifying the outcome record after its commit.

---

## 6. Verification Procedure

A verifier confirms an AEPF-compliant evidence bundle by performing the following procedure. All steps SHOULD be automatable.

### 6.1 Clone the evidence bundle

The verifier obtains the complete history of the evidence bundle from its publication location.

### 6.2 Identify the lock commit

From the outcome record, the verifier obtains the cited lock commit identifier and verifies its existence in the evidence bundle's history.

### 6.3 Verify lock commit contents

The verifier inspects the lock commit and confirms it introduces the artifacts required by Section 3 — pre-registration, analysis code, test data or test data fingerprint, sealed-artifact fingerprints if applicable.

### 6.4 Re-execute the analysis

The verifier checks out the lock commit and runs the analysis code in an environment matching the requirements file. The analysis code SHOULD verify the test data fingerprint at runtime; the verifier confirms this verification passes.

The verifier records the outputs produced by re-execution and compares them to the output artifacts committed in the output commit. Numerical equivalence within float-precision tolerances constitutes a successful re-execution.

Re-execution failure with a clear cause (e.g., a dependency that has since been removed from its source) does not invalidate the evidence bundle if the cause is documented. Re-execution failure that produces numerically different outputs from the same inputs DOES invalidate the bundle.

### 6.5 Verify sealed artifacts (if applicable)

For each sealed artifact, the verifier:

(a) Obtains the revealed artifact (committed after unbinding, or received from the evaluator).

(b) Computes the SHA-256 fingerprint of the revealed artifact.

(c) Compares the computed fingerprint to the fingerprint committed at the lock commit.

A mismatch invalidates the evidence bundle's claim to preservation of that sealed artifact.

### 6.6 Verify outcome record binding

The verifier confirms that the outcome record has not been modified after its commit, by checking that no subsequent commit in the evidence bundle modifies the outcome record file.

---

## 7. Operational Considerations

### 7.1 Version control system

This specification is written assuming git as the underlying version-control system, because git is in widest use and because git commit hashes are cryptographic. AEPF is compatible in principle with any version-control system that provides cryptographic content-addressable commits (such as Mercurial with content hash extensions).

Implementations using git SHOULD use SHA-256 commit hashes where the git installation supports it, for forward-compatibility with cryptographic standards. SHA-1 commit hashes remain acceptable for the v0.x working-draft period and for v1.0 of this specification.

### 7.2 Hosting

The evidence bundle SHOULD be published at a persistent, publicly accessible location (e.g., a public git hosting service). For evaluations involving confidential information that cannot be fully published, the evidence bundle MAY be hosted privately, with the cryptographic identifiers (commit hashes, SHA-256 fingerprints) published in a public abstract that allows verification by parties who later obtain access to the private bundle.

### 7.3 Tooling

Reference tooling for producing and verifying AEPF-compliant evidence bundles is OPTIONAL but RECOMMENDED. Tooling SHOULD at minimum support:

- Computing SHA-256 fingerprints of test data and sealed artifacts.
- Verifying that the lock commit contains the required artifacts.
- Re-executing the analysis code against the locked inputs.
- Comparing re-execution outputs against committed outputs.

### 7.4 Long-term preservation

AEPF preserves an evidence bundle's verifiability as long as:

- The version-control hosting remains accessible.
- The cryptographic primitives used (SHA-256, the version-control commit hash) are not compromised.
- Externally referenced test data sources remain accessible OR the data is committed directly.

Evaluators SHOULD consider archiving evidence bundles to permanent-archive services (e.g., academic institutional repositories, the Internet Archive's Software Heritage Archive) for evaluations whose long-term verifiability matters. Long-term preservation mechanisms SHOULD preserve both the repository contents and the complete commit history, as commit history integrity is essential to AEPF's verification procedure.

---

## 8. Security Considerations

### 8.1 Trust model

AEPF requires the verifier to trust:

- The cryptographic strength of SHA-256 and the underlying version-control commit hash.
- The integrity of the version-control hosting (specifically, that commit hashes cited in the outcome record resolve to the same content for all parties).

AEPF does NOT require the verifier to trust:

- The evaluator's good faith or competence.
- Any party other than the version-control hosting provider during the verification procedure.

### 8.2 Solo-evaluator integrity

When the evaluator and the methodology custodian are the same party (a common case for self-audits and small operations), the integrity of sealed artifacts depends on the evaluator's discipline not to access the sealed artifact during the binding period. AEPF mitigates this by requiring the SHA-256 fingerprint commitment at the lock commit, which makes any post-hoc modification of the sealed artifact detectable but does not prevent pre-execution inspection.

For evaluations where this risk is material, the SHOULD provision is: place the sealed artifact in the custody of a third party during the binding period. Where this is impractical, AEPF compliance constitutes a documented best-effort with the limitation explicitly disclosed.

### 8.3 What AEPF does not prevent

AEPF prevents post-hoc modification of bound artifacts. It does NOT prevent:

- The evaluator choosing methodology parameters informed by prior, unbound exploration of the data.
- The evaluator selecting which of multiple completed evaluations to publish (the "file drawer problem" — addressed by pre-registration discipline, not by AEPF).
- The evaluator misrepresenting the test data's relationship to the underlying system (e.g., claiming data is held-out when it was used during model training).

These are concerns of pre-registration discipline and methodology design, addressed separately.

---

## 9. What AEPF Does Not Specify

For clarity, AEPF as a format does NOT include or require:

- A specific evaluation methodology.
- Any particular metrics, decision criteria, or statistical procedures.
- A specific format for the outcome record, beyond the requirement that it exist and not be modified after commit.
- A specific format for the analysis code, beyond the requirement that it be self-contained and runtime-verify the test data fingerprint.
- A specific dependency-management tool.
- A specific publishing or hosting platform.

These choices are made by the evaluator according to the methodology being evaluated. AEPF specifies only the evidence preservation around those choices.

---

## 10. Compliance Statement

An evidence bundle is AEPF-compliant if and only if:

(a) It contains all artifacts required by Section 3.
(b) The artifacts are introduced in commits ordered as specified in Section 5.
(c) The lock commit is atomic per Section 4.1.
(d) Sealed-artifact fingerprints (where applicable) are committed at the lock commit per Section 3.5.
(e) The verification procedure (Section 6) succeeds when performed by a verifier with access to the evidence bundle.

Evaluators MAY include the following statement in outcome records to assert AEPF working-draft conformance:

> *"This evaluation's evidence preservation conforms to the AEPF v0.1 Working Draft."*

Evaluators MUST NOT make this statement unless all conditions above are met. Misuse of the conformance statement may be challenged by any verifier following the procedure in Section 6.

Following the publication of AEPF v1.0, conforming evaluations SHOULD update the statement to cite the published version (e.g., *"conforms to AEPF v1.0"*) in subsequent outcome records. Statements asserting conformance to the v0.1 Working Draft remain valid in outcome records that were bound during the working-draft period.

---

## 11. Versioning and Revision

This document is the AEPF v0.1 Working Draft. It is issued for public review and comment.

Revisions during the working-draft period MAY make substantive changes to required artifacts, ordering, or the verification procedure. Such revisions will be published as incremented draft versions (v0.2, v0.3, etc.) with a record of the changes from the prior draft.

Following the working-draft period, a v1.0 final specification will be published. From v1.0 onward, the version is bound at publication and does not change: future revisions (v1.1, v2.0, etc.) will be published as separate documents with their own version identifiers. Evidence bundles produced under a published version remain compliant with that version indefinitely; revisions do not retroactively apply.

Substantive revisions to a published version (changing required artifacts, the ordering, or the verification procedure) constitute a major version increment. Clarifications, formatting corrections, and example additions constitute a minor version increment.

Evaluators producing evidence bundles during the v0.x working-draft period SHOULD cite the specific draft version their bundle conforms to (e.g., "AEPF v0.1 Working Draft") in the outcome record and in any external attestation.

---

## 12. Acknowledgments

The structure of this specification draws on conventions established by the Internet Engineering Task Force (RFC series), the National Institute of Standards and Technology (FIPS publications), and the Open Science Framework's pre-registration discipline. AEPF formalizes the cryptographic-lock pattern empirically developed during the pre-registered evaluations published at the publisher's reference repository, 2026.

---

## 13. References

### 13.1 Normative

[FIPS 180-4] National Institute of Standards and Technology, "Secure Hash Standard (SHS)," FIPS PUB 180-4, August 2015.

[RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels," BCP 14, RFC 2119, March 1997.

[RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words," BCP 14, RFC 8174, May 2017.

### 13.2 Informative

[GIT] "git — distributed version-control system," https://git-scm.com/.

[OSF] Center for Open Science, "Pre-registration," https://www.cos.io/initiatives/prereg.

---

## Appendix A — Example Evidence Bundle Layout (non-normative)

A minimal AEPF-compliant evidence bundle has the following structure. This layout is illustrative; AEPF does not require any specific directory naming convention.

```
example_bundle/
├── preregistration.md          # §3.1 — pre-registration document
├── requirements.txt            # §3.3 — pinned runtime environment
├── analysis/                   # §3.2 — analysis code
│   └── run.py
├── hashes/                     # §3.4(b), §3.5 — SHA-256 fingerprints
│   ├── test_data.sha256
│   └── sealed_keys.sha256
├── outputs/                    # §3.6 — output artifacts
│   ├── predictions.csv
│   └── metrics.json
└── outcome.md                  # §3.7 — outcome record
```

Commit ordering for this example bundle:

- **Lock commit** introduces `preregistration.md`, `requirements.txt`, `analysis/`, and `hashes/` together.
- **Output commit** introduces `outputs/` after analysis execution.
- **Outcome commit** introduces `outcome.md` after the output commit.
- **Unbinding commit**, if applicable, reveals sealed artifacts (e.g., adds `sealed_keys.json` under a new `sealed/` directory) after the outcome commit and verifies against the corresponding hash file from the lock commit.

---

*End of AEPF v0.1 Working Draft.*