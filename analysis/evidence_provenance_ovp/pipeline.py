"""pipeline.py — Evidence Provenance Stage 0: produce the y-free screen input.

NQ-open QUESTIONS  ->  BM25 top-k (scores)  ->  Qwen RAG answer + length-normalized log-prob
->  entropy (sum-normalized top-k scores)  ->  stage0_screen_input.csv (4 columns, asserted).

FIREWALL (structural):
  * This file imports NO grader and accesses NO gold/correctness. (`import grader` here = broken firewall.)
  * Only the NQ-open QUESTION field is read; `ex["answer"]` is never selected, used, or written.
  * The screen-input writer asserts EXACTLY the four pinned columns at write time AND re-reads the
    header to confirm — a stray outcome column cannot be written, let alone read.
"""
import csv
import json
import numpy as np
import torch
from datasets import load_dataset
from pyserini.search.lucene import LuceneSearcher
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

import config

# NO `import grader`.  NO gold/correctness access anywhere in this module.


# ---- passage text extraction (confirmed against pyserini 2.3.0) --------------------------------
# A ScoredDoc carries only docid/score; the document text is fetched via searcher.doc(docid).raw(),
# which returns JSON {"id":..., "contents":"<title + passage>"}. (contents() returns None here.)
def _passage_text(searcher, hit):
    d = searcher.doc(hit.docid)
    if d is None:
        return ""
    raw = d.raw()
    if not raw:
        return ""
    try:
        return json.loads(raw).get("contents", raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def sum_normalized_entropy(scores):
    """Shannon entropy (nats) of the sum-normalized top-k BM25 scores."""
    s = np.asarray(scores, dtype=float)
    total = s.sum()
    if total <= 0:
        return 0.0
    p = s / total
    p = p[p > 0]
    return float(-(p * np.log(p)).sum())


# ---- [VERIFY #2] Qwen answer + length-normalized confidence ------------------------------------
# Uses the chat template (continuity with the detector arc's Qwen path) with the blessed RAG prompt
# as the user turn; greedy; confidence = mean per-token log-prob over the generated answer tokens.
# Confirm the log-prob extraction (output_scores) against your install with the probe.
def answer_and_confidence(model, tok, prompt):
    messages = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    enc = tok(text, return_tensors="pt", truncation=True, max_length=8192).to(model.device)
    with torch.no_grad():
        out = model.generate(
            **enc, do_sample=False, max_new_tokens=config.MAX_NEW_TOKENS,
            return_dict_in_generate=True, output_scores=True,
            pad_token_id=(tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id),
        )
    gen_ids = out.sequences[0, enc["input_ids"].shape[1]:]
    logps = []
    for step, logits in enumerate(out.scores):
        if step >= len(gen_ids):
            break
        logp = torch.log_softmax(logits[0].float(), dim=-1)[gen_ids[step]].item()
        logps.append(logp)
    answer = tok.decode(gen_ids, skip_special_tokens=True).strip()
    confidence = float(np.mean(logps)) if logps else float("nan")  # length-normalized log-prob
    return answer, confidence


def write_screen_input(rows):
    """The firewall, executable: exactly the four pinned columns, asserted at write and re-read."""
    assert config.SCREEN_INPUT_COLUMNS == ["qid", "entropy", "confidence", "max_retrieval_score"]
    with open(config.SCREEN_INPUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(config.SCREEN_INPUT_COLUMNS)
        for r in rows:
            assert len(r) == 4, "screen-input row must have exactly four fields"
            w.writerow(r)
    with open(config.SCREEN_INPUT_PATH, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == config.SCREEN_INPUT_COLUMNS, \
        "FIREWALL: written header %r != %r" % (header, config.SCREEN_INPUT_COLUMNS)


def build(limit=None):
    searcher = LuceneSearcher.from_prebuilt_index(config.INDEX)
    searcher.set_bm25(config.BM25_K1, config.BM25_B)

    tok = AutoTokenizer.from_pretrained(config.GENERATOR, revision=config.GENERATOR_REVISION)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(
        config.GENERATOR, revision=config.GENERATOR_REVISION,
        quantization_config=bnb, device_map="cuda").eval()
    _resolved = getattr(model.config, "_commit_hash", None)
    if _resolved and _resolved != config.GENERATOR_REVISION:
        raise SystemExit("ABORT: resolved generator revision %s != pinned %s"
                         % (_resolved, config.GENERATOR_REVISION))

    ds = load_dataset(config.DATASET, split=config.SPLIT, revision=config.DATASET_REVISION)
    rows = []
    for qid, ex in enumerate(ds):
        if limit is not None and qid >= limit:
            break
        question = ex["question"]                 # QUESTION ONLY; ex["answer"] is never touched
        hits = searcher.search(question, k=config.TOP_K)
        scores = [h.score for h in hits]
        entropy = sum_normalized_entropy(scores)
        max_score = max(scores) if scores else 0.0
        passages = "\n\n".join(_passage_text(searcher, h) for h in hits)
        prompt = config.PROMPT_TEMPLATE.format(passages=passages, question=question)
        _answer, confidence = answer_and_confidence(model, tok, prompt)   # answer is discarded here
        rows.append((qid, entropy, confidence, max_score))
        if (qid + 1) % 100 == 0:
            print("[pipeline] %d questions processed" % (qid + 1))

    write_screen_input(rows)
    print("[pipeline] wrote %s  (%d rows, 4 columns asserted)" % (config.SCREEN_INPUT_PATH, len(rows)))


if __name__ == "__main__":
    import sys
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None   # e.g. `python pipeline.py 5` for a smoke run
    build(limit=lim)
