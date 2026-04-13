"""
sensitivity.py
==============
Generates sensitivity tables and heatmaps for the LBO model.

What is Sensitivity Analysis?
───────────────────────────────
Instead of asking "what is the IRR?" (one answer),
we ask "how does IRR change as we vary two key inputs?"

This gives us a MATRIX of outcomes — a 5×5 or 6×6 grid
where each cell is an IRR under a different deal structure.

Why This is the Most Important Output:
────────────────────────────────────────
1. No assumption is certain. Entry multiples are negotiated.
   Exit multiples depend on market conditions 5 years away.
   A heatmap shows how ROBUST or FRAGILE the return thesis is.

2. It tells you: "Even if we're wrong on exit multiple by 1 turn,
   do we still clear the hurdle?" That's margin of safety thinking.

3. Investment committees use this to set LIMITS:
   "We will not pay more than 8.5x entry in any scenario"
   "We need at least 7x exit to underwrite this deal"

Two Heatmaps We Generate:
───────────────────────────
1. Entry Multiple × Exit Multiple → IRR
   The classic. Shows deal pricing sensitivity.

2. Revenue CAGR × EBITDA Margin → IRR
   Operational sensitivity. Shows how important execution is.

Color Convention (industry standard):
  🟢 Green  → IRR > 25%  (exceptional)
  🟡 Yellow → IRR 20-25% (good, clears hurdle)
  🟠 Orange → IRR 15-20% (marginal)
  🔴 Red    → IRR < 15%  (below hurdle — avoid)
"""

import copy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from assumptions import DealAssumptions
from returns import calculate_returns


def run_sensitivity(base_assumptions: DealAssumptions,
                    var1_name: str,
                    var1_values: list,
                    var2_name: str,
                    var2_values: list,
                    output_metric: str = "irr") -> pd.DataFrame:
    """
    Run a 2-variable sensitivity sweep and return a results matrix.

    Parameters
    ----------
    base_assumptions : DealAssumptions — starting point
    var1_name        : attribute name for rows (e.g. "entry_ev_multiple")
    var1_values      : list of values to test for var1 (rows)
    var2_name        : attribute name for columns (e.g. "exit_ev_multiple")
    var2_values      : list of values to test for var2 (columns)
    output_metric    : "irr" or "mom" — what to fill the matrix with

    Returns
    -------
    pd.DataFrame — matrix of output_metric values
    """
    matrix = []

    for v1 in var1_values:
        row = []
        for v2 in var2_values:
            # Clone assumptions and override both variables
            scenario = copy.deepcopy(base_assumptions)
            setattr(scenario, var1_name, v1)
            setattr(scenario, var2_name, v2)

            try:
                results = calculate_returns(scenario)
                if output_metric == "irr":
                    value = round(results["irr"] * 100, 1)   # as %
                elif output_metric == "mom":
                    value = round(results["mom"], 2)
                else:
                    value = round(results[output_metric], 1)
            except Exception:
                # If model breaks (e.g. negative FCF can't service debt), mark as NaN
                value = np.nan

            row.append(value)
        matrix.append(row)

    # Format axis labels cleanly
    row_labels = [f"{v}x" if "multiple" in var1_name else
                  f"{v*100:.0f}%" if any(k in var1_name for k in ["cagr", "margin", "rate"]) else
                  str(v) for v in var1_values]

    col_labels = [f"{v}x" if "multiple" in var2_name else
                  f"{v*100:.0f}%" if any(k in var2_name for k in ["cagr", "margin", "rate"]) else
                  str(v) for v in var2_values]

    df = pd.DataFrame(matrix, index=row_labels, columns=col_labels)
    df.index.name   = _label(var1_name)
    df.columns.name = _label(var2_name)

    return df


def _label(attr_name: str) -> str:
    """Convert attribute name to a clean display label"""
    labels = {
        "entry_ev_multiple" : "Entry EV/EBITDA Multiple →",
        "exit_ev_multiple"  : "Exit EV/EBITDA Multiple →",
        "revenue_cagr"      : "Revenue CAGR →",
        "ebitda_margin"     : "EBITDA Margin →",
        "interest_rate"     : "Interest Rate →",
        "debt_pct"          : "Debt % →",
        "holding_period"    : "Holding Period →",
    }
    return labels.get(attr_name, attr_name)


def _build_irr_colormap():
    """
    Custom colormap: Red → Orange → Yellow → Green
    Anchored to PE return thresholds.
    """
    colors_list = [
        (0.00, "#8B0000"),   # Dark red  — deeply negative / terrible
        (0.30, "#e74c3c"),   # Red       — below 10% IRR
        (0.50, "#e67e22"),   # Orange    — 10-15% IRR (marginal)
        (0.65, "#f1c40f"),   # Yellow    — 15-20% IRR
        (0.78, "#2ecc71"),   # Green     — 20-25% IRR (good)
        (1.00, "#1a7a3c"),   # Dark green — 25%+ IRR (exceptional)
    ]
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "pe_returns",
        [(pos, color) for pos, color in colors_list]
    )
    return cmap


