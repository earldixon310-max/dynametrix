# Result — EVIDENCE_PROVENANCE Stage 0 (y-free feasibility screen)

**Verdict: CLOSE-degenerate.** The candidate observable — retrieval-score entropy (Shannon entropy of
the sum-normalized top-k BM25 scores) — has essentially no variance across the substrate, so it cannot
be screened. Closed at feasibility, before any calibration compute.

## The numbers

| quantity | value | meaning |
|---|---|---|
| `sd(entropy)` | **0.0027 nats** | far below `ε_sd = 0.10` → **CLOSE-degenerate** |
| `multiple-R(entropy ~ confidence + max_retrieval_score)` | 0.349 | well below `ρ = 0.98` → **not** redundant |
| n | 3610 | full NQ-open validation split |
| entropy range | ~`ln 10 = 2.303` nats, near-constant | pinned at the maximum for every query |

The two thresholds together are diagnostic: entropy is **not** redundant with the baseline (`R = 0.35`,
fairly independent of confidence and max-score) — it closed because it is **variance-less**, not because
the baseline already contains it. There is nothing to screen *from*.

## Mechanism of the degeneracy (structural, not a fault)

BM25 scores within a top-k are always a gentle decay (here ~7–20, all within ~2× of each other). **Sum-
normalizing** a range-compressed score vector yields a near-uniform distribution for almost any query, so
its Shannon entropy is pinned near `ln k` regardless of how "ambiguous" the retrieval actually is. The
pipeline is healthy (real scores, sane confidence values, `R = 0.35`); the **observable** is the wrong
instrument. Entropy of a sum-normalized BM25 distribution lacks the dynamic range to vary across queries.

## What this is — and is not

- **Is:** a verdict on this specific observable instantiation. Sum-normalized BM25 score entropy is a
  structurally degenerate measure of retrieval ambiguity on NQ-open / BM25. The y-free feasibility screen
  caught it for the cost of retrieval + generation and **zero calibration compute** — the funnel working.
- **Is not:** a verdict on the Evidence Provenance hypothesis. The firewall held — Stage 0 never reached
  the `C↔y` relationship. Whether retrieval provenance adds correctness gain beyond confidence is
  **untested**; only this first observable is closed.

## Refinement to the degenerate arm (a methodology finding)

The pre-registration framed `CLOSE-degenerate` as "broken pipeline — fix and rerun." This run shows the
arm conflates two cases: a **broken instrument** (no signal) and a **structurally variance-less observable**
(the signal exists in principle but the chosen representation flattens it). This was the latter, and there
is nothing to "fix and rerun" — it closes the observable and constrains the successor. The degenerate arm
should distinguish the two going forward.

## Successor (dormant Atlas entry — not run)

Retrieval ambiguity needs a **dynamic-range** representation, not the entropy of a normalized score vector:
the raw top1−top2 score gap, the unnormalized score spread, or a dense / learned-sparse retriever whose
scores spike for clear matches. That is a **new pre-registered candidate** (new justification, lock, and
y-free screen), not an edit to this one. It waits as a dormant Atlas entry, per the consolidation
commitment (new directions wait; the verdict triggers the paper).

## Provenance

- **Lock:** `evidence-provenance-stage0-lock` @ commit `30691a1` (design sealed before any data).
- **Run:** single execution; `stage0_feasibility_result.json` is the canonical record.
- **Build stack:** pyserini **2.3.0**, JDK **Temurin 21.0.11.10**, index `lucene-inverted.wikipedia-dpr-100w.20260508.deb4c7b`, BM25 `k1=0.9 b=0.4`, top-k 10, sum-normalized; dataset `google-research-datasets/nq_open` @ `5dd9790a…` (validation); generator `Qwen/Qwen2.5-7B-Instruct` @ `a09a35458c…`, 4-bit bnb, greedy, `max_new_tokens=64`; confidence = mean per-token log-prob.
- **Firewall:** structural — no Stage 0 module imports `grader`; only `ex["question"]` is read; the writer asserts exactly `(qid, entropy, confidence, max_retrieval_score)`.
