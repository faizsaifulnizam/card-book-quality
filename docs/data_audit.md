# Data audit — MAS credit & charge cards

**Files:** `data/raw/credit-charge-cards-quarterly.csv` (primary) + `credit-charge-cards-annual.csv` (cross-check) — both **committed to the repo as vendored copies** (small files; the Singapore Open Data Licence allows redistribution with attribution). Pulled scripted from data.gov.sg on **2026-10-03**; `pull_manifest.json` records file-byte SHA-256 and coverage per file. No new hash comparison is asserted by this audit write-up.
The committed quarterly metadata records *Data Last Updated: 31/08/2026* (quarterly frequency). Metadata JSONs are **historical reference captures**, not guaranteed to refresh with the CSVs. This is a **fixed historical analysis**, not a live feed.
This manually maintained document is **based on output from `src/audit.py`**, rerun during this review (stdlib only, independent of DuckDB). The script prints evidence and runs in `run_all.py`; it does not produce this manually maintained Markdown file.

## Shape & units (the committed snapshot)

- **Coverage:** quarterly file = **47 quarters, 2014 Q4 → 2026 Q2, no gaps**; annual file = 2014 → 2025.
- **Fields:** exactly **6 series** (no hidden columns): Principal Cardholders · Supplementary Cardholders · Total Card Billings · Rollover Balance · Bad Debts Written Off · Charge-Off Rates. **282/282 cells populated — 0 nulls.**
- **Units used in this analysis:** principal/supplementary counts are reported card series, not deduplicated customers; billings and write-offs are **S$ million period flows**; rollover is a **S$ million quarter-end stock**; published charge-off rate is **% annualised**, not an interest rate or default probability. The generic dataset column metadata alone does not establish all of these definitions.
- **Publisher definition versus our proxy:** the historical MAS I.17 search result describes annual charge-off rate as yearly bad debts written off divided by average rollover for that year, and quarterly rates as annualised quarterly ratios. Full current notes were not retrievable in this review (see source trail below), so no fresh verification of monthly averaging or revision rules is claimed. Our computable annual proxy is explicitly **sum of quarterly write-offs ÷ average of four quarter-end rollover stocks**; exact bridge closure follows our chosen denominator.

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

Both flow gaps stay within **0.1 S$M in every year** (quarterly cells are published to 0.1). The recomputed proxy ratio agrees with the published annual rate within **±0.05 pt in 11/11 years in this snapshot**. Empirical agreement does not prove denominator equivalence, or a universal tolerance for refreshed data. Unobserved averaging-basis differences and rounding are not separately quantified.

## Cross-check: stocks (year-end = Q4) vs the bridge's averages

| year | rollover Q4 | rollover avg-of-4 (bridge) | principal cards Q4 | principal avg-of-4 |
|---|---|---|---|---|
| 2024 | 8,298.8 | 7,785.5 | 6,271,929 | 6,200,077 |
| 2025 | 9,400.2 | 8,920.3 | 6,135,494 | 6,222,499 |

## Rules chosen, before analysis (from the profile above)

1. **Calendar years, complete only.** Headline = **2025 vs 2024** — the latest two *complete* years (2026 has two quarters; it enters only through the trailing-4-quarter and H1-vs-H1 variants). Never compare single quarters sitting at different points of the year.
2. **The bridge runs on the recomputed annual rate** (`Σ write-offs ÷ average of the four quarter-end balances`) so that write-offs = rate × balance holds **exactly** at full precision; the published rate (rounded to 0.1) is displayed alongside and compared — the ±0.05 pt agreement above is the receipt.
3. **Peak year = 2020** (published 7.1%, recomputed 7.08% — the series maximum). The 2020-vs-2019 split ships beside the headline so one year's rise is not framed as a record.
4. **Descriptive pooled quarter means, not seasonal adjustment.** Mean published rate by quarter-of-year over complete years 2015–2025:

| quarter | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| mean % | 5.34 | 5.29 | 5.51 | 5.25 |

   The pooled mean range is **≈0.25 pt**, but these means mix yearly level changes and unusual years with any seasonal pattern. They do not identify pure seasonality or prove that 2024's move (5.0 → 6.5) was unrelated to it. Annual and H1-vs-H1 windows compare like positions; they are **same-season**, not seasonality-free.
5. **No outlier rule.** An official aggregate has no micro-outliers to trim; trimming aggregates would fabricate cleanliness.
6. **Card counts are part of the analysis, not customer identification.** Average total reported cards fell 0.4%; aggregate rollover per reported card rose 15%. Unique customers and revolving-account counts cannot be measured. The ratio includes non-revolving cards and is not mean borrower debt. Total-card versus principal-only and annual-average versus year-end sensitivities are disclosed in [`sensitivity.md`](sensitivity.md).

## Flagged breaks & freshness — carried into the write-up

- **2025 Q3 principal-card break:** 6,349,360 → 6,095,333 in one quarter (−254,027, **−4.0%**) — the largest one-quarter move in the file — then held at ~6.1–6.2M. **Flagged, not explained** (a definition change, a purge, or real — the file cannot say). 2025 card averages inherit it.
- **Supplementary cards:** −32% over the decade, down in 10/10 years since 2015 — gradual and continuous, unlike the Q3 break.
- **Revisions and freshness:** the analysis is frozen to this pull; source revisions can change values. The downloader has a moving freshness floor, but that does not refresh maintained prose. Exact current publisher revision rules were not retrieved here.
- **Balance caveat:** growth can reflect spending or slower repayment; this file does not establish stress. Ratio movements may reflect mix, accounting, recoveries, write-off timing and denominator changes as well as credit quality.

## Source trail and retrieval limits

The retrieved official dataset page identifies MAS as source and links SingStat table **M701051**.[1] Its retrieved copy showed coverage only through 2026 Q1 and an earlier update date than the committed metadata; it was not used to replace or re-date our fixed snapshot. Generic column legends are not governing notes for each economic series.

- [SingStat source table M701051](https://tablebuilder.singstat.gov.sg/table/TS/M701051): linked by the retrieved publisher page; table-body extraction failed.
- [MAS current I.17A page](https://www.mas.gov.sg/statistics/monthly-statistical-bulletin/i-17a-credit-and-charge-card-statistics): returned maintenance/unavailable; browser attempt timed out.
- [MAS historical I.17](https://eservices.mas.gov.sg/statistics/msb-xml/msb-statistics-history/Report.aspx?tableSetID=D.H&tableID=I.17): search surfaced formula notes and a June 2018 count-label change, but direct extraction redirected to a removed-page error. Search snippets are a lead, not verification of the current note text.

Therefore **exact current notes for count scope, rollover averaging, write-off treatment and revision rules remain a publisher-evidence gap**. The links above are provenance leads, not a claim that their full notes were successfully verified. Our flow/stock treatment is independently cross-checked against the committed annual data, and our quarter-end proxy denominator is an analyst choice. Do not silently promote either to a newly verified publisher definition.

## Sources

[1] [Quarterly dataset page (retrieved content differs from committed snapshot)](https://data.gov.sg/datasets/d_5c8e5801c2a64e2e6b16608296ef3e02/view)
