"""
returns.py
==========
Calculates the PE firm's investment returns from the LBO.

The Two Numbers Every PE Investor Cares About:
───────────────────────────────────────────────
1. IRR (Internal Rate of Return)
   - The annualized % return on invested equity
   - Think of it as: "what interest rate would a bank need to offer
     to give you the same result as this deal?"
   - PE firms typically target 20–25%+ IRR
   - Formula: Solve for r where NPV of all cash flows = 0
     0 = -Equity_invested + Exit_Equity / (1+r)^n

2. MoM (Money-on-Money Multiple)
   - How many times you got your money back
   - Simple: Exit Equity / Equity Invested
   - PE benchmark: 2.5x–3x over 5 years is a good deal
   - Does NOT account for time — a 3x in 3 years ≠ 3x in 7 years
     (that's why you need IRR alongside MoM)

The Three Drivers of LBO Returns:
───────────────────────────────────
1. EBITDA Growth     → company is worth more at exit
2. Debt Paydown      → more of exit proceeds go to equity
3. Multiple Expansion → selling at higher multiple than entry
   (e.g., buy at 8x, sell at 9x — this alone adds significant return)

Return Attribution tells you WHICH driver created the most value.
That's what separates a PE analyst from a finance student.
"""

import numpy_financial as npf
import pandas as pd
from assumptions import DealAssumptions
from debt_schedule import build_debt_schedule, get_exit_debt


def calculate_returns(assumptions: DealAssumptions) -> dict:
    """
    Calculate full LBO returns and attribute them to value drivers.

    Returns
    -------
    dict containing:
      - irr         : annualized equity return
      - mom         : money-on-money multiple
      - exit_ev     : enterprise value at sale
      - exit_equity : equity proceeds after debt repayment
      - attribution : breakdown of return drivers
      - debt_df     : debt schedule DataFrame
      - is_df       : income statement DataFrame
    """

    # ── Step 1: Build Debt Schedule (solves circular loop) ────
    debt_df, is_df = build_debt_schedule(assumptions)

    # ── Step 2: Exit EBITDA ───────────────────────────────────
    # EBITDA in the final projection year (Year 5)
    exit_ebitda = float(is_df.loc["EBITDA (₹ Cr)"].iloc[-1])

    # ── Step 3: Exit Enterprise Value ────────────────────────
    # Exit EV = Exit EBITDA × Exit Multiple
    # This is what the NEXT BUYER pays for the whole company
    exit_ev = round(exit_ebitda * assumptions.exit_ev_multiple, 2)

    # ── Step 4: Exit Equity Value ─────────────────────────────
    # What's left for the PE firm AFTER repaying remaining debt
    # Equity = Enterprise Value − Net Debt at Exit
    exit_debt = get_exit_debt(debt_df)
    exit_equity = round(exit_ev - exit_debt, 2)

    # ── Step 5: Cash Flow Stream for IRR ─────────────────────
    # IRR is calculated on EQUITY cash flows only:
    #   Year 0  : -Equity Invested (cash OUT — you write the cheque)
    #   Year 1–4: 0 (PE firms don't take dividends during hold period)
    #   Year 5  : +Exit Equity (cash IN — you receive sale proceeds)
    #
    # Note: In more advanced models, interim dividends or dividend
    # recaps would appear in Years 1–4. Keeping it clean here.
    cash_flows = (
        [-assumptions.equity_invested]          # Year 0: investment
        + [0] * (assumptions.holding_period - 1) # Years 1 to n-1: no cash
        + [exit_equity]                          # Year n: exit proceeds
    )

    irr = npf.irr(cash_flows)
    mom = round(exit_equity / assumptions.equity_invested, 2)

    # ── Step 6: Return Attribution ────────────────────────────
    # Decompose returns into the 3 value creation levers.
    # This is the most sophisticated part — shows you understand
    # WHERE the return came from, not just WHAT the return was.

    entry_ev     = assumptions.entry_ev
    entry_ebitda = assumptions.entry_year_ebitda

    # --- Driver 1: EBITDA Growth ---
    # What would exit EV be if ONLY EBITDA grew (same entry multiple, same debt)?
    ebitda_growth_ev     = round(exit_ebitda * assumptions.entry_ev_multiple, 2)
    ebitda_growth_equity = round(ebitda_growth_ev - exit_debt, 2)

    # --- Driver 2: Multiple Expansion ---
    # Premium from selling at a HIGHER multiple than entry
    # e.g., 8x → 9x on ₹215Cr EBITDA = extra ₹215Cr in value
    multiple_expansion_value = round(
        exit_ebitda * (assumptions.exit_ev_multiple - assumptions.entry_ev_multiple), 2
    )

    # --- Driver 3: Debt Paydown ---
    # Equity gained purely from debt being repaid
    # Every ₹1 of debt repaid = ₹1 more equity at exit
    debt_repaid = round(assumptions.total_debt - exit_debt, 2)

    # --- Sanity check: components should sum to total equity gain ---
    equity_gain        = round(exit_equity - assumptions.equity_invested, 2)
    attributed_gain    = round(
        (ebitda_growth_equity - assumptions.equity_invested)
        + multiple_expansion_value, 2
    )

    attribution = {
        "Entry Equity Invested (₹ Cr)"     : round(assumptions.equity_invested, 2),
        "EBITDA Growth Contribution (₹ Cr)" : round(ebitda_growth_equity - assumptions.equity_invested, 2),
        "Multiple Expansion (₹ Cr)"         : multiple_expansion_value,
        "Debt Paydown (₹ Cr)"               : debt_repaid,
        "Exit Equity Value (₹ Cr)"          : exit_equity,
    }

    return {
        "irr"          : irr,
        "mom"          : mom,
        "exit_ev"      : exit_ev,
        "exit_ebitda"  : exit_ebitda,
        "exit_debt"    : exit_debt,
        "exit_equity"  : exit_equity,
        "cash_flows"   : cash_flows,
        "attribution"  : attribution,
        "debt_df"      : debt_df,
        "is_df"        : is_df,
    }


