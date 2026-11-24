"""NVIDIA (NVDA) equity valuation: DCF (perpetuity and exit multiple), sensitivities, and reports.

Run:  PYTHONPATH=src python scripts/make_nvda_report.py

Data sources
------------
FY2026 actuals (fiscal year ended Jan 25, 2026), from the Form 10-K and the Q4 FY26 press release:
  revenue 215,938; GAAP operating income 130,387; net income 120,067; operating cash flow 102,718;
  capex 6,042; D&A 2,843; cash 10,605; marketable securities 51,951; debt 8,468 (7,469 long-term + 999 short-term);
  diluted weighted shares 24,514m; 24.2bn shares outstanding at May 15, 2026 (Q1 FY27 10-Q).
Market data: last close found in search, $215.38 (about Oct 28, 2026); 52-week range 164.27 to 243.37.

Assumptions (NOT sourced; change them and rerun): growth path, EBIT margin, tax rate, D&A, capex, NWC,
WACC, terminal growth, exit multiple. Each is labelled in the report.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ibval import DCFInputs, build_banker_model, build_client_summary, sensitivity_per_share, value
from ibval.football_field import Bar

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
COMPANY = "NVIDIA Corporation (NVDA)"
PREPARED_BY = "Shubham"

# FY2026 actuals ($m, shares in m)
FY26 = dict(revenue=215_938.0, operating_income=130_387.0, net_income=120_067.0,
            cash=10_605.0, marketable_securities=51_951.0, debt=8_468.0,
            diluted_shares=24_514.0, da=2_843.0, capex=6_042.0)
NET_CASH = FY26["cash"] + FY26["marketable_securities"] - FY26["debt"]  # 54,088
CURRENT_PRICE = 215.38
FIFTY_TWO_WEEK = (164.27, 243.37)

# Assumptions (illustrative, not sourced)
BASE = DCFInputs(
    revenue0=FY26["revenue"],
    growth=(0.50, 0.30, 0.20, 0.12, 0.08),
    ebit_margin=0.58,
    tax_rate=0.16,
    da_pct_revenue=FY26["da"] / FY26["revenue"],
    capex_pct_revenue=FY26["capex"] / FY26["revenue"],
    nwc_pct_revenue=0.10,
    wacc=0.10,
    terminal_growth=0.03,
    exit_multiple=20.0,
    net_debt=-NET_CASH,
    shares=FY26["diluted_shares"],
)

WACCS = np.array([0.085, 0.09, 0.095, 0.10, 0.105, 0.11])
GROWTHS = np.array([0.025, 0.03, 0.035, 0.04])


def build_bars(inp: DCFInputs) -> list[Bar]:
    grid = sensitivity_per_share(inp, np.array([0.09, inp.wacc, 0.11]),
                                 np.array([0.025, inp.terminal_growth, 0.035]))
    finite = grid[np.isfinite(grid)]
    exit_lo = value(_with(inp, exit_multiple=15.0), "exit").per_share
    exit_hi = value(_with(inp, exit_multiple=25.0), "exit").per_share
    return [
        Bar("DCF: perpetuity growth", float(finite.min()), float(finite.max()),
            "WACC 9%–11%, terminal growth 2.5%–3.5%"),
        Bar("DCF: exit multiple", min(exit_lo, exit_hi), max(exit_lo, exit_hi),
            "15x–25x EBITDA in year 5"),
        Bar("52-week trading range", FIFTY_TWO_WEEK[0], FIFTY_TWO_WEEK[1], "Market reference"),
    ]


def _with(inp: DCFInputs, **changes) -> DCFInputs:
    base = inp.__dict__.copy()
    base.update(changes)
    return DCFInputs(**base)


def sensitivity_html(inp: DCFInputs) -> str:
    grid = sensitivity_per_share(inp, WACCS, GROWTHS)
    lo, hi = float(np.nanmin(grid)), float(np.nanmax(grid))
    head = "".join(f"<th>g {g:.1%}</th>" for g in GROWTHS)
    rows = []
    for i, w in enumerate(WACCS):
        cells = []
        for j in range(len(GROWTHS)):
            v = grid[i, j]
            txt = "n/a" if not np.isfinite(v) else f"${v:,.0f}"
            shade = 0 if not np.isfinite(v) or hi == lo else (v - lo) / (hi - lo)
            bg = "var(--card)" if not np.isfinite(v) else f"color-mix(in srgb, #0b3d91 {int(12 + 60*shade)}%, var(--card))"
            cells.append(f'<td style="background:{bg}">{txt}</td>')
        rows.append(f"<tr><td>WACC {w:.1%}</td>{''.join(cells)}</tr>")
    return f"<table><tr><th></th>{head}</tr>{''.join(rows)}</table>"


def main() -> None:
    base = value(BASE, "perpetuity")
    exit_case = value(BASE, "exit")
    bars = build_bars(BASE)
    DOCS.mkdir(parents=True, exist_ok=True)

    client = build_client_summary(COMPANY, BASE, bars, CURRENT_PRICE, base, bank=PREPARED_BY)
    banker = build_banker_model(COMPANY, BASE, base, bars, CURRENT_PRICE, WACCS, GROWTHS, bank=PREPARED_BY)
    (DOCS / "nvda_client_summary.html").write_text(client, encoding="utf-8")
    (DOCS / "nvda_banker_model.html").write_text(banker, encoding="utf-8")

    import re
    def main_of(doc): return re.search(r"<main>(.*)</main>", doc, re.S).group(1)
    css = re.search(r"<style>(.*?)</style>", client, re.S).group(1)
    combined = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>NVIDIA valuation dashboard</title>
<style>{css}
nav.tabs{{display:flex;gap:8px;margin:8px 0 20px}}nav.tabs button{{font:inherit;padding:8px 14px;border-radius:999px;border:1px solid var(--grid);background:var(--card);color:var(--fg);cursor:pointer}}
nav.tabs button.on{{background:var(--accent);color:#fff;border-color:var(--accent)}}.view{{display:none}}.view.on{{display:block}}
.assume{{color:var(--muted);font-size:13px}}
</style></head><body><main>
<h1>NVIDIA (NVDA): valuation dashboard</h1>
<div class="sub">Illustrative valuation from FY2026 filings · prepared by {PREPARED_BY} · assumptions are not sourced and are labelled in the banker view</div>
<nav class="tabs"><button class="on" data-v="client">Client view</button><button data-v="banker">Banker view</button></nav>
<section class="view on" id="client">{main_of(client)}
<h2>Two ways to value it</h2>
<div class="card"><table>
<tr><th>Method</th><th>Value per share</th><th>What drives it</th></tr>
<tr><td>Perpetuity growth (base)</td><td>${base.per_share:,.2f}</td><td>10% WACC, 3% terminal growth; {base.terminal_share_of_ev:.0%} of value is in the terminal period</td></tr>
<tr><td>Exit multiple (cross-check)</td><td>${exit_case.per_share:,.2f}</td><td>20x year-5 EBITDA, discounted at 10%</td></tr>
<tr><td>Last close found</td><td>${CURRENT_PRICE:,.2f}</td><td>About Oct 28, 2026</td></tr>
</table>
<div class="note">The gap between the two methods shows how much of NVIDIA's value depends on growth beyond year 5. A perpetuity at a 10% discount rate is more conservative than a 20x exit multiple.</div></div>
</section>
<section class="view" id="banker">{main_of(banker)}
<h2>Sensitivity: value per share, WACC × terminal growth</h2>
<div class="card">{sensitivity_html(BASE)}<div class="note">Perpetuity method. Darker is higher.</div></div>
</section>
</main><script>
document.querySelectorAll('nav.tabs button').forEach(b=>b.onclick=()=>{{
  document.querySelectorAll('nav.tabs button').forEach(x=>x.classList.toggle('on',x===b));
  document.querySelectorAll('.view').forEach(v=>v.classList.toggle('on',v.id===b.dataset.v));
}});
</script></body></html>"""
    (DOCS / "nvda_dashboard.html").write_text(combined, encoding="utf-8")

    print(f"perpetuity ${base.per_share:,.2f}  exit ${exit_case.per_share:,.2f}  price ${CURRENT_PRICE:,.2f}")


if __name__ == "__main__":
    main()
