"""
scenarios.py
============
Runs Bull / Base / Bear scenario analysis on the LBO model.

Why Scenarios Matter in PE:
────────────────────────────
A Base Case tells you the expected return.
A Bear Case tells you if you can SURVIVE being wrong.
A Bull Case tells you the UPSIDE if things go better than expected.

PE investment committees don't just ask "what's the IRR?"
They ask "what's the IRR if revenue growth is half of what we expect?"
or "what if margins compress due to competition?"

The Bear Case is the most important one. If the Bear Case
still gives you a positive return and manageable debt, the deal
has a MARGIN OF SAFETY — that's what makes it investable.

Scenario Design Principle:
───────────────────────────
Don't just tweak one variable. Real scenarios change multiple
assumptions together — because in reality, bad times hit revenue,
margins AND exit multiples simultaneously (they're correlated).
That's what makes a Bear Case a true stress test.
"""

import copy
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from assumptions import DealAssumptions
from returns import calculate_returns


# ── Scenario Definitions ──────────────────────────────────
SCENARIOS = {

    "Bull": {
        "revenue_cagr"     : 0.18,
        "ebitda_margin"    : 0.22,
        "exit_ev_multiple" : 10.0,
        "interest_rate"    : 0.09,
        "description"      : "Strong growth, margin expansion, premium exit",
    },

    "Base": {
        "revenue_cagr"     : 0.12,
        "ebitda_margin"    : 0.18,
        "exit_ev_multiple" : 9.0,
        "interest_rate"    : 0.10,
        "description"      : "Management projections, stable operations",
    },

    "Bear": {
        "revenue_cagr"     : 0.06,
        "ebitda_margin"    : 0.14,
        "exit_ev_multiple" : 7.0,
        "interest_rate"    : 0.11,
        "description"      : "Slow growth, margin compression, market de-rating",
    },

    "Distressed": {
        "revenue_cagr"     : 0.02,
        "ebitda_margin"    : 0.11,
        "exit_ev_multiple" : 5.5,
        "interest_rate"    : 0.12,
        "description"      : "Near-recessionary conditions, survival mode",
    },
}


def run_all_scenarios(base_assumptions: DealAssumptions) -> dict:
    """
    Run all 4 scenarios and collect results.
    For each scenario: copy base assumptions → override → run model → store.
    """
    all_results = {}

    print("\n  Running scenario analysis...")
    print("  " + "-" * 60)

    for name, overrides in SCENARIOS.items():
        scenario_assumptions = copy.deepcopy(base_assumptions)
        description = overrides.get("description", "")

        for key, value in overrides.items():
            if key != "description":
                setattr(scenario_assumptions, key, value)

        results = calculate_returns(scenario_assumptions)
        results["scenario_assumptions"] = scenario_assumptions
        results["description"] = description
        all_results[name] = results

        irr_pct = results["irr"] * 100
        mom     = results["mom"]
        print(f"  {name:<14} | IRR: {irr_pct:>6.1f}%  | MoM: {mom:.2f}x  | {description}")

    print("  " + "-" * 60)
    return all_results


def build_scenario_table(all_results: dict) -> pd.DataFrame:
    """Build a summary comparison table — what goes in the investment memo."""
    rows = []
    for name, res in all_results.items():
        s = res["scenario_assumptions"]
        rows.append({
            "Scenario"             : name,
            "Revenue CAGR"         : f"{s.revenue_cagr*100:.0f}%",
            "EBITDA Margin"        : f"{s.ebitda_margin*100:.0f}%",
            "Exit Multiple"        : f"{s.exit_ev_multiple:.1f}x",
            "Exit EBITDA (Cr)"     : round(res["exit_ebitda"], 1),
            "Exit EV (Cr)"         : round(res["exit_ev"], 1),
            "Remaining Debt (Cr)"  : round(res["exit_debt"], 1),
            "Exit Equity (Cr)"     : round(res["exit_equity"], 1),
            "IRR"                  : f"{res['irr']*100:.1f}%",
            "MoM"                  : f"{res['mom']:.2f}x",
        })
    return pd.DataFrame(rows).set_index("Scenario")


