"""config.py — Evidence Provenance Stage 0 pinned configuration (build-manifest source of truth).

Decision-rule pins are LOCKED under tag `evidence-provenance-stage0-lock`. Mechanical pins are
recorded at build (single choice, no shopping). This module references NO gold answers and NO grader.
"""

# --- decision rule (LOCKED) ---
RHO = 0.98          # multiple-R close threshold (CLOSE-redundant)
EPS_SD = 0.10       # nats; degeneracy close threshold (CLOSE-degenerate)
TOP_K = 10

# --- substrate / pipeline (build pins; single choice, no shopping) ---
DATASET = "google-research-datasets/nq_open"   # bare "nq_open" alias no longer resolves; same dataset
DATASET_REVISION = "5dd9790a83002ad084ddeb7c420dc716852c6f28"   # pinned dataset commit (reproducibility)
SPLIT = "validation"               # ~3.6k questions; QUESTIONS ONLY are read at Stage 0
PYSERINI_VERSION = "2.3.0"
JDK = "Temurin-21.0.11.10"
INDEX = "wikipedia-dpr-100w"
INDEX_ARTIFACT = "lucene-inverted.wikipedia-dpr-100w.20260508.deb4c7b"
BM25_K1 = 0.9
BM25_B = 0.4
GENERATOR = "Qwen/Qwen2.5-7B-Instruct"
GENERATOR_REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"
QUANTIZATION = "bitsandbytes-4bit-nf4"
DECODING = "greedy"
MAX_NEW_TOKENS = 64
PROMPT_TEMPLATE = (
    "Use the following passages to answer the question.\n\n"
    "Passages:\n{passages}\n\n"
    "Question:\n{question}\n\n"
    "Answer:"
)

# --- the firewall, as data: the ONLY columns that may exist in the screen input ---
SCREEN_INPUT_COLUMNS = ["qid", "entropy", "confidence", "max_retrieval_score"]
SCREEN_INPUT_PATH = "stage0_screen_input.csv"
RESULT_PATH = "stage0_feasibility_result.json"

# pins recorded into the result JSON / build manifest
MANIFEST_PINS = [
    "DATASET", "DATASET_REVISION", "SPLIT", "PYSERINI_VERSION", "JDK", "INDEX", "INDEX_ARTIFACT",
    "BM25_K1", "BM25_B", "TOP_K", "GENERATOR", "GENERATOR_REVISION", "QUANTIZATION",
    "DECODING", "MAX_NEW_TOKENS", "RHO", "EPS_SD",
]
