# Observable Registry

Cumulative log of every observable the program has **proposed**, its information source, and what
happened when it was tested. The counterpart to candidate generation: the Atlas asks *what could carry
information*; this records *what was proposed, how it was derived, and the outcome*. Nothing is deleted —
nulls and closes stay, with provenance.

Status legend: **Validated** / **Not-Validated** / **Inconclusive** (OVP verdicts) · **Closed-feasibility**
(closed at a y-free screen, never reached the verdict) · **Dormant** (proposed, not yet run) ·
**Retired** (superseded).

| ID | Observable | Information source | Substrate | Status | Note |
|---|---|---|---|---|---|
| OBS-W-CT | CT-v1 coherence (persistence/instability/competition) | atmospheric residuals | weather | Closed (pre-discipline) | descriptor under-justified; verification null |
| OBS-D-trunc | truncated-input confidence | single forward pass | ChatGPT-detector | Not-Validated | same info source as `B` |
| OBS-D-len | text_length | input-intrinsic | ChatGPT-detector | Not-Validated | absorbed |
| OBS-D-prob | predicted_prob_ai | single forward pass | ChatGPT-detector | (see #3 ledger) | repackaged `B` |
| OBS-D-pred | pred (argmax) | single forward pass | ChatGPT-detector | (see #4 ledger) | repackaged `B` |
| OBS-D-spread | perturbation_spread (std over valid paraphrases) | multi-pass / paraphrase ensemble | ChatGPT-detector | **Not-Validated** (D=−0.0071, scope 1785/2000) | confidence already absorbs it |
| OBS-EP-ent | retrieval-score entropy (sum-normalized top-k BM25) | retrieval-pipeline structure (exogenous) | RAG-QA (NQ-open / BM25) | **Closed-feasibility** | `sd=0.0027` — variance-less by construction; **not** redundant (`R=0.35`) |
| OBS-EP-gap | retrieval ambiguity via **dynamic-range** score representation (top1−top2 gap / raw spread / dense-retriever scores that spike) | retrieval-pipeline structure (exogenous) | RAG-QA | **Dormant** | successor to OBS-EP-ent; needs its own justification + lock + y-free screen |

## Open observation across the registry

Every **endogenous** observable (computed from the model's own forward pass / its outputs) has been
Not-Validated — consistent with the structural argument that confidence, the model's own self-assessment,
already prices anything downstream of the same computation. The first **exogenous** candidate
(retrieval-pipeline structure) reached only the feasibility gate, where its first instantiation proved
variance-less. The exogenous frontier (retrieval structure with dynamic range; cross-model disagreement;
human disagreement; external retrieval) remains the place a YES could come from, and remains untested at
the verdict level.
