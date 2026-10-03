# Data audit — MAS credit & charge cards (repo 02)

**Files:** `data/raw/credit-charge-cards-quarterly.csv` (primary) + `credit-charge-cards-annual.csv` (cross-check).
Both pulled scripted from data.gov.sg on **2026-10-03** (`pull_manifest.json` has SHA-256 + coverage per file).
The quarterly dataset's own metadata records *Data Last Updated: 31/08/2026* (update frequency: quarterly).
Produced by `src/audit.py` (stdlib only — independent of the DuckDB pipeline by design).

## Shape & units (the `[VERIFY]`s, resolved from the live files)

- **Coverage:** quarterly file = **47 quarters, 2014 Q4 → 2026 Q2, no gaps**; annual file = 2014 → 2025.
- **Fields:** exactly **6 series** (no hidden columns): Principal Cardholders · Supplementary Cardholders · Total Card Billings · Rollover Balance · Bad Debts Written Off · Charge-Off Rates. **282/282 cells populated — 0 nulls.**
- **Units — stated per the publisher:** cardholders = number of cards; billings, rollover and write-offs = **S$ millions** (per quarter); charge-off rate = **% annualised**.
- **Rate definition (MAS I.17 note):** bad debts written off in the period ÷ the average rollover balance for the period, **annualised**. The rate's denominator is **rollover** — a revolving balance (stock) — not billings (a spending flow). Never conflated with a default probability.

| Series | min | max |
|---|---|---|
| Principal cardholders | 5,231,538 | 6,349,360 |
| Supplementary cardholders | 863,831 | 1,343,358 |
| Total card billings (S$M/qtr) | 10,618.7 | 27,992.2 |
| Rollover balance (S$M) | 5,148.9 | 9,640.8 |
| Bad debts written off (S$M/qtr) | 47.3 | 138.1 |
| Charge-off rate (% annualised) | 3.4 | 9.1 |

No duplicate quarters, no structural oddities — an official aggregate series; nothing excluded (282/282 cells retained).

## Cross-check: quarterly sums vs the published annual file

Σ of the four quarterly values vs the published annual figure — write-offs agree to ≤ **0.1 S$M** in every year (rounding: quarterly cells are published to 0.1). The annual rate **recomputed as Σ write-offs ÷ average of the four quarter-end rollover balances** agrees with the published annual rate within **±0.05 pt in 11/11 full years** — including 2020 (7.08 vs 7.1):

| year | ΔΣwrite-offs (0.1 S$M) | recomputed % | published % |
|---|---|---|---|
| 2015–2019 | ≤ ±0.1 | 5.69 · 4.87 · 4.74 · 5.99 · 5.85 | 5.7 · 4.9 · 4.7 · 6.0 · 5.8 |
| 2020 | −0.1 | **7.08** | **7.1** |
| 2021–2025 | ≤ ±0.1 | 4.48 · 3.54 · 4.02 · 5.44 · 5.83 | 4.5 · 3.5 · 4.0 · 5.4 · 5.8 |

(The small residuals are consistent with the publisher averaging monthly balances while we only see quarter-end balances — documented, not hidden.)

## Rules chosen, before analysis (from the profile above)

1. **Calendar years, complete only.** Headline = **2025 vs 2024** — the latest two *complete* years (2026 has two quarters; it enters only through the trailing-4-quarter sensitivity variant). Never compare single quarters sitting at different points of the year.
2. **The bridge runs on the recomputed annual rate** (`Σ write-offs ÷ average of the four quarter-end balances`) so that write-offs = rate × rollover holds **exactly** at full precision; the published rate (rounded to 0.1) is displayed alongside and compared — the ±0.05 pt agreement above is the receipt.
3. **Peak year = 2020** (published 7.1%, recomputed 7.08% — the series maximum). The 2020-vs-2019 split ships beside the headline so one year's rise is not framed as a record.
4. **Seasonality is real:** within 2024 the quarterly published rate ranged 5.0 → 6.5; annual sums (or same-position quarters) absorb it.
5. **No outlier rule.** An official aggregate has no micro-outliers to trim; trimming aggregates would fabricate cleanliness.
6. **Card counts are context only** (millions of cards in circulation) — not part of the rate→volume bridge.
