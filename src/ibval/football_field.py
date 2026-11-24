"""Football field: per-share value ranges across valuation methods."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .comps import implied_range
from .dcf import DCFInputs, sensitivity_per_share, value


@dataclass(frozen=True)
class Bar:
    label: str
    low: float
    high: float
    note: str


def build_football_field(
    inp: DCFInputs,
    peer_ev_ebitda: np.ndarray,
    ltm_ebitda: float,
    fifty_two_week: tuple[float, float],
    wacc_band: float = 0.01,
    growth_band: float = 0.005,
    exit_multiple_band: float = 1.0,
) -> list[Bar]:
    """Per-share ranges for each method. Each DCF range is a sensitivity band around the base case."""
    shares = inp.shares
    bars: list[Bar] = []

    # Perpetuity-growth DCF: flex WACC and terminal growth together.
    waccs = np.array([inp.wacc - wacc_band, inp.wacc, inp.wacc + wacc_band])
    growths = np.array([inp.terminal_growth - growth_band, inp.terminal_growth, inp.terminal_growth + growth_band])
    grid = sensitivity_per_share(inp, waccs, growths)
    finite = grid[np.isfinite(grid)]
    bars.append(Bar("DCF: perpetuity growth", float(finite.min()), float(finite.max()),
                    f"WACC {waccs[0]:.1%}–{waccs[-1]:.1%}, g {growths[0]:.1%}–{growths[-1]:.1%}"))

    # Exit-multiple DCF: flex the multiple.
    lo = value(_with(inp, exit_multiple=inp.exit_multiple - exit_multiple_band), "exit").per_share
    hi = value(_with(inp, exit_multiple=inp.exit_multiple + exit_multiple_band), "exit").per_share
    bars.append(Bar("DCF: exit multiple", min(lo, hi), max(lo, hi),
                    f"{inp.exit_multiple - exit_multiple_band:.1f}x–{inp.exit_multiple + exit_multiple_band:.1f}x EBITDA"))

    # Trading comps: interquartile EV/EBITDA applied to LTM EBITDA, less net debt.
    comp = implied_range(peer_ev_ebitda, ltm_ebitda)
    bars.append(Bar("Trading comps: EV/EBITDA",
                    (comp.low - inp.net_debt) / shares, (comp.high - inp.net_debt) / shares,
                    "25th–75th percentile of peers"))

    bars.append(Bar("52-week trading range", fifty_two_week[0], fifty_two_week[1], "Market reference"))
    return bars


def _with(inp: DCFInputs, **changes) -> DCFInputs:
    base = inp.__dict__.copy()
    base.update(changes)
    return DCFInputs(**base)
