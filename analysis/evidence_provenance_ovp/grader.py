"""grader.py — correctness scoring for Stage 2 (SEALED). NOT part of Stage 0.

This module is the firewall made physical: gold answers and the notion of "correct" live ONLY here.
The Stage 0 path (config.py / pipeline.py / screen.py) imports NONE of it, so no Stage 0 code can
read `y`. Grading is invoked only at the later, sealed candidate run — never during the feasibility
screen. If you find an `import grader` anywhere on the Stage 0 path, the firewall is broken.
"""
import re
import string


def _normalize(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in string.punctuation)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def is_correct(predicted_answer: str, gold_answers) -> bool:
    """Normalized exact match against any acceptable gold answer (Stage 2 target `y`)."""
    p = _normalize(predicted_answer)
    return any(p == _normalize(g) for g in gold_answers)