def plot_scenario_comparison(all_results: dict, save_path: str = None):
    """
    2-panel chart:
    Left  — IRR bar chart with PE hurdle rate reference lines
    Right — Equity invested vs exit value across scenarios
    """
    scenarios     = list(all_results.keys())
    irrs          = [all_results[s]["irr"] * 100 for s in scenarios]
    moms          = [all_results[s]["mom"] for s in scenarios]
    exit_equities = [all_results[s]["exit_equity"] for s in scenarios]
    entry_eq      = list(all_results.values())[0]["scenario_assumptions"].equity_invested

    colors = ["#2ecc71", "#3498db", "#e67e22", "#e74c3c"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor("#0f0f0f")

    for ax in axes:
        ax.set_facecolor("#1a1a1a")
        ax.tick_params(colors="white")
        for spine in ["bottom", "left"]:
            ax.spines[spine].set_color("#444")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # ── Panel 1: IRR Bar Chart ─────────────────────────────
    ax1 = axes[0]
    bars = ax1.bar(scenarios, irrs, color=colors,
                   width=0.5, zorder=3, edgecolor="#0f0f0f", linewidth=1.5)

    ax1.axhline(y=20, color="#f39c12", linewidth=1.8,
                linestyle="--", zorder=4, label="PE Hurdle Rate (20%)")
    ax1.axhline(y=25, color="#27ae60", linewidth=1.2,
                linestyle=":", zorder=4, label="Strong Return (25%)")

    for bar, irr in zip(bars, irrs):
        ax1.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 0.4,
                 f"{irr:.1f}%",
                 ha="center", va="bottom",
                 color="white", fontsize=11, fontweight="bold")

    ax1.set_title("IRR by Scenario", color="white",
                  fontsize=13, fontweight="bold", pad=12)
    ax1.set_ylabel("IRR (%)", color="#aaaaaa", fontsize=10)
    ax1.set_ylim(0, max(irrs) * 1.35)
    ax1.yaxis.label.set_color("#aaaaaa")
    ax1.tick_params(axis="x", colors="white")
    ax1.legend(facecolor="#2a2a2a", edgecolor="#444",
               labelcolor="white", fontsize=9)
    ax1.grid(axis="y", color="#2a2a2a", zorder=0)

    # ── Panel 2: Invested vs Exit Equity ──────────────────
    ax2 = axes[1]
    x     = np.arange(len(scenarios))
    width = 0.35

    ax2.bar(x - width / 2, [entry_eq] * len(scenarios),
            width, label=f"Equity Invested (₹{entry_eq:.0f}Cr)",
            color="#555555", zorder=3, edgecolor="#0f0f0f", linewidth=1.5)

    exit_bars = ax2.bar(x + width / 2, exit_equities,
                        width, label="Exit Equity",
                        color=colors, zorder=3,
                        edgecolor="#0f0f0f", linewidth=1.5)

    for bar, mom in zip(exit_bars, moms):
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 5,
                 f"{mom:.2f}x",
                 ha="center", va="bottom",
                 color="white", fontsize=10, fontweight="bold")

    ax2.set_title("Equity: Invested vs Exit Value",
                  color="white", fontsize=13, fontweight="bold", pad=12)
    ax2.set_ylabel("₹ Crore", color="#aaaaaa", fontsize=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels(scenarios, color="white")
    ax2.yaxis.label.set_color("#aaaaaa")
    ax2.legend(facecolor="#2a2a2a", edgecolor="#444",
               labelcolor="white", fontsize=9)
    ax2.grid(axis="y", color="#2a2a2a", zorder=0)

    company = list(all_results.values())[0]["scenario_assumptions"].company_name
    fig.suptitle(f"LBO Scenario Analysis — {company}",
                 color="white", fontsize=15, fontweight="bold", y=1.02)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"\n  Chart saved -> {save_path}")

    plt.show()
    return fig


# ── Run directly to test ───────────────────────────────────
if __name__ == "__main__":
    deal = DealAssumptions()
    deal.summary()

    all_results = run_all_scenarios(deal)

    table = build_scenario_table(all_results)
    print("\n  SCENARIO COMPARISON TABLE")
    print("  " + "=" * 75)
    print(table.to_string())

    plot_scenario_comparison(
        all_results,
        save_path="../outputs/charts/scenarios.png"
    )
