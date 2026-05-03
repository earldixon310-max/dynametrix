"""Confidence-language tests. Fail the build if forbidden tokens appear."""
import re
from pathlib import Path

import pytest

from app.utils.copy import APPROVED, FORBIDDEN_TOKENS, recommended_action, time_to_impact


def test_no_forbidden_tokens_in_approved():
    for k, v in APPROVED.items():
        for tok in FORBIDDEN_TOKENS:
            assert tok.lower() not in v.lower(), f"Forbidden token '{tok}' in approved string '{k}'"


def test_recommended_action_low_confidence_is_passive():
    s = recommended_action("commitment", 0.3).lower()
    assert "no action required" in s


def test_time_to_impact_handles_none():
    assert "not yet estimable" in time_to_impact(None).lower()


def test_no_overclaiming_in_repo():
    """Walk the backend source for overclaiming strings."""
    root = Path(__file__).resolve().parents[1] / "app"
    pattern = re.compile("|".join(re.escape(t) for t in FORBIDDEN_TOKENS), re.I)
    offenders = []
    for p in root.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        # The FORBIDDEN_TOKENS tuple itself lives in copy.py — skip self-reference there.
        if p.name == "copy.py":
            continue
        for m in pattern.finditer(text):
            offenders.append(f"{p}:{m.group(0)}")
    assert not offenders, "Overclaiming language found:\n" + "\n".join(offenders)
