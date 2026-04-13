"""
assumptions.py
==============
This is the CONTROL PANEL of the entire LBO model.
Every single number in the model flows from here.
Change one value here → everything updates automatically.

Concept: In real PE deals, analysts run dozens of versions
of a model by tweaking assumptions. Centralizing them like
this is standard professional practice.
"""

from dataclasses import dataclass, field


@dataclass
class DealAssumptions:
    # ── Company Info ──────────────────────────────────────────
    company_name: str = "Devyani International"
    base_year: int = 2024

    # ── Entry Assumptions ─────────────────────────────────────
    # EV = Enterprise Value = what you're paying for the whole business
    # EBITDA = Earnings Before Interest, Tax, Depreciation & Amortization
    #          It's the best proxy for a company's operating cash generation
    # Entry Multiple = how many times EBITDA you're paying (like a P/E ratio)
    entry_year_ebitda: float = 120.0        # ₹ Crore — EBITDA in year of purchase
    entry_ev_multiple: float = 8.0          # Buying at 8x EBITDA → EV = ₹960 Cr

    # ── Exit Assumptions ──────────────────────────────────────
    # You hope to SELL at a higher multiple than you bought
    # This difference (multiple expansion) is one of the 3 return drivers
    exit_ev_multiple: float = 9.0           # Selling at 9x EBITDA after 5 years
    holding_period: int = 5                 # Years before selling (typical PE = 3-7 yrs)

    # ── Capital Structure ─────────────────────────────────────
    # This is the HEART of an LBO — using debt to amplify returns
    # debt_pct = what fraction of the purchase price is funded by debt
    debt_pct: float = 0.65                  # 65% debt / 35% equity (typical LBO range)
    interest_rate: float = 0.10             # 10% annual interest on debt (India rate)

    # ── Operating Assumptions ─────────────────────────────────
    # These drive the Income Statement projections
    revenue_base: float = 800.0             # ₹ Crore — revenue in base year
    revenue_cagr: float = 0.12             # 12% annual revenue growth
    ebitda_margin: float = 0.18            # EBITDA as % of revenue (stable business)
    depreciation_pct_revenue: float = 0.03 # D&A as % of revenue
    capex_pct_revenue: float = 0.04        # Capital expenditure as % of revenue
    change_in_wc_pct_revenue: float = 0.01 # Working capital needs as % of revenue
    tax_rate: float = 0.25                 # 25% corporate tax rate (India)

    # ── Debt Repayment ────────────────────────────────────────
    # Cash sweep = use ALL available FCF to pay down debt aggressively
    # This is standard in LBOs — company's own cash pays off acquisition debt
    cash_sweep: bool = True                 # True = pay max debt each year from FCF

    # ── Computed Properties ───────────────────────────────────
    # These are DERIVED values — calculated from inputs above
    # You don't set these manually; they're computed automatically

    @property
    def entry_ev(self) -> float:
        """Enterprise Value = EBITDA × Entry Multiple"""
        return self.entry_year_ebitda * self.entry_ev_multiple

    @property
    def total_debt(self) -> float:
        """Debt raised = 65% of total EV paid"""
        return self.entry_ev * self.debt_pct

    @property
    def equity_invested(self) -> float:
        """PE firm's own money = remaining 35%"""
        return self.entry_ev * (1 - self.debt_pct)

    def summary(self):
        """Print a clean deal summary to console"""
        print("=" * 50)
        print(f"  LBO DEAL SUMMARY — {self.company_name}")
        print("=" * 50)
        print(f"  Entry EV          : ₹{self.entry_ev:,.1f} Cr")
        print(f"  Total Debt        : ₹{self.total_debt:,.1f} Cr  ({self.debt_pct*100:.0f}%)")
        print(f"  Equity Invested   : ₹{self.equity_invested:,.1f} Cr  ({(1-self.debt_pct)*100:.0f}%)")
        print(f"  Interest Rate     : {self.interest_rate*100:.1f}%")
        print(f"  Holding Period    : {self.holding_period} years")
        print(f"  Exit Multiple     : {self.exit_ev_multiple}x")
        print("=" * 50)


# ── Run this file directly to test it ─────────────────────
if __name__ == "__main__":
    deal = DealAssumptions()
    deal.summary()
    print(f"\n  Entry EV/EBITDA   : {deal.entry_ev_multiple}x")
    print(f"  Entry EV          : ₹{deal.entry_ev:,.0f} Cr")
    print(f"  Debt              : ₹{deal.total_debt:,.0f} Cr")
    print(f"  Equity Check      : ₹{deal.equity_invested:,.0f} Cr")
