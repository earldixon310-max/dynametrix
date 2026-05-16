"""
Render a reliability diagram from a case study's calibration_summary.json.

Pre-registered evaluation methodology — visualization tool.

The script is read-only against the input JSON. It does not modify any
locked pre-registered output. It produces additional visualization
artifacts (PNG, SVG) that can be committed alongside the existing
deliverables for a case study, or embedded in a result document
authored under the convention specified in docs/RESULT_TEMPLATE.md.

Style:
  - Clean white background, minimal chartjunk, institutional voice
  - Blue markers for bins that PASS the Wilson criterion
  - Burnt-rust markers for bins that FAIL
  - Subdued gray markers for bins EXCLUDED (n < 30)
  - Marker size proportional to sqrt(bin sample count)
  - Wilson 95% confidence interval shown as vertical error bars
  - Dashed gray diagonal indicating perfect calibration (y = x)
  - Title: model name; subtitle: revision · n · outcome

Usage:
  python render_reliability_diagram.py <path_to_calibration_summary.json>
  python render_reliability_diagram.py <path> --output <output_prefix>

Outputs (in the same folder as the input by default):
  reliability_diagram.png
  reliability_diagram.svg

Examples:
  python render_reliability_diagram.py \\
      case_studies/distilbert_sst2/calibration_summary.json

  python render_reliability_diagram.py \\
      case_studies/toxic_bert/calibration_summary.json \\
      --output case_studies/toxic_bert/reliability_diagram

Requires: matplotlib (lightweight; tools/requirements.txt).
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


# --- Style constants ---

PASS_COLOR = "#1A3A5C"        # deep navy — accent color for pass
FAIL_COLOR = "#A0421C"        # burnt rust — accent color for fail
EXCLUDED_COLOR = "#888888"    # subdued gray — for n < 30 bins
DIAGONAL_COLOR = "#BBBBBB"    # dashed perfect-calibration line
ERRORBAR_COLOR = "#444444"    # dark gray for Wilson CI bars

FIG_W, FIG_H = 8.0, 7.0       # inches
FIG_DPI = 150                 # publication-quality PNG

MARKER_MIN_SIZE = 30
MARKER_MAX_SIZE = 600

EXCLUDED_MARKER_SIZE = 30
EXCLUDED_MARKER_ALPHA = 0.45


def scale_marker_size(n: int, n_max: int) -> float:
    """Scale marker area proportional to sqrt(n / n_max)."""
    if n_max <= 0:
        return MARKER_MIN_SIZE
    frac = (n / n_max) ** 0.5
    return MARKER_MIN_SIZE + frac * (MARKER_MAX_SIZE - MARKER_MIN_SIZE)


def _short_revision(rev) -> str:
    if not rev:
        return ""
    s = str(rev)
    return s[:8] if len(s) > 8 else s


def render(summary_path: Path, output_prefix: Path) -> None:
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    bins = summary.get("bins", [])
    if not bins:
        print(f"ERROR: no 'bins' field in {summary_path}")
        sys.exit(1)

    model_name = summary.get("model_name", "(unknown model)")
    revision = _short_revision(summary.get("model_revision", ""))
    n_examples = summary.get("n_examples", "")
    outcome = summary.get("outcome", "(outcome unrecorded)")

    # For sqrt size scaling, exclude empty bins from n_max
    populated_ns = [b["n"] for b in bins if b.get("n", 0) > 0]
    n_max = max(populated_ns) if populated_ns else 1

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=FIG_DPI)

    # Perfect-calibration diagonal
    ax.plot(
        [0, 1], [0, 1],
        linestyle="--",
        color=DIAGONAL_COLOR,
        linewidth=1.0,
        zorder=1,
    )

    # Plot each bin
    saw_pass = False
    saw_fail = False
    saw_excluded = False
    for b in bins:
        n = b.get("n", 0)
        mp = b.get("mean_pred")
        of = b.get("observed_freq")

        if n == 0 or mp is None or of is None:
            continue

        excluded = bool(b.get("excluded", False))

        if excluded:
            ax.scatter(
                [mp], [of],
                s=EXCLUDED_MARKER_SIZE,
                color=EXCLUDED_COLOR,
                alpha=EXCLUDED_MARKER_ALPHA,
                edgecolors="none",
                zorder=2,
            )
            saw_excluded = True
            continue

        wlo = b.get("wilson_lo")
        whi = b.get("wilson_hi")
        passes = bool(b.get("passes", False))
        color = PASS_COLOR if passes else FAIL_COLOR

        # Wilson CI as vertical error bars
        if wlo is not None and whi is not None:
            ax.errorbar(
                [mp], [of],
                yerr=[[max(0.0, of - wlo)], [max(0.0, whi - of)]],
                fmt="none",
                ecolor=ERRORBAR_COLOR,
                elinewidth=1.2,
                capsize=5,
                zorder=3,
            )

        ax.scatter(
            [mp], [of],
            s=scale_marker_size(n, n_max),
            color=color,
            edgecolors="white",
            linewidths=1.2,
            zorder=4,
        )

        if passes:
            saw_pass = True
        else:
            saw_fail = True

    # Axes
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("Predicted probability", fontsize=12)
    ax.set_ylabel("Observed frequency", fontsize=12)
    ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_aspect("equal")

    # Grid
    ax.grid(True, linestyle=":", color="#DDDDDD", linewidth=0.8, alpha=0.6)
    ax.set_axisbelow(True)

    # Title (left-aligned, institutional voice)
    ax.set_title(
        f"Reliability — {model_name}",
        fontsize=13,
        loc="left",
        pad=20,
    )

    # Subtitle line under title (revision, n, outcome)
    subtitle_parts = []
    if revision:
        subtitle_parts.append(f"revision {revision}")
    if n_examples:
        subtitle_parts.append(f"n = {n_examples}")
    if outcome:
        subtitle_parts.append(f"outcome: {outcome}")
    subtitle = " · ".join(subtitle_parts)
    ax.text(
        0.0, 1.02,
        subtitle,
        transform=ax.transAxes,
        fontsize=10,
        color="#555555",
        verticalalignment="bottom",
    )

    # Legend — only include the categories actually present in the data
    legend_handles = []
    if saw_pass:
        legend_handles.append(
            Line2D(
                [], [],
                marker="o",
                color="white",
                markerfacecolor=PASS_COLOR,
                markeredgecolor="white",
                markersize=10,
                linewidth=0,
                label="Bin passes Wilson criterion",
            )
        )
    if saw_fail:
        legend_handles.append(
            Line2D(
                [], [],
                marker="o",
                color="white",
                markerfacecolor=FAIL_COLOR,
                markeredgecolor="white",
                markersize=10,
                linewidth=0,
                label="Bin fails Wilson criterion",
            )
        )
    if saw_excluded:
        legend_handles.append(
            Line2D(
                [], [],
                marker="o",
                color="white",
                markerfacecolor=EXCLUDED_COLOR,
                markeredgecolor="none",
                alpha=EXCLUDED_MARKER_ALPHA,
                markersize=7,
                linewidth=0,
                label="Bin excluded (n < 30)",
            )
        )
    legend_handles.append(
        Line2D(
            [], [],
            linestyle="--",
            color=DIAGONAL_COLOR,
            linewidth=1,
            label="Perfect calibration",
        )
    )

    ax.legend(
        handles=legend_handles,
        loc="lower right",
        fontsize=9,
        frameon=True,
        edgecolor="#CCCCCC",
        facecolor="white",
        framealpha=0.95,
    )

    plt.tight_layout()

    png_path = output_prefix.with_suffix(".png")
    svg_path = output_prefix.with_suffix(".svg")
    fig.savefig(png_path, dpi=FIG_DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(svg_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Wrote {png_path}")
    print(f"Wrote {svg_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Render a reliability diagram from a calibration_summary.json.",
    )
    parser.add_argument(
        "summary",
        type=Path,
        help="Path to calibration_summary.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file prefix (without extension). "
             "Default: 'reliability_diagram' in the same folder as the input.",
    )
    args = parser.parse_args()

    if not args.summary.exists():
        print(f"ERROR: input file not found: {args.summary}")
        sys.exit(1)

    output_prefix = args.output
    if output_prefix is None:
        output_prefix = args.summary.parent / "reliability_diagram"

    render(args.summary, output_prefix)


if __name__ == "__main__":
    main()