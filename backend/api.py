"""
api.py
======
FastAPI wrapper for the LBO calculation engine.
Exposes a single POST endpoint that accepts deal assumptions
and returns the full analysis as JSON.
"""

import sys
import os
import copy
import math
import warnings

warnings.filterwarnings("ignore")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

# Ensure local modules are importable
sys.path.insert(0, os.path.dirname(__file__))

from assumptions import DealAssumptions
from returns import calculate_returns
from scenarios import run_all_scenarios, build_scenario_table, SCENARIOS
from sensitivity import run_sensitivity

app = FastAPI(title="LBO Modeler API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Schema ─────────────────────────────────────────
class DealRequest(BaseModel):
    company_name: str = "Devyani International"
    base_year: int = 2024
    entry_year_ebitda: float = 120.0
    entry_ev_multiple: float = 8.0
    exit_ev_multiple: float = 9.0
    holding_period: int = 5
    debt_pct: float = 0.65
    interest_rate: float = 0.10
    revenue_base: float = 800.0
    revenue_cagr: float = 0.12
    ebitda_margin: float = 0.18
    depreciation_pct_revenue: float = 0.03
    capex_pct_revenue: float = 0.04
    change_in_wc_pct_revenue: float = 0.01
    tax_rate: float = 0.25
    cash_sweep: bool = True


def _safe_float(val):
    """Convert numpy/pandas values to JSON-safe Python floats."""
    if val is None:
        return None
    f = float(val)
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, 4)


def _df_to_dict(df):
    """Convert a pandas DataFrame to a JSON-serializable dict of dicts."""
    result = {}
    for idx in df.index:
        row = {}
        for col in df.columns:
            row[str(col)] = _safe_float(df.loc[idx, col])
        result[str(idx)] = row
    return result


def _build_assumptions(req: DealRequest) -> DealAssumptions:
    """Map request to DealAssumptions dataclass."""
    return DealAssumptions(
        company_name=req.company_name,
        base_year=req.base_year,
        entry_year_ebitda=req.entry_year_ebitda,
        entry_ev_multiple=req.entry_ev_multiple,
        exit_ev_multiple=req.exit_ev_multiple,
        holding_period=req.holding_period,
        debt_pct=req.debt_pct,
        interest_rate=req.interest_rate,
        revenue_base=req.revenue_base,
        revenue_cagr=req.revenue_cagr,
        ebitda_margin=req.ebitda_margin,
        depreciation_pct_revenue=req.depreciation_pct_revenue,
        capex_pct_revenue=req.capex_pct_revenue,
        change_in_wc_pct_revenue=req.change_in_wc_pct_revenue,
        tax_rate=req.tax_rate,
        cash_sweep=req.cash_sweep,
    )


