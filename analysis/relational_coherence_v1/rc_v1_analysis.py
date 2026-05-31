"""
rc_v1_analysis.py — Relational Coherence v1 analysis script.

Implements PRE_REGISTRATION_RC_v1.md exactly. This script is committed at the
same lock tag (`rc-v1-lock`) as the pre-registration and is single-execution
per §14. Two modes:

    --mode smoke       Pre-lock integration dry run on a tiny slice. Writes NO
                       locked artifacts. Validates the dataset shape, vLLM
                       SamplingParams acceptance, AWQ+KV VRAM fit, and the
                       embed→graph path end-to-end. Run on Profile B before lock.
    --mode calibrate   Compute τ from the calibration slice (§7), write
                       calibration_constants.json. Run once, tag rc-v1-calibrated.
    --mode main        Run the main analysis (§1.1, §9) using the frozen τ;
                       write RESULT_RC_v1.md. Run once, tag rc-v1-result.

Design (locked):
  - Single perturbation family: framing/layout variation (§3), 10 templates ×
    5 schemas = 50 distinct combinations per query, all used, lexicographic
    (template_index, schema_index) order, no selection step.
  - Model: Qwen2.5-7B-Instruct-AWQ (4-bit) via vLLM, T=0, max_new_tokens=512,
    seed 0x1DEA, 1 sample per variant (primary).
  - Edge predicate: cosine(MiniLM(output_i), MiniLM(output_j)) >= τ (§4).
  - Scalars: C = edge density, F = pair-fraction-in-same-component, LCC = largest
    connected component fraction (§5).
  - Accuracy: lenient label-recovery (§6.1).
  - Gated test (§1.1): among comparable query-pairs (|ΔC| <= Δ_c = 0.05), at least
    k = 0.20 satisfy |ΔF| >= δ_p = 0.10.

Data source (§2.1): the canonical MMLU release `cais/mmlu` (Hugging Face Hub),
loaded directly via the `datasets` library. Each item exposes the raw question,
the four separate option strings, and the integer gold index (0..3) — the shape
the §3 framing generator requires. (Earlier multi-bin drafts named PromptBench as
the substrate for its perturbation/attack module; the single-bin collapse removed
that role, and PromptBench's pre-assembled MMLU items do not expose separated
options, so v1 loads `cais/mmlu` directly. This is the same upstream data.)
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import itertools
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# vLLM selects the FlashInfer sampler for top-k/top-p when flashinfer is installed;
# FlashInfer JIT-compiles a CUDA kernel that needs nvcc / a full CUDA toolkit, which
# a driver-only WSL2 deployment lacks. Under the primary run's greedy decoding (T=0)
# token selection is argmax and identical across sampler backends, so we force vLLM's
# native PyTorch sampler (no JIT). Set before vLLM is imported; the value is inherited
# by the spawned EngineCore worker. Deployment setting only — see §2.3.
os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")

# =========================================================================
# Locked configuration constants (per PRE_REGISTRATION_RC_v1.md)
# =========================================================================

MASTER_SEED = 0x1DEA                     # §3.2, §2.2

# Model (§2.2)
MODEL_REPO = "Qwen/Qwen2.5-7B-Instruct-AWQ"
MODEL_QUANTIZATION = "awq"
# §2.3: KV-cache reservation fraction on the 16 GB card (shared with the Windows
# desktop compositor). Pinned below vLLM's 0.92 default to leave headroom. Governs
# only KV-cache size, not generated tokens under greedy decoding — not an analysis parameter.
GPU_MEMORY_UTILIZATION = 0.80
DECODING_PRIMARY = dict(temperature=0.0, top_p=1.0, top_k=-1,
                        repetition_penalty=1.0, max_tokens=512, seed=MASTER_SEED)
DECODING_STOCHASTIC = dict(temperature=0.7, top_p=0.95, max_tokens=512)  # seed varies per sample
STOCHASTIC_SAMPLES = 3                    # §2.2

# Embedding (§2.4)
EMBED_REPO = "sentence-transformers/all-MiniLM-L6-v2"

# Generator (§3)
N_VAR = 50                                # 10 templates × 5 schemas, all used

# Edge / scalars / calibration (§4, §5, §7)
TAU_PERCENTILE = 5.0                       # τ = 5th percentile of within-query output cosines

# Gated test thresholds (§1.1)
DELTA_C = 0.05                             # comparable-query consistency window
DELTA_P = 0.10                             # pair-fraction separation threshold
K_THRESHOLD = 0.20                         # min proportion of comparable pairs separated

# Bootstrap (§8) — per-query F CI
BOOTSTRAP_B = 10_000
BOOTSTRAP_SEED = MASTER_SEED

# Dataset (§2.1)
MAIN_SUBJECTS = ["high_school_mathematics", "professional_law", "miscellaneous"]
QUERIES_PER_SUBJECT = 100
CALIBRATION_SUBJECT = "elementary_mathematics"
CALIBRATION_N = 50
# Stochastic-panel subset (§2.2): first 16 hs_math + 17 prof_law + 17 misc
STOCHASTIC_SUBSET = {"high_school_mathematics": 16,
                     "professional_law": 17,
                     "miscellaneous": 17}

# Base prompt template option placeholders (§2.5) — content is filled verbatim.


# =========================================================================
# §3 Framing-variation generator (pinned)
# =========================================================================

# 10 framing templates (§3). {OPTIONS} is the schema-rendered option block.
FRAMING_TEMPLATES: List[str] = [
    "Question: {question}\n{OPTIONS}\n\nAnswer:",
    "Q: {question}\n{OPTIONS}\n\nA:",
    "Please answer this multiple-choice question.\n{question}\n{OPTIONS}\n\nAnswer:",
    "Read the question carefully and select the best option.\n{question}\n{OPTIONS}\n\nAnswer:",
    "Answer the following.\n{question}\n{OPTIONS}\n\nAnswer:",
    "Multiple choice question:\n{question}\n{OPTIONS}\n\nAnswer:",
    "{question}\nSelect one:\n{OPTIONS}\n\nAnswer:",
    "The following is a multiple-choice question.\n{question}\n{OPTIONS}\n\nAnswer:",
    "Examine the question below and identify the correct choice.\n{question}\n{OPTIONS}\n\nAnswer:",
    "Here is a question. Choose the correct answer from the options.\n{question}\n{OPTIONS}\n\nAnswer:",
]

# 5 option-layout schemas (§3). Each takes the four option strings and renders {OPTIONS}.
def _schema_s1(a, b, c, d): return f"Options:\n(A) {a}\n(B) {b}\n(C) {c}\n(D) {d}"
def _schema_s2(a, b, c, d): return f"(A) {a}\n(B) {b}\n(C) {c}\n(D) {d}"
def _schema_s3(a, b, c, d): return f"(A) {a}  (B) {b}  (C) {c}  (D) {d}"
def _schema_s4(a, b, c, d): return f"Options:\n(A) {a}\n\n(B) {b}\n\n(C) {c}\n\n(D) {d}"
def _schema_s5(a, b, c, d): return f"A. {a}\nB. {b}\nC. {c}\nD. {d}"

LAYOUT_SCHEMAS = [_schema_s1, _schema_s2, _schema_s3, _schema_s4, _schema_s5]


def generate_variants(question: str, options: Sequence[str]) -> List[str]:
    """Produce the 50 framing variants for one query (§3).

    Enumerated by (template_index, schema_index) in lexicographic order:
    template 0 with schemas 0..4, then template 1 with schemas 0..4, etc.
    Exactly 10 × 5 = 50 distinct combinations; all used, no selection.

    Option content and order are never permuted (§3 "meaning preservation by
    construction"); the verbatim question text is never altered.
    """
    assert len(options) == 4, "MMLU multi-choice requires exactly 4 options"
    a, b, c, d = options
    variants: List[str] = []
    for t_idx, template in enumerate(FRAMING_TEMPLATES):         # lexicographic outer
        for s_idx, schema in enumerate(LAYOUT_SCHEMAS):          # lexicographic inner
            options_block = schema(a, b, c, d)
            variants.append(template.format(question=question, OPTIONS=options_block))
    assert len(variants) == N_VAR, f"expected {N_VAR} variants, got {len(variants)}"
    return variants


def base_prompt(question: str, options: Sequence[str]) -> str:
    """Canonical base prompt (§2.5) = template 0 (Question:) with schema S1.
    Used as the reference for the p(v) sanity check (§3.1)."""
    a, b, c, d = options
    return FRAMING_TEMPLATES[0].format(question=question, OPTIONS=_schema_s1(a, b, c, d))


# =========================================================================
# §6 Lenient label-recovery accuracy
# =========================================================================

_LENIENT_PATTERNS = [
    re.compile(r"(?:answer|response|choice)[\s:]*(?:is|=|:)?[\s]*[\(\[]?([abcd])[\)\]]?"),
    re.compile(r"[\(\[]([abcd])[\)\]]"),
    re.compile(r"^[\s]*([abcd])[\s.,:;]"),
    re.compile(r"\b([abcd])\b"),  # last resort: lone a/b/c/d at a word boundary
]
_STRICT_PATTERN = re.compile(r"^\s*\(([abcd])\)", re.IGNORECASE)
_GOLD_LETTER = ["a", "b", "c", "d"]


def extract_lenient(output_text: str) -> Optional[str]:
    """§6.1 lenient label-recovery: first match across the ordered pattern list."""
    t = output_text.strip().lower()
    for pat in _LENIENT_PATTERNS:
        m = pat.search(t)
        if m:
            return m.group(1)
    return None


def accuracy_lenient(output_text: str, gold_index: int) -> int:
    letter = extract_lenient(output_text)
    if letter is None:
        return 0
    return int(letter == _GOLD_LETTER[gold_index])


def accuracy_strict(output_text: str, gold_index: int) -> int:
    """§6.2 strict-format: output must begin with (A)/(B)/(C)/(D)."""
    m = _STRICT_PATTERN.match(output_text)
    if not m:
        return 0
    return int(m.group(1).lower() == _GOLD_LETTER[gold_index])


# =========================================================================
# §4 / §5 Graph construction and scalars
# =========================================================================

def cosine_matrix(embeddings: np.ndarray) -> np.ndarray:
    """Pairwise cosine similarity of row-vectors (N × d) -> (N × N)."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-12, norms)
    unit = embeddings / norms
    return unit @ unit.T


def connected_components(adj: np.ndarray) -> List[int]:
    """Return component-size list {n_i} for an undirected boolean adjacency matrix.
    Union-find; diagonal ignored."""
    n = adj.shape[0]
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(n):
        for j in range(i + 1, n):
            if adj[i, j]:
                union(i, j)

    sizes: Dict[int, int] = {}
    for i in range(n):
        r = find(i)
        sizes[r] = sizes.get(r, 0) + 1
    return list(sizes.values())


def graph_scalars(cos: np.ndarray, tau: float) -> Tuple[float, float, float, np.ndarray]:
    """Compute C (edge density), F (pair-fraction-in-same-component), LCC (largest
    component fraction) for the behavioral-equivalence graph at threshold tau.

    Returns (C, F, LCC, adjacency).
    """
    n = cos.shape[0]
    adj = cos >= tau
    np.fill_diagonal(adj, False)

    n_edges = int(np.triu(adj, k=1).sum())
    total_pairs = n * (n - 1) / 2.0
    C = (n_edges / total_pairs) if total_pairs > 0 else 0.0

    comp_sizes = connected_components(adj)
    same_comp_pairs = sum(s * (s - 1) for s in comp_sizes)  # ordered pairs Σ n_i(n_i-1)
    denom = n * (n - 1)
    F = (same_comp_pairs / denom) if denom > 0 else 0.0
    LCC = (max(comp_sizes) / n) if comp_sizes else 0.0
    return float(C), float(F), float(LCC), adj


def bootstrap_F_ci(cos: np.ndarray, tau: float, seed: int = BOOTSTRAP_SEED,
                   B: int = BOOTSTRAP_B) -> Tuple[float, float]:
    """§8 per-query F 95% CI by bootstrap resampling over the N nodes.

    Resample node indices with replacement, take the induced cosine submatrix,
    recompute F on the induced graph, repeat B times, return (2.5, 97.5) pctiles.
    """
    n = cos.shape[0]
    rng = np.random.default_rng(seed)
    boot = np.empty(B)
    for b in range(B):
        idx = rng.integers(0, n, size=n)
        sub = cos[np.ix_(idx, idx)]
        _, f, _, _ = graph_scalars(sub, tau)
        boot[b] = f
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


# =========================================================================
# §1.1 Gated test
# =========================================================================

def gated_test(C_by_q: List[float], F_by_q: List[float]) -> Tuple[float, int, int]:
    """Among comparable query-pairs (|ΔC| <= DELTA_C), proportion with |ΔF| >= DELTA_P.

    Returns (proportion, n_separated, n_comparable).
    """
    n = len(C_by_q)
    n_comparable = 0
    n_separated = 0
    for i in range(n):
        for j in range(i + 1, n):
            if abs(C_by_q[i] - C_by_q[j]) <= DELTA_C:
                n_comparable += 1
                if abs(F_by_q[i] - F_by_q[j]) >= DELTA_P:
                    n_separated += 1
    proportion = (n_separated / n_comparable) if n_comparable > 0 else float("nan")
    return proportion, n_separated, n_comparable


# =========================================================================
# Data loading — cais/mmlu (canonical MMLU), loaded directly (§2.1)
# =========================================================================

# Unit separator used in the qid hash so option boundaries are unambiguous (§2.1).
_QID_SEP = "␟"


def _qid(question: str, choices: Sequence[str]) -> str:
    """Stable, content-derived question identifier (§2.1):
    SHA-256 of  question + ␟ + ␟.join(choices)."""
    payload = (question + _QID_SEP + _QID_SEP.join(choices)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_mmlu_items(subject: str, n: int, offset: int = 0) -> List[dict]:
    """Return up to n MMLU items for `subject`, ordered by qid-sort (§2.1).

    Source: `cais/mmlu`, `test` split, subject configuration. Each `cais/mmlu`
    row is {question:str, choices:list[4]:str, answer:int 0..3, subject:str}; we
    map it to {"question","options"(4),"gold"(0..3),"qid","subject"}. Items are
    sorted ascending by qid (content-derived, row-order-independent) and sliced
    [offset:offset+n].
    """
    from datasets import load_dataset

    ds = load_dataset("cais/mmlu", subject, split="test")
    items: List[dict] = []
    for row in ds:
        # §2.5: no normalization beyond whitespace trimming. qid (§2.1) is computed
        # on the trimmed content actually used, so the identifier is stable w.r.t.
        # the strings that enter the prompts.
        question = row["question"].strip()
        choices = [str(c).strip() for c in row["choices"]]
        assert len(choices) == 4, f"{subject}: expected 4 choices, got {len(choices)}"
        gold = int(row["answer"])
        assert 0 <= gold <= 3, f"{subject}: gold index {gold} out of range"
        items.append({
            "question": question,
            "options": choices,
            "gold": gold,
            "qid": _qid(question, choices),
            "subject": subject,
        })
    items.sort(key=lambda it: it["qid"])
    sliced = items[offset:offset + n]
    if len(sliced) < n:
        raise ValueError(
            f"{subject}: requested {n} items at offset {offset} but only "
            f"{len(sliced)} available (subject has {len(items)} test items)."
        )
    return sliced


def load_main_eval() -> List[dict]:
    items = []
    for subject in MAIN_SUBJECTS:
        items.extend(load_mmlu_items(subject, QUERIES_PER_SUBJECT))
    return items


def load_calibration() -> List[dict]:
    return load_mmlu_items(CALIBRATION_SUBJECT, CALIBRATION_N)


def load_stochastic_subset() -> List[dict]:
    items = []
    for subject, count in STOCHASTIC_SUBSET.items():
        items.extend(load_mmlu_items(subject, count))
    return items


# =========================================================================
# Model + embedding wrappers
# =========================================================================

class ModelRunner:
    """vLLM wrapper for Qwen2.5-7B-Instruct-AWQ with chat-template wrapping (§2.2, §2.5)."""

    def __init__(self):
        from vllm import LLM
        from transformers import AutoTokenizer
        self._LLM = LLM(model=MODEL_REPO, quantization=MODEL_QUANTIZATION,
                        seed=MASTER_SEED, dtype="float16",
                        gpu_memory_utilization=GPU_MEMORY_UTILIZATION)
        self._tok = AutoTokenizer.from_pretrained(MODEL_REPO)

    def _wrap(self, prompt: str) -> str:
        """Apply the model's default chat template, single user turn, no system
        prompt beyond the default (§2.5)."""
        messages = [{"role": "user", "content": prompt}]
        return self._tok.apply_chat_template(messages, tokenize=False,
                                             add_generation_prompt=True)

    def generate(self, prompts: List[str], decoding: dict, seed: Optional[int] = None) -> List[str]:
        from vllm import SamplingParams
        params = dict(decoding)
        if seed is not None:
            params["seed"] = seed
        sp = SamplingParams(**params)
        wrapped = [self._wrap(p) for p in prompts]
        outs = self._LLM.generate(wrapped, sp)
        # vLLM preserves input order
        return [o.outputs[0].text for o in outs]


class Embedder:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self._m = SentenceTransformer(EMBED_REPO)

    def encode(self, texts: List[str]) -> np.ndarray:
        return np.asarray(self._m.encode(texts, convert_to_numpy=True), dtype=np.float64)


# =========================================================================
# Calibration mode (§7)
# =========================================================================

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_calibration(out_dir: Path) -> None:
    print("[calibrate] loading calibration slice...")
    items = load_calibration()
    runner = ModelRunner()
    embedder = Embedder()

    within_query_cosines: List[float] = []
    pv_values: List[float] = []

    for k, item in enumerate(items):
        variants = generate_variants(item["question"], item["options"])
        outputs = runner.generate(variants, DECODING_PRIMARY)
        out_emb = embedder.encode(outputs)
        cos = cosine_matrix(out_emb)
        iu = np.triu_indices(N_VAR, k=1)
        within_query_cosines.extend(cos[iu].tolist())

        # p(v) sanity check (§3.1): input similarity of each variant to the base prompt
        base = base_prompt(item["question"], item["options"])
        in_emb = embedder.encode([base] + variants)
        base_vec, var_vecs = in_emb[0], in_emb[1:]
        bnorm = np.linalg.norm(base_vec) or 1e-12
        for vv in var_vecs:
            vnorm = np.linalg.norm(vv) or 1e-12
            pv_values.append(float(np.dot(base_vec, vv) / (bnorm * vnorm)))
        if (k + 1) % 10 == 0:
            print(f"[calibrate] {k+1}/{len(items)} queries done")

    tau = float(np.percentile(within_query_cosines, TAU_PERCENTILE))
    pv_arr = np.array(pv_values)

    constants = {
        "tau": tau,
        "tau_percentile": TAU_PERCENTILE,
        "n_calibration_queries": len(items),
        "n_within_query_cosines": len(within_query_cosines),
        "within_query_cosine_summary": {
            "min": float(np.min(within_query_cosines)),
            "p05": tau,
            "median": float(np.median(within_query_cosines)),
            "max": float(np.max(within_query_cosines)),
        },
        "pv_sanity_summary": {
            "min": float(pv_arr.min()), "p05": float(np.percentile(pv_arr, 5)),
            "median": float(np.median(pv_arr)), "max": float(pv_arr.max()),
            "fraction_ge_0.9": float((pv_arr >= 0.9).mean()),
        },
        "master_seed": MASTER_SEED,
    }
    out_path = out_dir / "calibration_constants.json"
    out_path.write_text(json.dumps(constants, indent=2))

    # §7 step 6: persist the FULL distributions (not only the percentile summaries)
    # so they are recoverable after single-execution calibration.
    dist_path = out_dir / "calibration_distributions.npz"
    np.savez_compressed(
        dist_path,
        within_query_cosines=np.asarray(within_query_cosines, dtype=np.float64),
        pv_values=np.asarray(pv_values, dtype=np.float64),
        tau=np.float64(tau),
        tau_percentile=np.float64(TAU_PERCENTILE),
    )

    const_sha = sha256_file(out_path)
    dist_sha = sha256_file(dist_path)
    print(f"[calibrate] tau = {tau:.4f}; wrote {out_path}")
    print(f"[calibrate] p(v) sanity: median={constants['pv_sanity_summary']['median']:.4f}, "
          f"fraction>=0.9={constants['pv_sanity_summary']['fraction_ge_0.9']:.4f}")
    print(f"[calibrate] wrote full distributions -> {dist_path} "
          f"({len(within_query_cosines)} cosines, {len(pv_values)} p(v) values)")
    print(f"[calibrate] SHA-256 calibration_constants.json = {const_sha}")
    print(f"[calibrate] SHA-256 calibration_distributions.npz = {dist_sha}")
    print("[calibrate] record both SHA-256 values in the materialization manifest (§11).")


# =========================================================================
# Main mode (§1.1, §9)
# =========================================================================

@dataclass
class QueryResult:
    qid: str
    subject: str
    C: float
    F: float
    F_ci_lo: float
    F_ci_hi: float
    LCC: float
    accuracy_lenient: float
    accuracy_strict: float
    n_variants: int


def run_stochastic_panel(runner: "ModelRunner", embedder: "Embedder",
                         tau: float) -> dict:
    """§2.2 stochastic sensitivity panel (non-gating, reported per §9).

    On the pinned 50-query subset (§2.2), draw STOCHASTIC_SAMPLES samples at
    T = 0.7 (seed = MASTER_SEED + sample_index) and recompute (C, F, LCC) per
    (query, sample). Returns a summary dict; does not affect the §1.1 verdict.
    """
    print("[panel] running stochastic sensitivity panel (T=0.7, "
          f"{STOCHASTIC_SAMPLES} samples on {sum(STOCHASTIC_SUBSET.values())} queries)...")
    items = load_stochastic_subset()
    per_sample_F: List[float] = []
    per_sample_C: List[float] = []
    per_sample_LCC: List[float] = []
    per_qid_F: Dict[str, List[float]] = {}
    n_failed = 0

    for item in items:
        variants = generate_variants(item["question"], item["options"])
        for s in range(STOCHASTIC_SAMPLES):
            try:
                outputs = runner.generate(variants, DECODING_STOCHASTIC,
                                          seed=MASTER_SEED + s)
            except Exception as exc:
                print(f"[panel] WARN sample {s} qid={item['qid']} failed: "
                      f"{type(exc).__name__}: {exc}")
                n_failed += 1
                continue
            cos = cosine_matrix(embedder.encode(outputs))
            C, F, LCC, _ = graph_scalars(cos, tau)
            per_sample_C.append(C)
            per_sample_F.append(F)
            per_sample_LCC.append(LCC)
            per_qid_F.setdefault(item["qid"], []).append(F)

    # within-query spread of F across the stochastic samples (sampling-noise probe)
    within_query_F_range = [max(v) - min(v) for v in per_qid_F.values() if len(v) > 1]

    summary = {
        "n_queries": len(items),
        "samples_per_query": STOCHASTIC_SAMPLES,
        "decoding": {k: v for k, v in DECODING_STOCHASTIC.items()},
        "n_failed_samples": n_failed,
        "F_mean": float(np.mean(per_sample_F)) if per_sample_F else float("nan"),
        "F_var": float(np.var(per_sample_F)) if per_sample_F else float("nan"),
        "C_mean": float(np.mean(per_sample_C)) if per_sample_C else float("nan"),
        "LCC_mean": float(np.mean(per_sample_LCC)) if per_sample_LCC else float("nan"),
        "mean_within_query_F_range": (float(np.mean(within_query_F_range))
                                      if within_query_F_range else float("nan")),
    }
    print(f"[panel] F_mean={summary['F_mean']:.4f}, "
          f"mean within-query F range={summary['mean_within_query_F_range']:.4f}")
    return summary


def run_main(out_dir: Path, tau: float) -> None:
    print(f"[main] using frozen tau = {tau:.4f}")
    items = load_main_eval()
    runner = ModelRunner()
    embedder = Embedder()

    results: List[QueryResult] = []
    dropped: List[str] = []

    for k, item in enumerate(items):
        variants = generate_variants(item["question"], item["options"])
        try:
            outputs = runner.generate(variants, DECODING_PRIMARY)
        except Exception as exc:  # technical inference failure (§8)
            print(f"[main] WARN dropping qid={item['qid']}: {type(exc).__name__}: {exc}")
            dropped.append(item["qid"])
            continue
        out_emb = embedder.encode(outputs)
        cos = cosine_matrix(out_emb)
        C, F, LCC, _ = graph_scalars(cos, tau)
        ci_lo, ci_hi = bootstrap_F_ci(cos, tau)
        acc_len = float(np.mean([accuracy_lenient(o, item["gold"]) for o in outputs]))
        acc_str = float(np.mean([accuracy_strict(o, item["gold"]) for o in outputs]))
        results.append(QueryResult(
            qid=item["qid"], subject=item.get("subject", "?"),
            C=C, F=F, F_ci_lo=ci_lo, F_ci_hi=ci_hi, LCC=LCC,
            accuracy_lenient=acc_len, accuracy_strict=acc_str, n_variants=N_VAR,
        ))
        if (k + 1) % 25 == 0:
            print(f"[main] {k+1}/{len(items)} queries done")

    C_by_q = [r.C for r in results]
    F_by_q = [r.F for r in results]
    proportion, n_sep, n_comp = gated_test(C_by_q, F_by_q)
    verdict = "POSITIVE" if (n_comp > 0 and proportion >= K_THRESHOLD) else "NULL"

    # high-accuracy + low-F cell (§1.2): report count (thresholds reported, not gating)
    hi_acc_lo_F = sum(1 for r in results if r.accuracy_lenient >= 0.9 and r.F <= 0.5)

    # Stochastic sensitivity panel (§2.2, §9) — non-gating; reuse the loaded model.
    stochastic_summary = run_stochastic_panel(runner, embedder, tau)

    _write_result_doc(out_dir, results, dropped, tau, proportion, n_sep, n_comp,
                      verdict, hi_acc_lo_F, stochastic_summary)
    print(f"\n=== GATED TEST: proportion={proportion:.4f} "
          f"(separated {n_sep}/{n_comp} comparable pairs); "
          f"k={K_THRESHOLD} → VERDICT: {verdict} ===")


def _write_result_doc(out_dir, results, dropped, tau, proportion, n_sep, n_comp,
                      verdict, hi_acc_lo_F, stochastic_summary=None) -> None:
    F = [r.F for r in results]
    C = [r.C for r in results]
    LCC = [r.LCC for r in results]
    acc = [r.accuracy_lenient for r in results]
    acc_s = [r.accuracy_strict for r in results]
    lines = []
    lines.append("# RESULT_RC_v1")
    lines.append("")
    lines.append(f"**Date:** {date.today().isoformat()}")
    lines.append(f"**Operator:** Earl Dixon")
    lines.append("**Pre-registration:** PRE_REGISTRATION_RC_v1.md (tag `rc-v1-lock`)")
    lines.append("")
    lines.append("## Run summary")
    lines.append(f"- Frozen τ: {tau:.4f}")
    lines.append(f"- Queries analyzed: {len(results)} (dropped for inference failure: {len(dropped)})")
    lines.append(f"- Variants per analyzed query: {N_VAR} for all (a query failing any "
                 f"variant is dropped in full, §8; no partial-variant queries enter the analysis)")
    if dropped:
        lines.append(f"- Dropped qids: {', '.join(dropped)}")
    lines.append("")
    lines.append("## Primary gated test (§1.1)")
    lines.append("")
    lines.append(f"**Comparable query-pairs (|ΔC| ≤ {DELTA_C}):** {n_comp:,}")
    lines.append(f"**Separated (|ΔF| ≥ {DELTA_P}):** {n_sep:,}")
    lines.append(f"**Proportion:** {proportion:.4f}  (threshold k = {K_THRESHOLD})")
    lines.append("")
    lines.append(f"### Verdict: {verdict}")
    lines.append("")
    if verdict == "POSITIVE":
        lines.append("Graph topology (F) distinguishes queries that the aggregate "
                     "consistency rate (C) rates as equivalent at the pre-registered "
                     "thresholds. The simple claim is supported.")
    else:
        lines.append("The proportion of comparable query-pairs with topological "
                     "separation did not reach k. Clean null under the pre-registered "
                     "thresholds; published with the same discipline as a positive.")
    lines.append("")
    lines.append("## Aggregate distributions")
    if results:
        lines.append(f"- C: mean {np.mean(C):.4f}, min {np.min(C):.4f}, max {np.max(C):.4f}")
        lines.append(f"- F: mean {np.mean(F):.4f}, min {np.min(F):.4f}, max {np.max(F):.4f}")
        lines.append(f"- LCC: mean {np.mean(LCC):.4f}, min {np.min(LCC):.4f}, max {np.max(LCC):.4f}")
        lines.append(f"- cross-query variance of F: {np.var(F):.5f}")
        lines.append(f"- accuracy_lenient: mean {np.mean(acc):.4f}")
        lines.append(f"- accuracy_strict (sensitivity): mean {np.mean(acc_s):.4f}, "
                     f"min {np.min(acc_s):.4f}, max {np.max(acc_s):.4f}")
        lines.append(f"- high-accuracy(≥0.9) + low-F(≤0.5) queries: {hi_acc_lo_F} (§1.2 characterization)")
    lines.append("")
    lines.append("## Stochastic sensitivity panel (§2.2, non-gating)")
    if stochastic_summary:
        s = stochastic_summary
        lines.append(f"- Queries: {s['n_queries']} × {s['samples_per_query']} samples "
                     f"at T=0.7 (failed samples: {s['n_failed_samples']})")
        lines.append(f"- F: mean {s['F_mean']:.4f}, variance {s['F_var']:.5f}")
        lines.append(f"- C mean {s['C_mean']:.4f}; LCC mean {s['LCC_mean']:.4f}")
        lines.append(f"- mean within-query F range across samples: "
                     f"{s['mean_within_query_F_range']:.4f} (sampling-noise probe)")
    else:
        lines.append("- (not run)")
    lines.append("")
    lines.append("## Per-query table")
    lines.append("")
    lines.append("| qid | subject | C | F | F 95% CI | LCC | acc_lenient | acc_strict |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(f"| {r.qid} | {r.subject} | {r.C:.3f} | {r.F:.3f} | "
                     f"[{r.F_ci_lo:.3f}, {r.F_ci_hi:.3f}] | {r.LCC:.3f} | "
                     f"{r.accuracy_lenient:.3f} | {r.accuracy_strict:.3f} |")
    lines.append("")
    lines.append("---")
    lines.append("*Single-execution result under tag `rc-v1-lock`. Published under "
                 "null-result-parity discipline (§9).*")
    (out_dir / "RESULT_RC_v1.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[main] wrote {out_dir / 'RESULT_RC_v1.md'}")


# =========================================================================
# Pre-lock integration dry run (writes NO locked artifacts)
# =========================================================================

def run_smoke(out_dir: Path, n: int = 2) -> None:
    """Integration dry run for the parts pure-function tests cannot reach.

    Validates, on the target hardware (Profile B):
      - load_dataset("cais/mmlu", subject, split="test") returns the expected
        {question, choices[4], answer} shape and the qid sort works
      - the §3 generator yields exactly N_VAR = 50 variants
      - vLLM accepts DECODING_PRIMARY as SamplingParams and the AWQ model + KV
        cache fit in available VRAM
      - the embedder and graph scalars run end-to-end

    Non-gating. Writes nothing. Uses a placeholder τ purely to exercise the graph
    path; the printed C/F/LCC are NOT results. Run before the lock commit.
    """
    subject = MAIN_SUBJECTS[0]
    print(f"[smoke] loading {n} items from cais/mmlu '{subject}' (test split)...")
    items = load_mmlu_items(subject, n)
    for it in items:
        assert len(it["options"]) == 4 and 0 <= it["gold"] <= 3, "unexpected item shape"
    print(f"[smoke] loaded {len(items)} items; first qid={items[0]['qid'][:12]}...")

    runner = ModelRunner()
    embedder = Embedder()
    for k, item in enumerate(items):
        variants = generate_variants(item["question"], item["options"])
        assert len(variants) == N_VAR, f"expected {N_VAR} variants, got {len(variants)}"
        outputs = runner.generate(variants, DECODING_PRIMARY)
        assert len(outputs) == N_VAR, f"expected {N_VAR} outputs, got {len(outputs)}"
        emb = embedder.encode(outputs)
        cos = cosine_matrix(emb)
        C, F, LCC, _ = graph_scalars(cos, 0.5)  # placeholder tau — integration check only
        print(f"[smoke] item {k}: {len(outputs)} generations, emb shape {emb.shape}, "
              f"C={C:.3f} F={F:.3f} LCC={LCC:.3f} (tau=0.5 placeholder, NOT a result)")
    print("[smoke] integration OK — dataset shape, vLLM SamplingParams, AWQ+KV fit, "
          "embedding, and graph scalars all ran. No artifacts written.")


# =========================================================================
# Entrypoint
# =========================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["smoke", "calibrate", "main"], required=True)
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--smoke-n", type=int, default=2,
                        help="(smoke mode) number of items to dry-run")
    parser.add_argument("--calibration-constants", type=Path, default=None,
                        help="(main mode) path to frozen calibration_constants.json")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "smoke":
        run_smoke(args.out_dir, args.smoke_n)
        return 0

    if args.mode == "calibrate":
        run_calibration(args.out_dir)
        return 0

    # main mode: load frozen tau
    cc_path = args.calibration_constants or (args.out_dir / "calibration_constants.json")
    if not cc_path.exists():
        print(f"ERROR: calibration constants not found at {cc_path}; run --mode calibrate first.")
        return 1
    tau = json.loads(cc_path.read_text())["tau"]
    run_main(args.out_dir, tau)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# end of rc_v1_analysis.py
