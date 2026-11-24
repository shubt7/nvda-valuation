"""Trading comparables: implied valuation ranges from peer multiples."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ImpliedRange:
    low: float
    mid: float
    high: float


def implied_range(
    peer_multiples: np.ndarray,
    metric: float,
    low_pct: float = 25.0,
    high_pct: float = 75.0,
) -> ImpliedRange:
    """Apply the interquartile range of peer multiples to a company metric.

    The result is an enterprise value (for EV multiples) or equity value (for P/E),
    depending on which metric the caller passes in.
    """
    m = np.asarray(peer_multiples, dtype=float)
    m = m[np.isfinite(m) & (m > 0)]
    if m.size < 3:
        raise ValueError("need at least three valid peer multiples")
    lo, mid, hi = np.percentile(m, [low_pct, 50.0, high_pct])
    return ImpliedRange(low=float(lo * metric), mid=float(mid * metric), high=float(hi * metric))
