<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/banner.svg">
  <img src="assets/banner.svg" width="100%" alt="card-book-quality — a six-repo series on Singapore's public data">
</picture>

# card-book-quality

[![CI](https://github.com/faizsaifulnizam/card-book-quality/actions/workflows/ci.yml/badge.svg)](https://github.com/faizsaifulnizam/card-book-quality/actions/workflows/ci.yml) [![license: MIT](https://img.shields.io/badge/license-MIT-C0552B.svg)](LICENSE) ![Python 3.12](https://img.shields.io/badge/Python-3.12-2E7D6B.svg) ![DuckDB](https://img.shields.io/badge/analytics-DuckDB-22607B.svg) [![data: data.gov.sg](https://img.shields.io/badge/data-data.gov.sg-14293D.svg)](https://data.gov.sg/datasets/d_5c8e5801c2a64e2e6b16608296ef3e02/view) [![Excel quick-check](https://img.shields.io/badge/Excel-quick--check%20included-8A6EAF.svg)](outputs/quick_check.xlsx)

> **Answer:** Write-offs rose **+96.5 S$M to 519.7 S$M** in 2025 vs 2024 — and the split says **mostly the book, partly the rate**: volume **+63.9** vs rate **+32.6 S$M** (midpoint weights; the interaction is 0 by construction). The rate drifted up (recomputed 5.44% → 5.83%; published 5.4% → 5.8%) but stays well below its **2020 peak (7.08% / 7.1%)** — and 2020 was the *opposite* story: the book shrank and the rate alone drove the rise (**volume −41.2 + rate +73.0 = +31.8**). Descriptive, all issuers, one year's change.

**Status:** built 2026-10-03. Part of a six-repo series on Singapore's public data.

## Key numbers (all reproducible)

- **Headline (2025 vs 2024):** write-offs 423.2 → **519.7 S$M** (**+96.5**); bridge = volume **+63.9** + rate **+32.6** S$M.
- **Rate:** 5.44% → **5.83%** recomputed annual (published 5.4% → 5.8%) — still below the **2020 peak (7.08% / 7.1% published)**.
- **Robust across windows and bases:** trailing 4 quarters +79.3 = +58.4 + 20.9; the freshest two-quarter read is volume-only (+23.7 = +27.2 − 3.5); reading rates off the published table changes the split by ≤0.5 S$M ([`docs/sensitivity.md`](docs/sensitivity.md)).
- **Data quality:** 47 quarters (2014 Q4 – 2026 Q2), 282/282 cells retained, 0 exclusions; the recomputed rate reconciles with the published annual rate within **±0.05 pt in 11/11 years** ([`docs/data_audit.md`](docs/data_audit.md)).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="reports/figures/f1_timeline-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="reports/figures/f1_timeline.png">
  <img src="reports/figures/f1_timeline.png" width="100%" alt="Billings, write-offs and the charge-off rate with the rollover balance, 2015–2026">
</picture>

*Billings, write-offs (with the 4-quarter sum) and the charge-off rate — the rate's denominator (rollover, dashed) shown beside it, never conflated with default. 2015 Q1 – 2026 Q2.*

### More views

| | |
|---|---|
| <a href="reports/figures/f2_bridge.png"><picture><source media="(prefers-color-scheme: dark)" srcset="reports/figures/f2_bridge-dark.png"><source media="(prefers-color-scheme: light)" srcset="reports/figures/f2_bridge.png"><img src="reports/figures/f2_bridge.png" alt="Waterfall: 2025 vs 2024 and 2020 vs 2019 write-off changes split into volume and rate"></picture></a> | **Excel quick-check** — pick a quarter from a dropdown; the sheet pulls billings, rollover, write-offs, the published rate, a rolling 4-quarter sum and the rate-vs-last-year change ([`outputs/quick_check.xlsx`](outputs/quick_check.xlsx), formula-only). |

*The rate-vs-volume waterfall (`f2`) for the latest year and the 2020 peak — full size in [`reports/figures/`](reports/figures/) · half-page write-up in [`docs/decision_memo.md`](docs/decision_memo.md).*

## The question

Card write-offs are reported as a dollar amount, and a bigger number invites the wrong reading. The right question is two-dimensional: **did the book grow, or did the rate worsen?** The two look identical in a level chart and mean entirely different things. This repo splits the change arithmetically, defines the rate before any chart uses it, and shows the 2020 peak beside the latest year so neither is framed out of context.

## The data

- **Credit and charge cards, quarterly** — MAS via [data.gov.sg](https://data.gov.sg/datasets/d_5c8e5801c2a64e2e6b16608296ef3e02/view): 47 quarters, 2014 Q4 – 2026 Q2, 6 series — cardholders (principal/supplementary), total billings, rollover balance, bad debts written off, charge-off rate. An annual file rides along as a cross-check.
- **Units:** billings, rollover and write-offs in **S$ millions** (per quarter); the charge-off rate **% annualised** — bad debts written off ÷ average rollover balance, annualised (MAS definition).
- Licence: Singapore Open Data Licence (© Monetary Authority of Singapore / SingStat). A [script](src/download.py) downloads both files into `data/raw/` (gitignored, SHA-256 manifest); the raw files are never edited.

## Method

DuckDB throughout; one row per quarter after staging. The pipeline, end to end:

1. **Pull** — scripted from data.gov.sg, structure-validated before replacing files, SHA-256 + coverage in a manifest: [`src/download.py`](src/download.py)
2. **Audit** — profile, units, and the rate definition checked against the published annual figures *before* analysis: [`docs/data_audit.md`](docs/data_audit.md)
3. **Stage** — the raw file is wide (one row per series, one column per quarter): unpivot → parse labels ('20262Q' = 2026 Q2) → one tidy table; every cell accounted for: [`sql/01_staging.sql`](sql/01_staging.sql)
4. **Check** — 8 assertions (series completeness, contiguity, ranges), run *before* the parquet is written; failures leave existing files untouched: [`sql/05_checks.sql`](sql/05_checks.sql) — 8/8 pass, 282/282 cells
5. **Measure** — annual aggregates, complete years only: [`sql/02_metrics.sql`](sql/02_metrics.sql)
6. **Bridge** — the rate-vs-volume split + sensitivity: [`src/analysis.py`](src/analysis.py) → [`outputs/yearly_bridge.csv`](outputs/yearly_bridge.csv)
7. **Stress** — window, basis and weighting variants: [`docs/sensitivity.md`](docs/sensitivity.md)
8. **Draw · write · check** — figures are code, light + dark ([`src/figures.py`](src/figures.py)); the memo ([`docs/decision_memo.md`](docs/decision_memo.md)); the Excel quick-check ([`src/build_workbook.py`](src/build_workbook.py))

### The comparison, made computable

Three choices make the question answerable: **complete calendar years — 2025 vs 2024** (annual sums absorb the quarterly seasonal swing; within 2024 the published quarterly rate ranged 5.0 → 6.5, so a single-quarter comparison would read noise); a **recomputed annual rate** — Σ write-offs ÷ the average of the four quarter-end rollover balances — so that write-offs = rate × balance holds *exactly* at full precision (the published rate, rounded to 0.1, is displayed beside it and reconciles within ±0.05 pt); and a **midpoint split** of the change — next.

### The bridge (the core, in words)

Write-offs are the product of a rate and a balance, so the change splits cleanly:

```text
Δ write-offs = Δrollover × avg rate    volume — the book grew
             + Δrate × avg rollover    rate — lending quality changed
```

**Volume** answers "same rate, bigger book"; **rate** answers "same book, worse rate". With midpoint weights (averages of the two years) the two terms exhaust the change exactly — the interaction is absorbed symmetrically and shows as 0; the base-weighted alternative (where the joint term is visible, +4.4 S$M — about 5% of the change) ships in the sensitivity table so the choice is auditable. **Why rollover and not billings:** the rate's denominator is the rollover balance — the interest-bearing balance carried month to month, the thing write-offs are actually measured against. Billings are *spending flow* through the card, a different quantity; using them would answer a different question. Scope of **volume**: balance growth from all causes (more cards, more spending per card, slower repayment) — the split does not attribute *why* the balance grew.

### Rules chosen, and why

| Rule | Choice | Why |
|------|--------|-----|
| Comparison | calendar **2025 vs 2024** | latest complete years; annual sums absorb seasonality (2024's quarterly published rate ranged 5.0→6.5). 2026's two quarters enter via the trailing-window variant |
| Rate basis | **recomputed** annual: Σ write-offs ÷ avg quarter-end rollover | write-offs = rate × balance holds exactly; published rate shown beside it, reconciles ±0.05 pt (11/11 years) |
| Split | **midpoint weights** | volume + rate exhaust the change exactly; the base-weighted variant (+4.4 S$M joint term) is shown in sensitivity |
| Outliers | none applied | an official aggregate series has nothing to trim — trimming aggregates would fabricate cleanliness |
| Seasonality | annual or same-position quarters only | never compare a Q1 against a Q3 |

### Validation — receipts, not claims

- **8/8 checks** pass on the staged table; **282/282 cells** (6 series × 47 quarters) retained, **0 exclusions** — reconciliation printed by [`src/build_dataset.py`](src/build_dataset.py).
- **Independent recompute:** 3 years (2019, 2020, 2025) recomputed from the *raw CSV* in plain Python stdlib — write-offs, average balances and rates match the pipeline exactly (1e-6).
- **Rate reconciliation:** recomputed vs published annual rate — max |Δ| **0.049 pt** over 11 years (2020 included: 7.08 vs 7.1). The comparator is the published *annual* figure; the average of the four *quarterly* published rates differs by up to 0.22 pt and is documented, not hidden ([`docs/data_audit.md`](docs/data_audit.md)).
- **Identity asserts** on every bridge row: volume + rate + interaction == Δ write-offs (ε = 1e-9); interaction ≡ 0 with midpoint weights; the base-weighted alternative also closes exactly.
- **Sensitivity:** direction stable across the trailing 4-quarter window, the two-quarter read, the published-rate basis and the base-weighted variant ([`docs/sensitivity.md`](docs/sensitivity.md)).
- **Determinism:** figures re-render byte-identical; the CSV regenerates identical (`git diff --quiet`).
- **Rounding:** contribution columns in the CSV are display-rounded to 2 dp; sums may differ from full precision by ≲0.05 S$M.
- **Stranger-rerun:** fresh clone → the commands below → the pipeline reproduces the committed outputs for the 2026-10-03 pull (a later re-pull can move the newest quarters).

### Limits

**Not a forecast; not causal; not a bank.** All issuers combined — this file cannot name an institution or a product, cannot say why the rate moved, and cannot time defaults. Write-offs are an accounting flow with issuer timing choices; the two newest quarters can be restated. The full list lives under **Caveats** below.

### Principles this repo follows

1. **One question per repo** — the method serves the question, not the reverse.
2. **Define before use** — the annualised rate is defined (and reconciled to the published one) before any chart shows it.
3. **SQL first** — the numbers live in `sql/`; Python glues, splits and draws.
4. **Nothing hand-edited** — raw data immutable; every number regenerates from code.
5. **Limits are part of the deliverable.**

## Reproduce

```bash
git clone https://github.com/faizsaifulnizam/card-book-quality && cd card-book-quality
uv venv .venv --python 3.12          # or: python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt   # or: pip install -r requirements.txt

python src/download.py       # both raw CSVs → data/raw/ (gitignored; add --force to re-pull)
python src/build_dataset.py  # staging + 8 checks → data/processed/quarterly.parquet
python src/analysis.py       # annual bridge + sensitivity → outputs/
python src/figures.py        # re-renders reports/figures/ (light + dark)
python src/build_workbook.py # rebuilds outputs/quick_check.xlsx
```

Then check `outputs/yearly_bridge.csv`: the 2025 row reads **Δ +96.5 = volume +63.9 + rate +32.6**, and opening `outputs/quick_check.xlsx` on its default selection (2026 Q2) shows write-offs **138.1** with a 4-quarter sum of **543.4**. Data as of the 2026-10-03 pull — a later re-pull can move the newest quarters.

## Caveats

- **All issuers in Singapore, not one bank** — system aggregates from MAS via data.gov.sg.
- Write-offs are a flow with issuer timing; the newest quarters can be restated — the compared years are calendar-complete but not revision-final.
- The published quarterly rate is rounded to 0.1 pt and computed on monthly balances; the bridge uses the recomputed annual basis (reconciles ±0.05 pt annually) — both are shown.
- The midpoint split choice is visible: the base-weighted alternative shifts +4.4 S$M into a joint term (≈5% of the change).
- Descriptive only — no forecast, no causal claim. Drivers (interest rates, credit standards, relief measures) are out of scope.

## Out of scope

A default forecast or early-warning model, issuer-level attribution, monthly nowcasting, and cross-country comparisons built from this file.

## Licence

Code: MIT. Data: Singapore Open Data Licence — © Monetary Authority of Singapore / SingStat, via data.gov.sg. This is an independent, unofficial analysis.

---

*Part of a six-repo series on Singapore's public data — the other five repos go live as they're built:* **[hdb-resale-mart](https://github.com/faizsaifulnizam/hdb-resale-mart)** · **coe-quota-premium · retail-sales-split · coe-category-break · hdb-lease-slope**

*If you found this useful, a star helps others find it.*
