# OVP — Design History (out-of-artifact)

This file holds the design narrative and editorial history of the Observable Validation Protocol (OVP) spec. It is kept **separate from the spec itself** on purpose: the spec (`OVP_v0.1_OBSERVABLE_VALIDATION_PROTOCOL.md`) must be cold-readable per its own §7/§9 — handed to an independent reader as a stranger would read it, with no design conversation, lineage notes, or rationale supplied out of band. Design narrative embedded *inside* the spec would defeat that gate (this was itself a cold-reader finding). So the "why" lives here; the spec carries only the "what."

## Lineage

OVP abstracts a question the program kept re-deriving informally:
- **RC_v1** — does graph topology `F` add structure beyond pairwise consistency `C`? (measure: a pair-separation rate)
- **CT-v1** — does a novelty term add structure beyond a baseline formula? (measure: an ablation correlation)
- **Dynametrix-HRRR gate** — is a new predictor redundant with an existing one? (measure: an independence correlation)

Each used a *different* operational measure, which is precisely why they are **lineage, not OVP studies**: they motivate OVP and the ledger begins empty (spec §9). The deeper lesson carried forward is CALIB_POSCONTROL's: the discriminating instrument must itself be validated on synthetic ground truth before its verdicts on real candidates are trusted.

The question OVP operationalizes — whether a candidate quantity earns the status of *validated observable* within a given evidence base — is old (Reichenbach, Quine, Cartwright). What is new is the disciplined, falsifiable procedure.

## Revision history

**Draft → working draft (the one-measure / four-verdict episode).** An early draft pinned a single measure (HDG) but declared four verdicts. The first independent cold-reader pass found this structurally impossible: a redundant candidate and a noise candidate both sit at HDG ≈ 0, so one scalar cannot separate them. Two resolutions were weighed:
- *Option 1* — pin a second statistic (baseline-recoverability) and keep four verdicts. Rejected: a second pinned statistic is a second degree of freedom even when pinned, and it would make a three-statistic v0.3 defensible by the same logic. The version mechanism exists to carry that expansion *across* versions, not within one.
- *Option 2* (adopted) — hold strict one-measure-per-version; v0.1 returns **three** verdicts (Validated, Not-Validated, Inconclusive), with the redundant-vs-noise distinction deferred to **v0.2** (= v0.1 + a pinned baseline-recoverability statistic + the four-verdict structure). The cold pass thereby handed v0.2 its design seed.

Control-failure was reclassified from a fourth verdict to a run-invalidating documented condition (you cannot trust any verdict from an instrument that failed its own setup check).

**Second cold-reader pass (assembled-draft read).** A fresh isolated reviewer, given the spec file and nothing else, returned four blocking findings, all accepted and fixed in the spec:
1. *Identity contradiction* — "one measure per version" vs "metric differs across studies" were never reconciled. Fixed by separating the version-fixed **measure form** (HDG) from the study-pinned **instantiation** (concrete metric, estimator/function class, split protocol, cut points), and noting that instantiating the same measure across substrates is not the same as pinning a second measure.
2. *τ_lo unanchored* — "D ≈ 0 → Not-Validated" only holds if τ_lo > 0, which was unstated. Fixed by pinning τ_lo strictly positive.
3. *Self-defeating cold-reader gate* — the artifact contained design narrative (the Drafting note + inline "(review …)" annotations) that the gate forbids the cold reader from seeing. Fixed by moving all design narrative to this file and stripping the inline scaffolding.
4. *By-construction vs 90/100* — a random noise arm cannot be guaranteed below τ_lo every replication. Fixed by pinning the arm's D-*distribution* (expected value + margin) on the correct side; the ≥-of-R bar is the allowance for sampling scatter.

Smaller fixes from the same pass: Arm 3 reworded from "certifies" to "exercises/witnesses" the Inconclusive verdict (a non-gated arm certifies nothing); `R` defined (replications per study; OVP_POSCONTROL_v1 pins R = 100); split-protocol contents specified; and §6's overloaded word "usable" split into a three-rung ladder — **self-validated** (positive control passes) → **operational** (self-validated + ≥3 real ledger verdicts) → **community-validated** (operational + ≥1 externally-authored candidate).

## Standing discipline

The spec is **not locked**. Per §7/§9, locking to v0.1 requires an independent cold-reader pass on the spec body alone, with any divergence recorded. The spec's author — including the AI collaborator that drafted and revised it — is the most context-saturated reader and cannot be that pass. Each revision above that changed structure earned a fresh cold read; this file records that history so the spec need not.