def print_returns(results: dict, assumptions: DealAssumptions):
    """Print a clean returns summary — like a PE deal tearsheet"""

    irr = results["irr"]
    mom = results["mom"]

    # ── Verdict Logic ─────────────────────────────────────────
    if irr >= 0.25:
        verdict = "🟢 STRONG DEAL — Exceeds PE hurdle rate"
    elif irr >= 0.20:
        verdict = "🟡 GOOD DEAL — Meets PE hurdle rate"
    elif irr >= 0.15:
        verdict = "🟠 MARGINAL — Below typical PE target"
    else:
        verdict = "🔴 WEAK DEAL — Does not clear hurdle rate"

    print("\n" + "=" * 55)
    print("  LBO RETURNS SUMMARY")
    print("=" * 55)
    print(f"  Company          : {assumptions.company_name}")
    print(f"  Entry EV         : ₹{assumptions.entry_ev:,.1f} Cr  ({assumptions.entry_ev_multiple}x EBITDA)")
    print(f"  Exit EV          : ₹{results['exit_ev']:,.1f} Cr  ({assumptions.exit_ev_multiple}x EBITDA)")
    print(f"  Exit Debt        : ₹{results['exit_debt']:,.1f} Cr")
    print(f"  Exit Equity      : ₹{results['exit_equity']:,.1f} Cr")
    print("-" * 55)
    print(f"  Equity Invested  : ₹{assumptions.equity_invested:,.1f} Cr")
    print(f"  IRR              : {irr*100:.1f}%")
    print(f"  MoM Multiple     : {mom:.2f}x")
    print("-" * 55)
    print(f"  Verdict          : {verdict}")
    print("=" * 55)

    print("\n  RETURN ATTRIBUTION (Where did the money come from?)")
    print("-" * 55)
    for k, v in results["attribution"].items():
        bar = "█" * int(abs(v) / 20)  # simple ASCII bar
        print(f"  {k:<38}: ₹{v:>8.1f} Cr  {bar}")
    print("=" * 55)


# ── Run this file directly to test ────────────────────────
if __name__ == "__main__":
    deal = DealAssumptions()
    results = calculate_returns(deal)
    print_returns(results, deal)

    print(f"\n  Cash Flow Stream passed to IRR function:")
    for i, cf in enumerate(results["cash_flows"]):
        label = "Entry" if i == 0 else f"Year {i}" if i < len(results['cash_flows'])-1 else "Exit"
        print(f"    {label:>6}: ₹{cf:>10,.1f} Cr")
