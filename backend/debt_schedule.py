"""
debt_schedule.py
================
Models how the acquisition debt gets paid down year by year.

This is the MECHANICAL HEART of an LBO model.

Core Concept — The Circular Loop:
  - Interest expense depends on opening debt balance
  - Opening debt balance depends on last year's repayment
  - Repayment depends on FCF
  - FCF depends on interest expense (via tax shield)

  This creates a CIRCULAR DEPENDENCY between the income statement
  and the debt schedule. We solve it iteratively — run the loop
  until numbers converge. This is exactly how Excel's circular
  reference setting works in professional LBO models.

Debt Repayment Mechanics:
  - Each year, the company uses its Free Cash Flow to repay debt
  - This is called a "cash sweep" — sweep all available cash to debt
  - As debt falls → interest expense falls → more FCF available
  - More FCF → even faster debt paydown → compounding effect
  - By exit year, ideally 50-70% of debt is repaid
"""

import pandas as pd
from assumptions import DealAssumptions
from income_statement import project_income_statement


def build_debt_schedule(assumptions: DealAssumptions,
                        max_iterations: int = 50,
                        tolerance: float = 0.01) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Iteratively solve the debt schedule + income statement together.

    Why iterative? Because:
      FCF → repayment → lower debt → lower interest → higher FCF (loop)

    We keep recalculating until the numbers stop changing (converge).

    Parameters
    ----------
    assumptions    : DealAssumptions
    max_iterations : safety cap on loop count
    tolerance      : stop when debt changes less than ₹0.01 Cr between iterations

    Returns
    -------
    (debt_df, income_df) — both fully reconciled DataFrames
    """

    years = list(range(
        assumptions.base_year + 1,
        assumptions.base_year + assumptions.holding_period + 1
    ))

    # ── ITERATION LOOP ────────────────────────────────────────
    # Start with simplified IS (flat debt assumption)
    # Then feed real debt schedule back in → repeat until stable

    # Step 1: Initial pass — no debt schedule yet
    opening_balances = [assumptions.total_debt] * assumptions.holding_period
    prev_closing_balances = [0.0] * assumptions.holding_period

    for iteration in range(max_iterations):

        # Step 2: Project IS using current opening debt balances
        is_df = project_income_statement(assumptions, opening_balances)
        fcf_series = is_df.loc["Free Cash Flow (₹ Cr)"].tolist()

        # Step 3: Build debt schedule using FCF from IS
        debt_rows = {}
        opening_bal = []
        interest_exp = []
        repayments   = []
        closing_bal  = []

        current_debt = assumptions.total_debt  # Start with full acquisition debt

        for i, year in enumerate(years):
            open_b = current_debt
            opening_bal.append(round(open_b, 2))

            # Interest on opening balance
            int_exp = round(open_b * assumptions.interest_rate, 2)
            interest_exp.append(int_exp)

            # Available FCF for debt repayment this year
            available_fcf = fcf_series[i]

            if assumptions.cash_sweep:
                # Cash sweep: use ALL FCF to repay debt (capped at debt outstanding)
                # Can't repay more than what's owed
                repayment = round(min(available_fcf, open_b), 2)
            else:
                # Scheduled repayment: fixed amount per year (alternative structure)
                repayment = round(assumptions.total_debt / assumptions.holding_period, 2)
                repayment = min(repayment, open_b)  # Can't exceed outstanding

            repayments.append(repayment)

            # Closing balance = Opening - Repayment
            # (Interest is EXPENSED not capitalized in this model)
            close_b = round(open_b - repayment, 2)
            close_b = max(close_b, 0)  # Debt can't go negative
            closing_bal.append(close_b)

            # Next year's opening = this year's closing
            current_debt = close_b

        # Step 4: Check convergence
        # If closing balances haven't changed much, we've solved the loop
        max_change = max(
            abs(closing_bal[i] - prev_closing_balances[i])
            for i in range(assumptions.holding_period)
        )

        if max_change < tolerance:
            # Converged — we're done
            break

        # Step 5: Update for next iteration
        # Next iteration's OPENING balances = this iteration's closing balances shifted
        opening_balances = [assumptions.total_debt] + closing_bal[:-1]
        prev_closing_balances = closing_bal.copy()

    # ── Build Debt Schedule DataFrame ─────────────────────────
    debt_rows = {
        "Opening Debt (₹ Cr)"    : opening_bal,
        "Interest Expense (₹ Cr)": interest_exp,
        "FCF Available (₹ Cr)"   : [round(f, 2) for f in fcf_series],
        "Debt Repayment (₹ Cr)"  : repayments,
        "Closing Debt (₹ Cr)"    : closing_bal,
    }

    # Leverage ratio = Debt / EBITDA — banks use this to assess risk
    # >6x is considered aggressive, <4x is conservative
    ebitda_series = is_df.loc["EBITDA (₹ Cr)"].tolist()
    leverage_ratios = [
        round(opening_bal[i] / ebitda_series[i], 2)
        for i in range(len(years))
    ]
    debt_rows["Leverage Ratio (Debt/EBITDA)"] = leverage_ratios

    debt_df = pd.DataFrame(debt_rows, index=years).T
    debt_df.index.name = "Line Item"
    debt_df.columns.name = "Year"

    return debt_df, is_df


def get_exit_debt(debt_df: pd.DataFrame) -> float:
    """Return the closing debt balance in the final (exit) year"""
    return float(debt_df.loc["Closing Debt (₹ Cr)"].iloc[-1])


def print_debt_schedule(debt_df: pd.DataFrame):
    """Pretty-print debt schedule to console"""
    print("\n" + "=" * 75)
    print("  DEBT REPAYMENT SCHEDULE")
    print("=" * 75)
    print(debt_df.to_string())
    print("=" * 75)

    # Key insight callout
    opening = float(debt_df.loc["Opening Debt (₹ Cr)"].iloc[0])
    closing = float(debt_df.loc["Closing Debt (₹ Cr)"].iloc[-1])
    pct_repaid = ((opening - closing) / opening) * 100
    print(f"\n  ► Debt at Entry  : ₹{opening:,.1f} Cr")
    print(f"  ► Debt at Exit   : ₹{closing:,.1f} Cr")
    print(f"  ► % Repaid       : {pct_repaid:.1f}%")
    print(f"  ► Leverage drops from {debt_df.loc['Leverage Ratio (Debt/EBITDA)'].iloc[0]}x "
          f"→ {debt_df.loc['Leverage Ratio (Debt/EBITDA)'].iloc[-1]}x")


# ── Run this file directly to test ────────────────────────
if __name__ == "__main__":
    deal = DealAssumptions()
    deal.summary()

    debt_df, is_df = build_debt_schedule(deal)

    print_debt_schedule(debt_df)

    print("\n  ► Reconciled Income Statement (Interest now reflects actual debt):")
    print(is_df.loc[["EBITDA (₹ Cr)",
                     "Interest Expense (₹ Cr)",
                     "Net Income (₹ Cr)",
                     "Free Cash Flow (₹ Cr)"]].to_string())
