"""
Approved confidence language. ALL user-facing strings about model output must
come from here. Do not invent new phrasings in routes, services, or templates.

Mirrored on the frontend at frontend/lib/copy.ts — keep in sync.
"""
from typing import Final

DISCLAIMER_SHORT: Final = (
    "This is not a deterministic weather forecast. Outputs are probabilistic and "
    "based on structural signal interpretation."
)

DISCLAIMER_LONG: Final = (
    "Dynametrix is a structural intelligence and early-warning support tool. "
    "It does not replace official forecasts, emergency management guidance, or "
    "meteorological advisories. Users should consult official sources such as the "
    "National Weather Service or local authorities. Outputs are probabilistic and "
    "based on structural signal interpretation."
)

# Approved phrases
APPROVED = {
    "structural_commitment": "Structural commitment detected",
    "elevated_organization": "Elevated structural organization",
    "estimated_lead_time": "Estimated lead time",
    "confidence_level": "Confidence level",
    "monitoring_posture": "Recommended monitoring posture",
    "pre_commitment": "Pre-commitment signature observed",
    "reconfiguration": "Structural reconfiguration in progress",
    "decay": "Structural decay detected",
    "false_start": "Transient organization (false start)",
    "quiet": "No structural commitment in current window",
}

# Forbidden tokens — used by tests to fail builds that introduce overclaiming.
FORBIDDEN_TOKENS = (
    "guaranteed",
    "will happen",
    "certain storm",
    "ai predicts",
    "ai prediction",
    "definitely",
    "100% chance",
)


def lifecycle_label(state: str) -> str:
    return {
        "quiet": "Quiet — no structural commitment",
        "organizing": "Organizing — structural metrics rising",
        "pre_commitment": "Pre-commitment signature observed",
        "committed": "Structural commitment detected",
        "reconfiguring": "Structural reconfiguration in progress",
        "decaying": "Structural decay — system unwinding",
    }.get(state, state)


def event_label(event_type: str) -> str:
    return {
        "pre_commitment": "Pre-commitment",
        "commitment": "Commitment",
        "reconfiguration": "Reconfiguration",
        "false_start": "False start",
        "decay": "Decay",
    }.get(event_type, event_type)


def time_to_impact(hours: float | None) -> str:
    """Conservative phrasing for lead time."""
    if hours is None:
        return "Lead time not yet estimable"
    if hours < 1:
        return "Estimated lead time: under 1 hour"
    if hours < 6:
        return f"Estimated lead time: ~{round(hours)} hours"
    if hours < 24:
        return f"Estimated lead time: ~{round(hours)} hours (within 1 day)"
    days = hours / 24.0
    return f"Estimated lead time: ~{days:.1f} days"


def recommended_action(event_type: str, confidence: float) -> str:
    """Posture, never a directive."""
    if confidence < 0.5:
        return "Maintain routine monitoring posture. No action required at this confidence level."
    if event_type in ("pre_commitment", "commitment"):
        return (
            "Heightened monitoring posture recommended. Review official forecasts and "
            "consider pre-positioning resources per your organization's playbook."
        )
    if event_type == "reconfiguration":
        return (
            "Reassess current operational posture. Conditions may shift away from prior expectations."
        )
    if event_type == "false_start":
        return "Stand down elevated posture. The structural signature did not commit."
    if event_type == "decay":
        return "Monitoring posture may be relaxed as structural organization unwinds."
    return "Maintain current monitoring posture."
