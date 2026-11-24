"""HTML reports: a plain-English client summary and a detailed banker model view.

Both are single self-contained files (inline SVG and CSS, no external assets).
"""

from __future__ import annotations

import html

import numpy as np

from .dcf import DCFInputs, DCFResult, sensitivity_per_share, value
from .football_field import Bar

CSS = """
:root{--bg:#fff;--fg:#1d1d1f;--muted:#6e6e73;--card:#f5f5f7;--grid:#d9d9de;--accent:#0b3d91;--pos:#1a7f37;--neg:#c62828}
@media (prefers-color-scheme: dark){:root{--bg:#111;--fg:#f2f2f2;--muted:#9a9aa0;--card:#1c1c1e;--grid:#333;--accent:#7fb2ff}}
body{font:15px/1.55 system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--fg);margin:0;padding:32px}
main{max-width:1040px;margin:0 auto}
h1{font-size:28px;margin:0 0 4px}h2{font-size:18px;margin:28px 0 10px;color:var(--accent)}
.sub{color:var(--muted);margin-bottom:20px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}
.kpi,.card{background:var(--card);border-radius:12px;padding:16px 18px}
.kpi .v{font-size:24px;font-weight:600}.kpi .l{color:var(--muted);font-size:13px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:right;padding:7px 9px;border-bottom:1px solid var(--grid)}
th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-weight:500}
.note{color:var(--muted);font-size:13px;margin-top:8px}
.takeaways li{margin-bottom:8px}
.chart{width:100%;height:auto}.axis{fill:var(--muted);font-size:12px}.lbl{fill:var(--fg);font-size:13px}
.grid{stroke:var(--grid)}.bar{fill:var(--accent);opacity:.85}.bar.ref{fill:var(--muted)}.now{stroke:var(--neg);stroke-dasharray:4 3;stroke-width:1.5}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;background:var(--card);border:1px solid var(--grid);font-size:12px;color:var(--muted)}
.disclaimer{color:var(--muted);font-size:12px;margin-top:28px;border-top:1px solid var(--grid);padding-top:12px}
"""


def _money(x: float) -> str:
    return f"${x:,.2f}"


def football_svg(bars: list[Bar], current_price: float, width: int = 900) -> str:
    left, right, top, row_h = 230, 30, 20, 46
    lo = min(b.low for b in bars)
    hi = max(b.high for b in bars)
    lo = min(lo, current_price) * 0.9
    hi = max(hi, current_price) * 1.08
    height = top + row_h * len(bars) + 40

    def px(v):
        return left + (v - lo) / (hi - lo) * (width - left - right)

    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" xmlns="http://www.w3.org/2000/svg">']
    for t in np.linspace(lo, hi, 6):
        x = px(t)
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{height-30}" class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="{height-12}" class="axis" text-anchor="middle">${t:,.0f}</text>')
    for i, b in enumerate(bars):
        y = top + i * row_h
        cls = "bar ref" if b.label.startswith("52") else "bar"
        parts.append(f'<text x="{left-12}" y="{y+row_h/2+5:.1f}" class="lbl" text-anchor="end">{html.escape(b.label)}</text>')
        parts.append(f'<rect x="{px(b.low):.1f}" y="{y+10}" width="{max(px(b.high)-px(b.low),2):.1f}" height="{row_h-20}" rx="4" class="{cls}"/>')
        parts.append(f'<text x="{px(b.low)-6:.1f}" y="{y+row_h/2+4:.1f}" class="axis" text-anchor="end">${b.low:,.0f}</text>')
        parts.append(f'<text x="{px(b.high)+6:.1f}" y="{y+row_h/2+4:.1f}" class="axis">${b.high:,.0f}</text>')
    x = px(current_price)
    parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top-8}" y2="{height-30}" class="now"/>')
    parts.append(f'<text x="{x:.1f}" y="{top-12}" class="axis" text-anchor="middle">Current ${current_price:,.2f}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _heat(v: float, lo: float, hi: float) -> str:
    if not np.isfinite(v):
        return "var(--card)"
    t = 0 if hi == lo else (v - lo) / (hi - lo)
    # light grey -> accent blue, mixed in CSS so it adapts to the theme
    return f"color-mix(in srgb, #0b3d91 {int(15 + 55 * t)}%, var(--card))"


def sensitivity_table(inp: DCFInputs, waccs, growths, current_price: float) -> str:
    grid = sensitivity_per_share(inp, waccs, growths)
    finite = grid[np.isfinite(grid)]
    lo, hi = float(finite.min()), float(finite.max())
    head = "".join(f"<th>g {g:.1%}</th>" for g in growths)
    rows = []
    for i, w in enumerate(waccs):
        cells = []
        for j in range(len(growths)):
            v = grid[i, j]
            txt = "n/a" if not np.isfinite(v) else _money(v)
            cells.append(f'<td style="background:{_heat(v, lo, hi)}">{txt}</td>')
        rows.append(f"<tr><td>WACC {w:.1%}</td>{''.join(cells)}</tr>")
    return f"<table><tr><th></th>{head}</tr>{''.join(rows)}</table>"


def _projection_table(res: DCFResult) -> str:
    p = res.projection
    yrs = "".join(f"<th>Y{int(y)}</th>" for y in p.years)
    def row(name, arr):
        return f"<tr><td>{name}</td>" + "".join(f"<td>{v:,.1f}</td>" for v in arr) + "</tr>"
    return (f"<table><tr><th>$m</th>{yrs}</tr>"
            + row("Revenue", p.revenue) + row("EBITDA", p.ebitda)
            + row("EBIT", p.ebit) + row("Unlevered FCF", p.ufcf) + "</table>")


def build_client_summary(company: str, inp: DCFInputs, bars: list[Bar], current_price: float,
                         base: DCFResult, bank: str = "") -> str:
    mid_low = min(b.low for b in bars if not b.label.startswith("52"))
    mid_high = max(b.high for b in bars if not b.label.startswith("52"))
    upside = base.per_share / current_price - 1
    direction = "above" if upside > 0 else "below"
    takeaways = [
        f"Our base-case intrinsic value is <b>{_money(base.per_share)} per share</b>, "
        f"{abs(upside):.0%} {direction} the current price of {_money(current_price)}.",
        f"Across methods, the indicative value range is <b>{_money(mid_low)} to {_money(mid_high)}</b> per share.",
        f"About {base.terminal_share_of_ev:.0%} of the value sits in the long-term outlook, so results depend heavily on margin and growth assumptions.",
        "The range reflects reasonable variation in discount rate, growth and exit assumptions, not a precise target.",
    ]
    lis = "".join(f"<li>{t}</li>" for t in takeaways)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(company)} valuation summary</title>
