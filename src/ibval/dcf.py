"""Unlevered discounted cash flow (DCF) valuation.

Conventions
-----------
* Cash flows are end-of-year and discounted at WACC.
* Unlevered FCF = EBIT x (1 - tax) + D&A - capex - change in net working capital.
* Terminal value is either Gordon growth on the final-year FCF, or an exit
  multiple on the final-year EBITDA.
* Equity value = enterprise value - net debt; per-share value divides by shares.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DCFInputs:
    revenue0: float                 # last actual revenue
    growth: tuple[float, ...]       # annual revenue growth, one entry per projection year
    ebit_margin: float
    tax_rate: float
    da_pct_revenue: float
    capex_pct_revenue: float
    nwc_pct_revenue: float          # net working capital as a share of revenue
    wacc: float
    terminal_growth: float
    exit_multiple: float            # EV / final-year EBITDA
    net_debt: float
    shares: float

    def __post_init__(self):
        if len(self.growth) < 1:
            raise ValueError("need at least one projection year")
        if self.wacc <= self.terminal_growth:
            raise ValueError("WACC must exceed terminal growth for a finite Gordon value")
        if self.shares <= 0 or self.revenue0 <= 0:
            raise ValueError("revenue0 and shares must be positive")


@dataclass(frozen=True)
class Projection:
    years: np.ndarray
    revenue: np.ndarray
    ebit: np.ndarray
    ebitda: np.ndarray
    ufcf: np.ndarray


@dataclass(frozen=True)
class DCFResult:
    projection: Projection
    pv_fcf: float
    terminal_value: float
    pv_terminal: float
    enterprise_value: float
    equity_value: float
    per_share: float
    terminal_share_of_ev: float


def project(inp: DCFInputs) -> Projection:
    growth = np.asarray(inp.growth, dtype=float)
    revenue = inp.revenue0 * np.cumprod(1 + growth)
    prev_revenue = np.concatenate([[inp.revenue0], revenue[:-1]])
    ebit = revenue * inp.ebit_margin
    da = revenue * inp.da_pct_revenue
    capex = revenue * inp.capex_pct_revenue
    nwc = revenue * inp.nwc_pct_revenue
    prev_nwc = prev_revenue * inp.nwc_pct_revenue
    d_nwc = nwc - prev_nwc
    ufcf = ebit * (1 - inp.tax_rate) + da - capex - d_nwc
    return Projection(
        years=np.arange(1, len(growth) + 1),
        revenue=revenue,
        ebit=ebit,
        ebitda=ebit + da,
        ufcf=ufcf,
    )


def value(inp: DCFInputs, terminal: str = "perpetuity") -> DCFResult:
    """Value a company. ``terminal`` is 'perpetuity' (Gordon growth) or 'exit' (multiple)."""
    proj = project(inp)
    n = len(proj.years)
    discount = (1 + inp.wacc) ** -proj.years
    pv_fcf = float(np.dot(proj.ufcf, discount))

    if terminal == "perpetuity":
        tv = proj.ufcf[-1] * (1 + inp.terminal_growth) / (inp.wacc - inp.terminal_growth)
    elif terminal == "exit":
        tv = proj.ebitda[-1] * inp.exit_multiple
    else:
        raise ValueError("terminal must be 'perpetuity' or 'exit'")

    pv_tv = tv * (1 + inp.wacc) ** -n
    ev = pv_fcf + pv_tv
    equity = ev - inp.net_debt
    return DCFResult(
        projection=proj,
        pv_fcf=pv_fcf,
        terminal_value=float(tv),
        pv_terminal=float(pv_tv),
        enterprise_value=float(ev),
        equity_value=float(equity),
        per_share=float(equity / inp.shares),
        terminal_share_of_ev=float(pv_tv / ev) if ev else float("nan"),
    )


def wacc(cost_equity: float, cost_debt: float, tax_rate: float, equity_value: float, debt: float) -> float:
    """Weighted average cost of capital from market-value weights."""
    total = equity_value + debt
    if total <= 0:
        raise ValueError("capital structure must have positive total value")
    return (equity_value / total) * cost_equity + (debt / total) * cost_debt * (1 - tax_rate)


def sensitivity_per_share(
    inp: DCFInputs, waccs: np.ndarray, growths: np.ndarray
) -> np.ndarray:
    """Per-share value on a WACC x terminal-growth grid (perpetuity method).

    Cells where WACC <= g are returned as NaN.
    """
    grid = np.full((len(waccs), len(growths)), np.nan)
    for i, w in enumerate(waccs):
        for j, g in enumerate(growths):
            if w <= g:
                continue
            base = inp.__dict__.copy()
            base.update(wacc=float(w), terminal_growth=float(g))
            grid[i, j] = value(DCFInputs(**base), "perpetuity").per_share
    return grid
