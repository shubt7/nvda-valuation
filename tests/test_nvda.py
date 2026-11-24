import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import make_nvda_report as m  # noqa: E402
from ibval import value  # noqa: E402


def test_fy26_net_cash_matches_balance_sheet():
    # 10,605 cash + 51,951 marketable securities - 8,468 debt
    assert m.NET_CASH == pytest.approx(54_088)


def test_fy26_margins_match_filings():
    assert m.FY26["operating_income"] / m.FY26["revenue"] == pytest.approx(0.6038, abs=1e-4)


def test_base_case_is_internally_consistent():
    base = value(m.BASE, "perpetuity")
    # Equity bridge: EV plus net cash, divided by diluted shares.
    assert base.equity_value == pytest.approx(base.enterprise_value + m.NET_CASH)
    assert base.per_share == pytest.approx(base.equity_value / m.FY26["diluted_shares"])


def test_perpetuity_value_below_exit_multiple_value_at_base_inputs():
    # Documented in the report: the 10% / 3% perpetuity is more conservative than a 20x exit.
    assert value(m.BASE, "perpetuity").per_share < value(m.BASE, "exit").per_share


def test_sensitivity_falls_with_wacc():
    grid = m.sensitivity_html  # smoke: function exists
    assert callable(grid)
    from ibval import sensitivity_per_share
    g = sensitivity_per_share(m.BASE, np.array([0.09, 0.10, 0.11]), np.array([0.03]))
    assert g[0, 0] > g[1, 0] > g[2, 0]


def test_bars_are_ordered():
    for b in m.build_bars(m.BASE):
        assert b.low <= b.high