def plot_heatmap(df: pd.DataFrame,
                 title: str,
                 metric_label: str = "IRR (%)",
                 base_row: str = None,
                 base_col: str = None,
                 save_path: str = None):
    """
    Plot a styled heatmap with:
    - Color-coded cells (red → green by return quality)
    - PE hurdle annotations
    - Base case cell highlighted
    - Clean dark theme
    """
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor("#0f0f0f")
    ax.set_facecolor("#0f0f0f")

    cmap = _build_irr_colormap()

    # Determine color range anchored to PE thresholds
    all_vals = df.values.flatten()
    all_vals = all_vals[~np.isnan(all_vals)]
    vmin = max(0, float(np.min(all_vals)) - 2)
    vmax = float(np.max(all_vals)) + 2

    sns.heatmap(
        df,
        ax=ax,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        annot=True,
        fmt=".1f",
        annot_kws={"size": 11, "weight": "bold", "color": "white"},
        linewidths=1.5,
        linecolor="#0f0f0f",
        cbar_kws={"label": metric_label, "shrink": 0.8},
    )

    # ── Style the colorbar ─────────────────────────────────
    cbar = ax.collections[0].colorbar
    cbar.ax.yaxis.label.set_color("white")
    cbar.ax.tick_params(colors="white")

    # ── Highlight base case cell ───────────────────────────
    if base_row and base_col:
        try:
            row_idx = list(df.index).index(base_row)
            col_idx = list(df.columns).index(base_col)
            ax.add_patch(plt.Rectangle(
                (col_idx, row_idx), 1, 1,
                fill=False, edgecolor="white",
                lw=3, zorder=5
            ))
            ax.text(col_idx + 0.5, row_idx - 0.15,
                    "BASE", color="white", fontsize=8,
                    ha="center", fontweight="bold")
        except ValueError:
            pass

    # ── Add PE hurdle annotation ───────────────────────────
    fig.text(
        0.13, -0.02,
        "🟢 >25% Exceptional   🟡 20–25% Good (meets hurdle)   "
        "🟠 15–20% Marginal   🔴 <15% Below hurdle",
        color="#aaaaaa", fontsize=9, ha="left"
    )

    # ── Axis styling ───────────────────────────────────────
    ax.set_title(title, color="white", fontsize=14,
                 fontweight="bold", pad=16)
    ax.tick_params(axis="x", colors="white", labelsize=10)
    ax.tick_params(axis="y", colors="white", labelsize=10, rotation=0)
    ax.set_xlabel(df.columns.name, color="#aaaaaa",
                  fontsize=11, labelpad=10)
    ax.set_ylabel(df.index.name, color="#aaaaaa",
                  fontsize=11, labelpad=10)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"  Chart saved -> {save_path}")

    plt.show()
    return fig


def run_all_sensitivities(assumptions: DealAssumptions,
                          save_dir: str = "../outputs/charts/"):
    """
    Run and plot both core sensitivity analyses.

    Heatmap 1: Entry Multiple × Exit Multiple → IRR
    Heatmap 2: Revenue CAGR × EBITDA Margin  → IRR
    """

    print("\n  Running sensitivity analysis...")

    # ── Heatmap 1: Deal Pricing Sensitivity ───────────────
    # Most important for deal structuring decisions
    # "How much can we pay?" and "What exit do we need?"
    print("  [1/2] Entry Multiple × Exit Multiple...")

    entry_multiples = [6.0, 7.0, 8.0, 9.0, 10.0, 11.0]  # rows
    exit_multiples  = [7.0, 8.0, 9.0, 10.0, 11.0]        # columns

    heatmap1 = run_sensitivity(
        assumptions,
        var1_name   = "entry_ev_multiple",
        var1_values = entry_multiples,
        var2_name   = "exit_ev_multiple",
        var2_values = exit_multiples,
        output_metric = "irr"
    )

    print("\n  HEATMAP 1: Entry × Exit Multiple (IRR %)")
    print("  " + "=" * 55)
    print(heatmap1.to_string())

    plot_heatmap(
        heatmap1,
        title      = f"IRR Sensitivity: Entry vs Exit Multiple\n{assumptions.company_name} LBO",
        base_row   = f"{assumptions.entry_ev_multiple}x",
        base_col   = f"{assumptions.exit_ev_multiple}x",
        save_path  = f"{save_dir}heatmap_entry_exit.png"
    )

    # ── Heatmap 2: Operational Sensitivity ────────────────
    # "Even if we pay the right price, can management execute?"
    # Tests how sensitive returns are to operational performance
    print("\n  [2/2] Revenue CAGR × EBITDA Margin...")

    rev_cagrs      = [0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 0.18]
    ebitda_margins = [0.12, 0.14, 0.16, 0.18, 0.20, 0.22]

    heatmap2 = run_sensitivity(
        assumptions,
        var1_name   = "revenue_cagr",
        var1_values = rev_cagrs,
        var2_name   = "ebitda_margin",
        var2_values = ebitda_margins,
        output_metric = "irr"
    )

    print("\n  HEATMAP 2: Revenue CAGR × EBITDA Margin (IRR %)")
    print("  " + "=" * 55)
    print(heatmap2.to_string())

    plot_heatmap(
        heatmap2,
        title      = f"IRR Sensitivity: Revenue Growth vs EBITDA Margin\n{assumptions.company_name} LBO",
        base_row   = f"{assumptions.revenue_cagr*100:.0f}%",
        base_col   = f"{assumptions.ebitda_margin*100:.0f}%",
        save_path  = f"{save_dir}heatmap_operations.png"
    )

    print("\n  Sensitivity analysis complete.")
    return heatmap1, heatmap2


# ── Run directly to test ───────────────────────────────────
if __name__ == "__main__":
    import os
    os.makedirs("../outputs/charts", exist_ok=True)

    deal = DealAssumptions()
    deal.summary()

    h1, h2 = run_all_sensitivities(deal)