@app.post("/api/calculate")
def calculate(req: DealRequest):
    """
    Run the full LBO analysis and return:
      - deal summary
      - base case returns
      - income statement
      - debt schedule
      - 4-scenario analysis
      - 2 sensitivity heatmaps
    """
    deal = _build_assumptions(req)

    # ── Base case returns ──────────────────────────────────
    results = calculate_returns(deal)

    irr_val = _safe_float(results["irr"])
    if irr_val is not None:
        irr_pct = round(irr_val * 100, 1)
    else:
        irr_pct = None

    # Verdict
    if irr_val is None:
        verdict = "N/A"
    elif irr_val >= 0.25:
        verdict = "STRONG DEAL — Exceeds PE hurdle rate"
    elif irr_val >= 0.20:
        verdict = "GOOD DEAL — Meets PE hurdle rate"
    elif irr_val >= 0.15:
        verdict = "MARGINAL — Below typical PE target"
    else:
        verdict = "WEAK DEAL — Does not clear hurdle rate"

    # Attribution
    attribution = {}
    for k, v in results["attribution"].items():
        attribution[k] = _safe_float(v)

    # Income statement & debt schedule
    is_data = _df_to_dict(results["is_df"])
    debt_data = _df_to_dict(results["debt_df"])

    # ── Scenarios ──────────────────────────────────────────
    all_scenarios = run_all_scenarios(deal)
    scenario_table = build_scenario_table(all_scenarios)
    scenarios_out = {}
    for name, res in all_scenarios.items():
        s = res["scenario_assumptions"]
        scenarios_out[name] = {
            "revenue_cagr": round(s.revenue_cagr * 100, 0),
            "ebitda_margin": round(s.ebitda_margin * 100, 0),
            "exit_multiple": s.exit_ev_multiple,
            "interest_rate": round(s.interest_rate * 100, 1),
            "exit_ebitda": _safe_float(res["exit_ebitda"]),
            "exit_ev": _safe_float(res["exit_ev"]),
            "exit_debt": _safe_float(res["exit_debt"]),
            "exit_equity": _safe_float(res["exit_equity"]),
            "irr": _safe_float(res["irr"]),
            "irr_pct": round(_safe_float(res["irr"]) * 100, 1) if _safe_float(res["irr"]) else None,
            "mom": _safe_float(res["mom"]),
            "description": res.get("description", ""),
        }

    # ── Sensitivity heatmaps ───────────────────────────────
    heatmap1 = run_sensitivity(
        deal,
        var1_name="entry_ev_multiple",
        var1_values=[6.0, 7.0, 8.0, 9.0, 10.0, 11.0],
        var2_name="exit_ev_multiple",
        var2_values=[7.0, 8.0, 9.0, 10.0, 11.0],
    )
    heatmap2 = run_sensitivity(
        deal,
        var1_name="revenue_cagr",
        var1_values=[0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 0.18],
        var2_name="ebitda_margin",
        var2_values=[0.12, 0.14, 0.16, 0.18, 0.20, 0.22],
    )

    h1_data = _df_to_dict(heatmap1)
    h2_data = _df_to_dict(heatmap2)

    return {
        "deal_summary": {
            "company_name": deal.company_name,
            "entry_ev": _safe_float(deal.entry_ev),
            "total_debt": _safe_float(deal.total_debt),
            "equity_invested": _safe_float(deal.equity_invested),
            "debt_pct": deal.debt_pct,
            "interest_rate": deal.interest_rate,
            "holding_period": deal.holding_period,
            "entry_ev_multiple": deal.entry_ev_multiple,
            "exit_ev_multiple": deal.exit_ev_multiple,
            "revenue_base": deal.revenue_base,
            "revenue_cagr": deal.revenue_cagr,
            "ebitda_margin": deal.ebitda_margin,
        },
        "returns": {
            "irr": irr_val,
            "irr_pct": irr_pct,
            "mom": _safe_float(results["mom"]),
            "exit_ev": _safe_float(results["exit_ev"]),
            "exit_ebitda": _safe_float(results["exit_ebitda"]),
            "exit_debt": _safe_float(results["exit_debt"]),
            "exit_equity": _safe_float(results["exit_equity"]),
            "verdict": verdict,
            "attribution": attribution,
        },
        "income_statement": is_data,
        "debt_schedule": debt_data,
        "scenarios": scenarios_out,
        "sensitivity": {
            "entry_exit": {
                "title": "Entry Multiple × Exit Multiple → IRR (%)",
                "row_label": "Entry EV/EBITDA",
                "col_label": "Exit EV/EBITDA",
                "data": h1_data,
                "base_row": f"{deal.entry_ev_multiple}x",
                "base_col": f"{deal.exit_ev_multiple}x",
            },
            "growth_margin": {
                "title": "Revenue CAGR × EBITDA Margin → IRR (%)",
                "row_label": "Revenue CAGR",
                "col_label": "EBITDA Margin",
                "data": h2_data,
                "base_row": f"{deal.revenue_cagr*100:.0f}%",
                "base_col": f"{deal.ebitda_margin*100:.0f}%",
            },
        },
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "lbo-modeler"}