<style>{CSS}</style></head><body><main>
<h1>{html.escape(company)}: valuation summary</h1>
<div class="sub">Client view{(' · prepared by ' + html.escape(bank)) if bank else ''} · illustrative analysis</div>
<div class="kpis">
  <div class="kpi"><div class="v">{_money(base.per_share)}</div><div class="l">Base-case value per share</div></div>
  <div class="kpi"><div class="v">{_money(current_price)}</div><div class="l">Current share price</div></div>
  <div class="kpi"><div class="v">{upside:+.0%}</div><div class="l">Base case vs. current</div></div>
</div>
<h2>Valuation range by method</h2>
<div class="card">{football_svg(bars, current_price)}
<div class="note">Bars show per-share value. The dashed line is the current price. Ranges come from sensitivity bands, not point estimates.</div></div>
<h2>Key takeaways</h2>
<div class="card"><ul class="takeaways">{lis}</ul></div>
<div class="disclaimer">Illustrative analysis built on hypothetical inputs. Not investment advice, a fairness opinion, or a recommendation to buy or sell any security.</div>
</main></body></html>"""


def build_banker_model(company: str, inp: DCFInputs, base: DCFResult, bars: list[Bar],
                       current_price: float, waccs, growths, bank: str = "") -> str:
    a = inp
    assumptions = [
        ("Revenue (last actual)", _money(a.revenue0) + "m"),
        ("Revenue growth, Y1 → Y" + str(len(a.growth)), f"{a.growth[0]:.1%} → {a.growth[-1]:.1%}"),
        ("EBIT margin", f"{a.ebit_margin:.1%}"),
        ("Tax rate", f"{a.tax_rate:.1%}"),
        ("D&A / capex / NWC (% revenue)", f"{a.da_pct_revenue:.1%} / {a.capex_pct_revenue:.1%} / {a.nwc_pct_revenue:.1%}"),
        ("WACC", f"{a.wacc:.2%}"),
        ("Terminal growth", f"{a.terminal_growth:.2%}"),
        ("Exit multiple (cross-check)", f"{a.exit_multiple:.1f}x EBITDA"),
        ("Net debt", _money(a.net_debt) + "m"),
        ("Diluted shares", f"{a.shares:,.1f}m"),
    ]
    arows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in assumptions)
    exit_res = value(a, "exit")
    bridge = (f"<table><tr><th>Bridge ($m)</th><th>Value</th></tr>"
              f"<tr><td>PV of unlevered FCF</td><td>{base.pv_fcf:,.1f}</td></tr>"
              f"<tr><td>PV of terminal value (perpetuity)</td><td>{base.pv_terminal:,.1f}</td></tr>"
              f"<tr><td><b>Enterprise value</b></td><td><b>{base.enterprise_value:,.1f}</b></td></tr>"
              f"<tr><td>Less: net debt</td><td>({a.net_debt:,.1f})</td></tr>"
              f"<tr><td><b>Equity value</b></td><td><b>{base.equity_value:,.1f}</b></td></tr>"
              f"<tr><td>Value per share</td><td>{_money(base.per_share)}</td></tr>"
              f"<tr><td>Exit-multiple cross-check, per share</td><td>{_money(exit_res.per_share)}</td></tr>"
              f"<tr><td>Terminal value share of EV</td><td>{base.terminal_share_of_ev:.0%}</td></tr></table>")
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(company)} banker model</title>
<style>{CSS}</style></head><body><main>
<h1>{html.escape(company)}: banker model</h1>
<div class="sub">Internal detail{(' · ' + html.escape(bank)) if bank else ''} · all figures $m except per share</div>
<h2>Assumptions</h2><div class="card"><table>{arows}</table></div>
<h2>Projections and unlevered free cash flow</h2><div class="card">{_projection_table(base)}</div>
<h2>DCF bridge</h2><div class="card">{bridge}</div>
<h2>Sensitivity: value per share, WACC × terminal growth</h2>
<div class="card">{sensitivity_table(a, waccs, growths, current_price)}
<div class="note">Darker cells are higher values. Cells with WACC ≤ g are undefined.</div></div>
<h2>Football field (per share)</h2>
<div class="card">{football_svg(bars, current_price)}</div>
<div class="disclaimer">Internal working model on hypothetical inputs. Verify all inputs against filings and market data before any use.</div>
</main></body></html>"""
