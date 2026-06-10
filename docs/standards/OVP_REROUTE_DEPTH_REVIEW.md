# OVP Re-route-Depth Taxonomy — Review Thread (redesign-or-retire)

**Status:** split out of `OVP_v0.2_TEMPLATE_HARDENING_DRAFT.md` at that draft's cold-pass-1. This is an OVP-internal **review-discipline** question (how many cold passes a narrow fold needs before lock) — *not* a judge/lock mechanism (those are H1/T-2 in the hardening draft) and *not* RTVP. It is held separately because it **relaxes a safety invariant** (two-independent-pass coverage of a fold's delta) and therefore, by the program's own "program-evolution gets the same discipline as artifacts" principle, deserves more scrutiny than the structure-*adding* guards — its own adversarial pass, framed **redesign-or-retire**, not a presumption that a middle tier gets built.

---

## 1. The question (the original seed)

Reviews keep producing: *cold pass finds a substantive-but-non-gating issue → fold → full warm + two-cold re-route.* The full re-route is the conservative default and was applied as written every time (verdict-#3 ancestry fold; CP2-N1). **Open question:** is there a *principled* middle tier — cheaper than the full re-route — for folds **substantive in meaning but narrow in surface**? **Hard constraint:** any such tier must NOT become "clear-modulo by another name"; the truncation-NB1 bar (*the locked artifact is exactly the one that was read*) cannot erode, and the fix-author can never self-certify "narrow enough."

## 2. The proposed taxonomy (as drafted, now under review)

- **Tier C — full re-route (warm + two cold).** Default for SUBSTANTIVE folds (gating rule / pinned constant / seed / estimator / computation / measurement / *meaning* of a pre-committed interpretation).
- **Tier B — one fresh cold pass + a pre-committed five-point narrowness test.** NEW middle tier for provably-narrow, non-substantive folds (precision/completeness/propagation tightening of an already-locked commitment).
- **Tier A — no new pass; reader-prescribed fix applied verbatim, verified by the next already-scheduled pass.** Purely editorial.

Five-point narrowness test (gates Tier B): (1) one section, diff-scoped; (2) no change to gating/constant/seed/estimator/computation/measurement; (3) tightens precision/completeness/propagation only, does not alter a pre-committed interpretation's *meaning*; (4) author writes a ripple-site enumeration; (5) a cold reader confirms (1)–(4) and may escalate.

## 3. Cold-pass-1 findings against the taxonomy (carried intact)

The pass found the taxonomy is **the highest-risk of the three seeds and not yet sound**:

- **Condition 1 is weak and quietly dangerous.** "Provably single-section / diff-scoped" is a *syntactic* test offered as control over *semantic* scope. Diff size is uncorrelated with semantic reach — CP2-N1's one-paragraph foil reframing rippled to §0.5.5 / §4 / §7. Condition 1 gives false comfort and must not be cited as evidence of narrowness; the real work is in conditions 4–5.
- **Condition 2 is the strongest gate** — but extend its substantive list to **name the candidate/baseline definition and feature set explicitly** (a `[B,p]`→`[B,pred]` change is substantive and is not obviously a "computation").
- **Condition 3 is the leak — the "clear-modulo by another name" door.** "Precision-tightening vs meaning-change" is *itself* an interpretive judgment, and the author writes the fold rationale (controls the framing). Almost any meaning-change can be described as a precision-tightening — verdict-#3's "strictly more powerful" → "more powerful in slope only" can be framed either way. As worded, the taxonomy's entire safety rests on a single reader rejecting the author's framing. **Condition 3 needs an operational test, not porous words, or it becomes the exact loophole NB1 forbade.**
- **The "one cold read" defense in rev1 defended the wrong flank.** One read preserves *byte-identity* between read and locked — true for any reader count ≥1, never the property at risk. The property Tier B actually relaxes is the **two-independent-pass invariant**, and the program has **on-record evidence against single passes** (two readers on byte-identical artifacts diverged clean-vs-3-blockers — "precisely why one clean pass is not the bar"). Tier B applies *one* pass to the **freshly changed bytes — the riskiest region** — while the rest of the document kept two. That is the real erosion.
- **Anchoring compounds it.** A second reader's value is largely in catching the *unenumerated* ripple; condition 4 hands the single Tier-B reader an *author-produced* enumeration to "confirm," anchoring them on the author's blind spots.
- **Tier A has its own leak.** It assumes a downstream pass exists. If the fold is the **last change before lock**, there is no next pass and "applied verbatim" is author-attested at the one moment it matters most — a mis-transcribed "verbatim" fix is clear-modulo by another name. **Tier A must be conditioned on a scheduled downstream pass actually existing.**
- **The self-check is a consistency check, not a correctness check.** The taxonomy reproduces every past call without loosening *relative to past practice* — but it is calibrated to fit N prior judgment calls, so it would faithfully reproduce whatever latitude those calls already contained. "Doesn't loosen vs. ourselves" ≠ "the floor is correct in absolute terms." Mild overfitting, stated out loud.

## 4. What a HARDENED Tier B would require (if pursued)

From the pass's mitigations:
- **Condition 3:** an operational precision-vs-meaning test (not author-framed prose) — e.g. a change qualifies only if it cannot alter any reader's *action* on any pre-committed outcome, demonstrated against the enumerated outcomes, not asserted.
- **Independent ripple enumeration:** the Tier-B reader enumerates ripple sites **independently, before** seeing the author's list, then compares (defeats anchoring).
- **Additional reader:** the Tier-B reader is **additional to** the two who cleared the pre-fold bytes, not a substitute.
- **Cheap escalation:** escalation to Tier C must be cheap enough that time pressure does not bias against it.
- **Tier A:** conditioned on a real, scheduled downstream pass.

## 5. The redesign-or-retire question (what this thread's own pass must decide)

**The cost rationale may not survive being made safe.** A *safe* Tier B is "one **additional** independent reader who does **full independent ripple analysis** with cheap escalation" — which is not meaningfully cheaper than the full re-route it was meant to economize. If hardening Tier B erases its own savings, the honest resolution is **retire**: record *"no middle tier is both safe and cheaper — keep full-re-route as the permanent default,"* and treat the seed's value as having **named and answered** the question rather than having produced a new tier.

**Decision for this thread's cold pass:**
- **Redesign** — adopt a hardened Tier B with §4's mitigations, only if it demonstrably saves cost over Tier C while passing the condition-3 operational test; **or**
- **Retire** — conclude no safe-and-cheaper middle tier exists; lock "substantive fold → full re-route" as the standing default and close the seed.

Author's lean (non-binding): **retire** is the likely honest outcome — the cost saving evaporates under the safety requirements, and the program already has evidence that one pass is not the bar. But the call belongs to this thread's independent pass, framed neutrally, not to the author.

## 6. Boundary

Tier A and the full-re-route default already operate (they are current practice, not new). This thread decides only the **fate of Tier B** and the formalization (or retirement) of the taxonomy as a written rule. Nothing here changes any locked artifact; it changes only the *forward* review discipline, and only if it survives its own pass.
