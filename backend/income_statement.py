"""
income_statement.py
===================
Projects a 5-year Income Statement and Free Cash Flow (FCF).

Concept: In an LBO, we need to know how much CASH the company
generates each year — because that cash is used to repay debt.
More cash = faster debt paydown = higher equity returns.

Flow:
  Revenue
  - COGS / OpEx
  = EBITDA  (operating profit before non-cash & financing items)
  - D&A     (Depreciation & Amortization — non-cash charge)
  = EBIT    (operating profit)
  - Interest (cost of the debt we took on)
  = EBT     (Earnings Before Tax)
  - Tax
  = Net Income

  Free Cash Flow (FCF):
  = EBITDA - Tax - Capex - Change in Working Capital
  (We use EBITDA as base, not Net Income, because D&A is non-cash)
"""

import pandas as pd
from assumptions import DealAssumptions


def project_income_statement(assumptions: DealAssumptions,
                              debt_schedule: list[float] = None) -> pd.DataFrame:
    """
    Build a 5-year projected Income Statement + FCF.

    Parameters
    ----------
    assumptions   : DealAssumptions object (all inputs live here)
    debt_schedule : list of OPENING debt balances per year
                    Used to compute interest expense correctly.
                    If None, uses total_debt for all years (simplified).

    Returns
    -------
    pd.DataFrame with one column per projection year
    """

    years = list(range(
        assumptions.base_year + 1,
        assumptions.base_year + assumptions.holding_period + 1
    ))  # e.g. [2025, 2026, 2027, 2028, 2029]

    rows = {}  # We'll build each line item as a list across years

    # ── LINE 1: Revenue ───────────────────────────────────────
    # Grows at CAGR (Compound Annual Growth Rate) each year
    # Formula: Revenue_t = Revenue_base × (1 + CAGR)^t
    revenue = []
    for t in range(1, assumptions.holding_period + 1):
        rev_t = assumptions.revenue_base * ((1 + assumptions.revenue_cagr) ** t)
        revenue.append(round(rev_t, 2))
    rows["Revenue (₹ Cr)"] = revenue

    # ── LINE 2: EBITDA ────────────────────────────────────────
    # EBITDA Margin assumed stable (real models sensitize this)
    # Concept: A stable margin means costs grow proportionally with revenue
    ebitda = [round(r * assumptions.ebitda_margin, 2) for r in revenue]
    rows["EBITDA (₹ Cr)"] = ebitda

    # ── LINE 3: D&A (Depreciation & Amortization) ─────────────
    # Non-cash charge — reduces profit on paper but NOT actual cash out
    # Key concept: we ADD IT BACK when computing FCF
    da = [round(r * assumptions.depreciation_pct_revenue, 2) for r in revenue]
    rows["D&A (₹ Cr)"] = da

    # ── LINE 4: EBIT ──────────────────────────────────────────
    # EBIT = EBITDA - D&A
    # Also called "Operating Income" — profit from operations only
    ebit = [round(ebitda[i] - da[i], 2) for i in range(len(years))]
    rows["EBIT (₹ Cr)"] = ebit

    # ── LINE 5: Interest Expense ──────────────────────────────
    # This is the COST of the LBO debt — paid from company's earnings
    # Interest = Opening Debt Balance × Interest Rate
    # As debt gets paid down, interest expense FALLS → more cash to equity
    if debt_schedule is None:
        # Simplified: assume debt stays flat (first pass)
        interest = [round(assumptions.total_debt * assumptions.interest_rate, 2)
                    for _ in years]
    else:
        # Accurate: use actual opening balance each year
        interest = [round(d * assumptions.interest_rate, 2)
                    for d in debt_schedule]
    rows["Interest Expense (₹ Cr)"] = interest

    # ── LINE 6: EBT (Earnings Before Tax) ────────────────────
    ebt = [round(ebit[i] - interest[i], 2) for i in range(len(years))]
    rows["EBT (₹ Cr)"] = ebt

    # ── LINE 7: Tax ───────────────────────────────────────────
    # Tax is only on POSITIVE earnings (no negative tax in simple model)
    tax = [round(max(ebt[i], 0) * assumptions.tax_rate, 2)
           for i in range(len(years))]
    rows["Tax (₹ Cr)"] = tax

    # ── LINE 8: Net Income ────────────────────────────────────
    net_income = [round(ebt[i] - tax[i], 2) for i in range(len(years))]
    rows["Net Income (₹ Cr)"] = net_income

    # ─────────────────────────────────────────────────────────
    # FREE CASH FLOW SECTION
    # FCF = Cash actually available to repay debt / distribute
    # ─────────────────────────────────────────────────────────

    # ── LINE 9: Capex ─────────────────────────────────────────
    # Capital Expenditure = money spent on assets (machines, stores, etc.)
    # Cash OUT — reduces available cash
    capex = [round(r * assumptions.capex_pct_revenue, 2) for r in revenue]
    rows["(-) Capex (₹ Cr)"] = capex

    # ── LINE 10: Change in Working Capital ────────────────────
    # Working Capital = money tied up in day-to-day operations
    # An INCREASE in WC = cash absorbed (negative for FCF)
    delta_wc = [round(r * assumptions.change_in_wc_pct_revenue, 2) for r in revenue]
    rows["(-) ΔWorking Capital (₹ Cr)"] = delta_wc

    # ── LINE 11: Free Cash Flow ───────────────────────────────
    # FCF = EBITDA - Tax - Capex - ΔWC
    # (D&A is non-cash so NOT subtracted here)
    # Concept: This is the REAL cash the business generates for debt repayment
    fcf = [
        round(ebitda[i] - tax[i] - capex[i] - delta_wc[i], 2)
        for i in range(len(years))
    ]
    rows["Free Cash Flow (₹ Cr)"] = fcf

    # ── Build DataFrame ───────────────────────────────────────
    df = pd.DataFrame(rows, index=years).T
    df.index.name = "Line Item"
    df.columns.name = "Year"

    return df


def print_income_statement(df: pd.DataFrame):
    """Pretty-print the income statement to console"""
    print("\n" + "=" * 75)
    print("  PROJECTED INCOME STATEMENT & FREE CASH FLOW")
    print("=" * 75)
    print(df.to_string())
    print("=" * 75)


# ── Run this file directly to test ────────────────────────
if __name__ == "__main__":
    deal = DealAssumptions()
    deal.summary()

    is_df = project_income_statement(deal)
    print_income_statement(is_df)

    # Show just FCF row — what flows into debt repayment
    print("\n  ► Free Cash Flow (used for debt repayment):")
    print(is_df.loc["Free Cash Flow (₹ Cr)"].to_string())
