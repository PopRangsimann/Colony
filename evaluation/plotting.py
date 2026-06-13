"""
Config-Driven Figure Generation
=================================
Clean style matching reference publication figures.
Solid lines, filled markers, light dashed grid, all spines.
"""

from __future__ import annotations

import csv
import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from evaluation import sim_config

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")
DATA_DIR = os.path.join(RESULTS_DIR, "data")

# ─── Global Style — match reference figure ─────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica", "sans-serif"],
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 13,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 11,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "axes.linewidth": 1.0,
    "axes.edgecolor": "black",
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.direction": "out",
    "ytick.direction": "out",
})

# Scheme visual config — matching reference image style
# Order: Ref first (orange, green, red), then Proposed (blue)
SCHEME_STYLE = {
    "Ref[3]": {
        "color": "#ff7f0e",   # orange
        "marker": "s",        # square
    },
    "Ref[6]": {
        "color": "#2ca02c",   # green
        "marker": "^",        # triangle
    },
    "Ref[20]": {
        "color": "#d62728",   # red
        "marker": "D",        # diamond
    },
    "Ours": {
        "color": "#1f77b4",   # blue
        "marker": "o",        # circle
    },
}

# Map old scheme names to new display names
DISPLAY_NAMES = {
    "Ala'anzy et al.":      "Ref[3]",
    "Jasim & Al-Raweshidy": "Ref[6]",
    "Kashyap et al.":       "Ref[20]",
    "Proposed":             "Ours",
}


def _ensure_results_dir():
    os.makedirs(FIGURES_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)


def plot_experiment(
    summary: Dict[str, Dict[str, Any]],
    title: str,
    xlabel: str,
    ylabel: str,
    filename: str,
    logx: bool = False,
    ylim: tuple = None,
):
    """
    Plot a single experiment figure with all schemes.

    Parameters
    ----------
    summary : dict
        {scheme_name: {"x": [...], "mean": [...], "std": [...]}}
    title : str
        Figure title.
    xlabel, ylabel : str
        Axis labels.
    filename : str
        Base filename (without extension).
    logx : bool
        Whether to use log scale on x-axis.
    ylim : tuple, optional
        Manual y-axis limits (ymin, ymax).
    """
    _ensure_results_dir()

    fig, ax = plt.subplots(figsize=(8, 5.5))

    # Plot each scheme
    for scheme_name, data in summary.items():
        x = np.array(data["x"])
        y = np.array(data["mean"])

        # Get display name
        display = DISPLAY_NAMES.get(scheme_name, scheme_name)
        style = SCHEME_STYLE.get(display, {"color": "#666666", "marker": "o"})

        ax.plot(
            x, y,
            label=display,
            color=style["color"],
            marker=style["marker"],
            linestyle="-",         # all solid lines
            linewidth=2.0,
            markersize=8,
            markeredgecolor=style["color"],
            markerfacecolor=style["color"],
            zorder=3,
        )

    # Axis labels (no title on plot — cleaner)
    ax.set_xlabel(xlabel, fontweight="bold")
    ax.set_ylabel(ylabel, fontweight="bold")

    if logx:
        ax.set_xscale("log")
        ax.xaxis.set_major_formatter(mticker.ScalarFormatter())
        ax.xaxis.set_minor_formatter(mticker.NullFormatter())

    if ylim:
        ax.set_ylim(ylim)

    # Light dashed grid — matching reference
    ax.grid(True, which="major", linestyle="--", alpha=0.3, linewidth=0.6,
            color="#cccccc")
    ax.set_axisbelow(True)

    # Keep ALL spines visible (matching reference)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.0)
        spine.set_color("black")

    # Legend — upper right with thin border, matching reference
    legend = ax.legend(
        loc="best",
        frameon=True,
        fancybox=False,
        edgecolor="#cccccc",
        framealpha=1.0,
        borderpad=0.5,
        handlelength=1.8,
        labelspacing=0.4,
    )
    legend.get_frame().set_linewidth(0.6)

    fig.tight_layout(pad=1.5)

    # Save figure
    png_path = os.path.join(FIGURES_DIR, f"{filename}.png")
    fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {png_path}")

    # Save CSV
    csv_path = os.path.join(DATA_DIR, f"{filename}.csv")
    _save_csv(summary, csv_path)
    print(f"  Saved: {csv_path}")

    return png_path


def _save_csv(summary: Dict[str, Dict], csv_path: str):
    """Save raw data as CSV for reviewer reproducibility."""
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["scheme", "x_value", "mean", "std"])
        for scheme_name, data in summary.items():
            display = DISPLAY_NAMES.get(scheme_name, scheme_name)
            for i, x_val in enumerate(data["x"]):
                writer.writerow([
                    display,
                    x_val,
                    f"{data['mean'][i]:.6f}",
                    f"{data['std'][i]:.6f}",
                ])
