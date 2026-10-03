# Data audit — MAS credit & charge cards

**Files:** `data/raw/credit-charge-cards-quarterly.csv` (primary) + `credit-charge-cards-annual.csv` (cross-check) — both **committed to the repo as vendored copies** (small files; the Singapore Open Data Licence allows redistribution with attribution). Pulled scripted from data.gov.sg on **2026-10-03**; `pull_manifest.json` carries SHA-256 **of the file bytes** (matches `sha256sum`) + coverage per file.
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

## The dictionary: flows vs stocks (why the annual file has two kinds of row)

| kind | series | annual figure is… | rule |
|---|---|---|---|
| **flow** | Total Card Billings · Bad Debts Written Off | the **sum** of the year's four quarters | match Σ quarters within 0.1 S$M (cells are published to 0.1) |
| **stock** | Rollover Balance · cardholders | the **year-end value (= Q4)** | equal Q4 exactly — and **never** the average the bridge uses |

The bridge's balance denominator is the **average of the four quarter-end balances** (2025: 8,920.3 S$M); the annual file's rollover is the year-end stock (2025: 9,400.2 = Q4). Different quantities, both correct — comparing them as if interchangeable would read as a pipeline error. Both reconciliations print in `src/audit.py` and are **asserted** before any output is written in `src/analysis.py`.

## Cross-check: quarterly sums vs the published annual file — flows (yearly sums)

| year | ΔΣ write-offs (S$M) | ΔΣ billings (S$M) | recomputed % | published % | Δrate |
|---|---|---|---|---|---|
| 2015 | −0.10 | +0.10 | 5.69 | 5.7 | −0.01 |
| 2016 | 0.00 | 0.00 | 4.87 | 4.9 | −0.03 |
| 2017 | +0.10 | +0.10 | 4.74 | 4.7 | +0.04 |
| 2018 | 0.00 | 0.00 | 5.99 | 6.0 | −0.01 |
| 2019 | 0.00 | −0.10 | 5.85 | 5.8 | +0.05 |
| 2020 | −0.10 | 0.00 | **7.08** | **7.1** | −0.02 |
| 2021 | 0.00 | 0.00 | 4.48 | 4.5 | −0.02 |
| 2022 | 0.00 | 0.00 | 3.54 | 3.5 | +0.04 |
| 2023 | +0.10 | −0.10 | 4.02 | 4.0 | +0.02 |
| 2024 | 0.00 | +0.10 | 5.44 | 5.4 | +0.04 |
| 2025 | −0.10 | 0.00 | 5.83 | 5.8 | +0.03 |

Both flow gaps stay within **0.1 S$M in every year** (rounding: quarterly cells are published to 0.1). The recomputed rate agrees with the published annual rate within **±0.05 pt in 11/11 years**. (The small residuals are consistent with the publisher averaging monthly balances while we only see quarter-end balances — documented, not hidden.)

## Cross-check: stocks (year-end = Q4) vs the bridge's averages

| year | rollover Q4 | rollover avg-of-4 (bridge) | principal cards Q4 | principal avg-of-4 |
|---|---|---|---|---|
| 2024 | 8,298.8 | 7,785.5 | 6,271,929 | 6,200,077 |
| 2025 | 9,400.2 | 8,920.3 | 6,135,494 | 6,222,499 |

## Rules chosen, before analysis (from the profile above)

1. **Calendar years, complete only.** Headline = **2025 vs 2024** — the latest two *complete* years (2026 has two quarters; it enters only through the trailing-4-quarter and H1-vs-H1 variants). Never compare single quarters sitting at different points of the year.
2. **The bridge runs on the recomputed annual rate** (`Σ write-offs ÷ average of the four quarter-end balances`) so that write-offs = rate × balance holds **exactly** at full precision; the published rate (rounded to 0.1) is displayed alongside and compared — the ±0.05 pt agreement above is the receipt.
3. **Peak year = 2020** (published 7.1%, recomputed 7.08% — the series maximum). The 2020-vs-2019 split ships beside the headline so one year's rise is not framed as a record.
4. **Seasonality is mild — and 2024 is not a seasonal story.** Mean published rate by quarter-of-year over the complete years 2015–2025:

| quarter | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| mean % | 5.34 | 5.29 | 5.51 | 5.25 |

   The typical seasonal range is **≈0.25 pt**; 2024's within-year move (5.0 → 6.5) is a **level shift plus a spike**, not this pattern. Annual windows are used because the rate changed *level* mid-series, not because seasonality is large.
5. **No outlier rule.** An official aggregate has no micro-outliers to trim; trimming aggregates would fabricate cleanliness.
6. **Card counts are part of the analysis, not context.** They feed the per-card splits (`outputs/book_split.csv`): 2025's balance growth is **not more customers** (total cards −0.4%; balance per card +15%).

## Flagged breaks & freshness — carried into the write-up

- **2025 Q3 principal-card break:** 6,349,360 → 6,095,333 in one quarter (−254,027, **−4.0%**) — the largest one-quarter move in the file — then held at ~6.1–6.2M. **Flagged, not explained** (a definition change, a purge, or real — the file cannot say). 2025 card averages inherit it.
- **Supplementary cards:** −32% over the decade, down in 10/10 years since 2015 — gradual and continuous, unlike the Q3 break.
- **The two newest quarters can be restated** (write-off registrations; provisional upstream data). The downloader's freshness floor is "latest quarter within **two quarters of today**" — a fixed floor would silently go stale.
- **"Volume" caveat:** balance growth can be slower repayment (stress) as well as expansion — write-offs lag stress; see the README Limits.
