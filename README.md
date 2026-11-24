# nvda-valuation

An equity valuation of NVIDIA (NVDA) by **Shubham**, built on FY2026 filings. It runs a DCF with two terminal methods, a WACC × terminal-growth sensitivity, and a client and banker report.

> This is an illustrative valuation, not investment advice, a fairness opinion, or a recommendation to buy or sell NVDA. The growth, margin, and discount-rate assumptions are judgments, and the result is sensitive to them. Verify inputs and update the share price before relying on any figure.

## Results (base case)

| Method | Value per share | Notes |
|---|---|---|
| DCF, perpetuity growth | **$141.31** | 10% WACC, 3% terminal growth |
| DCF, exit multiple | **$219.05** | 20x year-5 EBITDA, discounted at 10% |
| Last close found | $215.38 | About Oct 28, 2026. Refresh before use. |

The two methods disagree by about 55%. The perpetuity value depends on sustaining growth at a 3% rate after year 5, and that assumption carries most of the value. The exit value assumes the market still pays 20x EBITDA in year 5. Read the gap as the range of outcomes, not a point estimate.

## Data

**FY2026 actuals** (fiscal year ended Jan 25, 2026), from the Form 10-K and the Q4 FY26 press release:

- Revenue $215,938m; GAAP operating income $130,387m (60.4% margin); net income $120,067m
- Operating cash flow $102,718m; capex $6,042m; D&A $2,843m
- Cash $10,605m; marketable securities $51,951m; debt $8,468m, giving net cash of $54,088m
- Diluted weighted shares 24,514m; 24.2bn shares outstanding at May 15, 2026

**Market data:** the $215.38 close and the $164.27–$243.37 52-week range came from search results. The close is dated about Oct 28, 2026. Update `CURRENT_PRICE` in the script before use.

**Assumptions (not sourced):** revenue growth of 50%, 30%, 20%, 12%, 8% over five years; a 58% EBIT margin; a 16% tax rate; NWC at 10% of revenue; a 10% WACC; 3% terminal growth; a 20x exit multiple. All of them are in `scripts/make_nvda_report.py` and the banker view labels them.

## Quick start

```bash
pip install -e ".[dev]"
pytest -q                                   # 6 tests
PYTHONPATH=src python scripts/make_nvda_report.py
```

Outputs go to `docs/`: `nvda_dashboard.html` (Client and Banker tabs), `nvda_client_summary.html`, and `nvda_banker_model.html`.

## Method

- Unlevered FCF = EBIT × (1 − tax) + D&A − capex − Δ NWC, discounted at WACC with end-of-year cash flows.
- Perpetuity terminal value = final-year FCF × (1 + g) / (WACC − g). Exit terminal value = year-5 EBITDA × multiple.
- Equity value = enterprise value + net cash. Per share = equity / diluted shares.

## Limitations

- The model is a single-scenario, five-year DCF. It has no scenario weighting and no comparable-company cross-check, because I could not verify peer multiples.
- Stock-based compensation (about $6.4bn in FY26) is not deducted from free cash flow. Treating it as a cash cost would lower the value.
- The tax rate and NWC are assumptions, not reported figures.

## Layout

```
src/ibval/        DCF engine and report builders (copied from ib-valuation-toolkit)
scripts/          make_nvda_report.py: inputs, valuation, and reports
tests/            6 tests: net cash, margins, equity bridge, method ordering, sensitivity, bars
docs/             generated HTML reports
```

## License

MIT. © Shubham
