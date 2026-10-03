<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/banner.svg">
  <img src="assets/banner.svg" width="100%" alt="card-book-quality — did card write-offs rise because the book grew or because the charge-off rate worsened">
</picture>

# card-book-quality

**Muhammad Faiz Saifulnizam** · data-analytics portfolio, Singapore · [github.com/faizsaifulnizam](https://github.com/faizsaifulnizam)

[![CI](https://github.com/faizsaifulnizam/card-book-quality/actions/workflows/ci.yml/badge.svg)](https://github.com/faizsaifulnizam/card-book-quality/actions/workflows/ci.yml) [![license: MIT](https://img.shields.io/badge/license-MIT-C0552B.svg)](LICENSE) ![Python 3.12](https://img.shields.io/badge/Python-3.12-2E7D6B.svg) ![DuckDB](https://img.shields.io/badge/analytics-DuckDB-22607B.svg) [![data: data.gov.sg](https://img.shields.io/badge/data-data.gov.sg-14293D.svg)](https://data.gov.sg/datasets/d_5c8e5801c2a64e2e6b16608296ef3e02/view) [![Excel quick-check](https://img.shields.io/badge/Excel-quick--check%20included-8A6EAF.svg)](outputs/quick_check.xlsx)

> **Answer:** Write-offs are at a series high (**519.7 S$M** in 2025, **+96.5** vs 2024) for two reasons, in sequence: the **charge-off rate reset in 2024** (**+1.42 pt** on the annual average, then six quarters parked around **5.9–6.0%** published) and then the **revolving balance kept growing in 2025** (+14.6% average). The 2025 delta splits **volume +63.9 / rate +32.6 S$M** (midpoint weights) — and it is *not* more customers: total cards **−0.4%**, balances per card **+15%** (S$1,089 → S$1,252). Balance growth is not automatically health — it also happens when repayment slows. 2020 remains the opposite shape: the book **shrank** and the rate alone drove the rise (**volume −41.2 + rate +73.0 = +31.8**). Descriptive, all issuers, no forecast.

**Status:** built 2026-10-03 · latest revision 2026-10-04 (external-review fixes: workbook formula, chart windows, per-card splits).

## Key numbers (all reproducible)

- **Headline (2025 vs 2024):** write-offs 423.2 → **519.7 S$M** (**+96.5**); bridge = volume **+63.9** + rate **+32.6 S$M**.
- **The path (why the level climbed +317.8 from 2022 to 2025):** **2024 vs 2023 = +152.8 = volume +50.0 + rate +102.8** — the year the rate reset; then **2025 vs 2024 = +96.5 = +63.9 + +32.6**; from the 2022 trough: **+317.8 = volume +150.4 + rate +167.4** — the rate term is the larger leg of the climb, not the smallest.
- **Rate:** 5.44% → 5.83% recomputed annual (published 5.4 → 5.8) — an annual average that **lags** the move that already happened: the step-up landed in 2024, and the published quarterly rate has sat at **5.9–6.0% for six quarters**; still below the **2020 peak (7.08% / 7.1% published)**.
- **The book, per card:** total cards **−0.4%** (principal +0.4%, supplementary **−5.2%** — down in 10 of the last 10 years); rollover per card **S$1,089 → S$1,252 (+15%)**; rollover/billings **0.321 → 0.344**; write-offs per principal card **S$68 → S$84 (+22%)**; the 2025 Δrollover **+1,135 S$M** splits cards **−32** + balance-per-card **+1,167** ([`outputs/book_split.csv`](outputs/book_split.csv)).
- **Robust across windows and bases:** trailing 4 quarters +79.3 = +58.4 + 20.9; the freshest two-quarter read is +23.7 = +27.2 − 3.5 — **the rate term is no longer adding**; reading rates off the published table moves the split ≤0.5 S$M ([`docs/sensitivity.md`](docs/sensitivity.md)).
- **Data quality:** 47 quarters (2014 Q4 – 2026 Q2), 282/282 cells retained, 0 exclusions; the recomputed rate reconciles with the published annual rate within **±0.05 pt in 11/11 years**; flows and stocks both reconcile against the published annual file ([`docs/data_audit.md`](docs/data_audit.md)).
- **Flagged, not explained:** principal cardholders fell **−4.0% in a single quarter** at 2025 Q3 (the largest move in the file) and stayed down — 2025 card averages are read with that break in mind ([`docs/data_audit.md`](docs/data_audit.md)).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="reports/figures/f1_timeline-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="reports/figures/f1_timeline.png">
  <img src="reports/figures/f1_timeline.png" width="100%" alt="Billings, write-offs, trailing 4-quarter write-offs and the charge-off rate, 2015–2026">
</picture>

*Billings · write-offs (quarterly) · write-offs (trailing 4 quarters — shown only for full windows) · the charge-off rate. 2015 Q1 – 2026 Q2.*

### More views

| | |
|---|---|
| <a href="reports/figures/f2_bridge.png"><picture><source media="(prefers-color-scheme: dark)" srcset="reports/figures/f2_bridge-dark.png"><source media="(prefers-color-scheme: light)" srcset="reports/figures/f2_bridge.png"><img src="reports/figures/f2_bridge.png" alt="Waterfall: 2025 vs 2024 (volume-led), 2024 vs 2023 (the rate step-up) and 2020 vs 2019 (peak), each split into volume and rate"></picture></a> | <a href="reports/figures/f3_contributions.png"><picture><source media="(prefers-color-scheme: dark)" srcset="reports/figures/f3_contributions-dark.png"><source media="(prefers-color-scheme: light)" srcset="reports/figures/f3_contributions.png"><img src="reports/figures/f3_contributions.png" alt="Stacked bars: each year's change in write-offs split into volume and rate, 2016–2025"></picture></a> |
| <a href="reports/figures/f4_book.png"><picture><source media="(prefers-color-scheme: dark)" srcset="reports/figures/f4_book-dark.png"><source media="(prefers-color-scheme: light)" srcset="reports/figures/f4_book.png"><img src="reports/figures/f4_book.png" alt="Cardholders (principal and supplementary), the rollover balance, and write-offs per principal card"></picture></a> | **Excel quick-check** — pick a quarter from a dropdown; the sheet pulls the quarter's figures, a 4-quarter rolling sum and the rate change (SUMIFS keyed to a quarter index — no OFFSET), and the Annual bridge sheet computes the split **as live formulas** ([`outputs/quick_check.xlsx`](outputs/quick_check.xlsx), formula-only). Also attached to the [latest release](https://github.com/faizsaifulnizam/card-book-quality/releases). |

*The waterfall for the latest year, the 2024 step-up and the 2020 peak (**f2**) · every year's change split volume vs rate, 2016–2025 (**f3**) · cards, the revolving balance and write-offs per principal card (**f4**) — full sizes in [`reports/figures/`](reports/figures/); half-page write-up in [`docs/decision_memo.md`](docs/decision_memo.md).*

## The question

Card write-offs are reported as a dollar amount, and a bigger number invites the wrong reading. The right question is two-dimensional: **did the book grow, or did the rate worsen?** The two look identical in a level chart and mean entirely different things. This repo splits the change arithmetically, defines the rate before any chart uses it, and shows the **path — not one delta**: the 2020 peak, the 2024 step-up (+1.42 pt), the 5.9–6.0% shelf since, and a 2025 whose rise is balance-driven but not customer-driven.

## The data

- **Credit and charge cards, quarterly** — MAS via [data.gov.sg](https://data.gov.sg/datasets/d_5c8e5801c2a64e2e6b16608296ef3e02/view): 47 quarters, 2014 Q4 – 2026 Q2, 6 series — cardholders (principal/supplementary), total billings, rollover balance, bad debts written off, charge-off rate. Cardholder counts feed the per-card splits in [`outputs/book_split.csv`](outputs/book_split.csv). An annual file rides along as a cross-check.
- **Units:** billings, rollover and write-offs in **S$ millions** (per quarter); the charge-off rate **% annualised** — bad debts written off ÷ average rollover balance, annualised (MAS definition).
- Licence: Singapore Open Data Licence (© Monetary Authority of Singapore / SingStat). Both raw files are **committed** under `data/raw/` as vendored copies (small; licence allows redistribution with attribution) with a SHA-256 manifest — a clone reproduces everything offline; `src/download.py --force` re-pulls.

## Method

DuckDB throughout; one row per quarter after staging. The pipeline, end to end (or just `python src/run_all.py`):

1. **Pull** — scripted from data.gov.sg, structure-validated before replacing files, SHA-256 of the file bytes + coverage in a manifest: [`src/download.py`](src/download.py)
2. **Audit** — profile, units, the rate definition, and the flows-vs-stocks reconciliation checked against the published annual figures *before* analysis: [`docs/data_audit.md`](docs/data_audit.md)
3. **Stage** — the raw file is wide (one row per series, one column per quarter): unpivot → parse labels ('20262Q' = 2026 Q2) → one tidy table; every cell accounted for: [`sql/01_staging.sql`](sql/01_staging.sql)
4. **Check** — 8 assertions (series completeness, contiguity, ranges), run *before* the parquet is written; failures leave existing files untouched: [`sql/03_checks.sql`](sql/03_checks.sql) — 8/8 pass, 282/282 cells
5. **Measure** — annual aggregates, complete years only; the trailing-4-quarter sum is `ROWS 3 PRECEDING` and stays blank until four quarters exist (no partial windows): [`sql/02_metrics.sql`](sql/02_metrics.sql)
6. **Bridge** — the rate-vs-volume split, the book split (cards × balance-per-card) and sensitivity: [`src/analysis.py`](src/analysis.py) → [`outputs/yearly_bridge.csv`](outputs/yearly_bridge.csv) · [`outputs/book_split.csv`](outputs/book_split.csv)
7. **Stress** — window, basis and weighting variants: [`docs/sensitivity.md`](docs/sensitivity.md)
8. **Draw · write · check** — four figures as code, light + dark, copied to `docs/img/` in the same run ([`src/figures.py`](src/figures.py)); the memo ([`docs/decision_memo.md`](docs/decision_memo.md)); the Excel quick-check with live bridge formulas ([`src/build_workbook.py`](src/build_workbook.py))

### The comparison, made computable

Three choices make the question answerable: **complete calendar years — 2025 vs 2024** (annual sums keep the provisional newest quarters out of the headline; seasonality here is mild — quarter-of-year averages sit at 5.25–5.51%, a ~0.25 pt range — and 2024's within-year move of 5.0 → 6.5 is a level shift plus a spike, *not* that pattern; [seasonal table in the audit](docs/data_audit.md)); a **recomputed annual rate** — Σ write-offs ÷ the average of the four quarter-end rollover balances — so that write-offs = rate × balance holds *exactly* at full precision (the published rate, rounded to 0.1, is displayed beside it and reconciles within ±0.05 pt); and a **midpoint split** of the change — next.

### The bridge (the core, in words)

Write-offs are the product of a rate and a balance, so the change splits cleanly:

```text
Δ write-offs = Δrollover × avg rate    volume — the book grew
             + Δrate × avg rollover    rate — lending quality changed
```

**Volume** answers "same rate, bigger book"; **rate** answers "same book, worse rate". With midpoint weights (averages of the two years) the two terms exhaust the change exactly — the interaction is absorbed symmetrically and shows as 0; the base-weighted alternative (where the joint term is visible, +4.4 S$M — about 5% of the change) ships in the sensitivity table so the choice is auditable. **Why rollover and not billings:** the rate's denominator is the rollover balance — the interest-bearing balance carried month to month, the thing write-offs are actually measured against. Billings are *spending flow* through the card, a different quantity; using them would answer a different question. **Scope of volume:** balance growth from all causes — and it splits further: **Δrollover +1,135 S$M (2025 vs 2024) = cards −32 + balance-per-card +1,167** (per card: S$1,089 → S$1,252, +15%; total cards −0.4% — [book split CSV](outputs/book_split.csv)). And **"volume" is not a health signal**: balances also grow when repayment slows — borrowers stressed but not yet written off — which this split cannot separate from expansion.

### Rules chosen, and why

| Rule | Choice | Why |
|------|--------|-----|
| Comparison | calendar **2025 vs 2024** | latest complete years; annual sums keep the provisional newest quarters out and absorb the mild seasonal swing. 2026's two quarters enter via the trailing-window variant |
| Rate basis | **recomputed** annual: Σ write-offs ÷ avg quarter-end rollover | write-offs = rate × balance holds exactly; published rate shown beside it, reconciles ±0.05 pt (11/11 years) |
| Split | **midpoint weights** | volume + rate exhaust the change exactly; the base-weighted variant (+4.4 S$M joint term) is shown in sensitivity |
| Cards | used in the per-card splits | "the book grew" ≠ "more customers": total cards −0.4% in 2025 — the growth is per-card balance ([book split CSV](outputs/book_split.csv)) |
| Outliers | none applied | an official aggregate series has nothing to trim — trimming aggregates would fabricate cleanliness |
| Seasonality | annual or same-position quarters only | never compare a Q1 against a Q3 |

### Validation — receipts, not claims

- **Independent recompute:** **every complete year** (11/11) is recomputed from the *raw CSV* in plain Python stdlib — write-offs, average balances and rates match the pipeline exactly (1e-6).
- **Rate reconciliation (empirical):** recomputed vs published annual rate — max |Δ| **0.049 pt** over 11 years (2020 included: 7.08 vs 7.1). The comparator is the published *annual* figure; the average of the four *quarterly* published rates differs by up to 0.22 pt and is documented, not hidden ([`docs/data_audit.md`](docs/data_audit.md)).
- **Flow/stock reconciliation (empirical):** flows (write-offs, billings) sum to the published annual figures within **0.1 S$M**; stocks (rollover, cardholders) equal the **year-end Q4** value exactly — the annual file and the pipeline cannot silently disagree.
- **8/8 checks** pass on the staged table; **282/282 cells** (6 series × 47 quarters) retained, **0 exclusions** — reconciliation printed by [`src/build_dataset.py`](src/build_dataset.py).
- **Workbook recompute:** `build_workbook.py` scopes every sheet for `OFFSET` (zero found) and asserts the 4-quarter formula's inputs — the SUMIFS row window keyed to the quarter index — sum to the same value Python computes (**543.4** for the default selection on this pull).
- **Algebraic closure, not a finding:** with midpoint weights volume + rate ≡ Δ write-offs *by construction* — the interaction is split symmetrically, not discovered. The base-weighted alternative surfaces the joint term (+4.4 S$M) in the sensitivity table.
- **Sensitivity:** direction stable across the trailing 4-quarter window, the two-quarter read, the published-rate basis and the base-weighted variant — though the freshest two-quarter read has the **rate term at −3.5** (the rate is no longer adding), so "stable" is a statement about dollars, not the mix ([`docs/sensitivity.md`](docs/sensitivity.md)).
- **Determinism:** figures re-render byte-identical (hash-checked); the CSVs regenerate identical; CI re-runs the full pipeline on the committed raw files below.
- **Rounding:** contribution columns in the CSV are display-rounded to 2 dp; sums may differ from full precision by ≲0.05 S$M.
- **Stranger-rerun:** fresh clone → the commands below → the pipeline reproduces the committed outputs for the 2026-10-03 pull (a later re-pull can move the newest quarters).

### Limits

**Not a forecast; not causal; not a bank.** All issuers combined — this file cannot name an institution or a product, cannot say why the rate moved, and cannot time defaults. Write-offs are an accounting flow with issuer timing choices; the two newest quarters can be restated. **"Volume" is not a health signal** — the balance piece measures size, not cause: balances grow with spending and with slower repayment alike. The full list lives under **Caveats** below.

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

python src/run_all.py        # runs the five stages below, in order
# or individually:
python src/download.py       # raw CSVs → data/raw/ (already vendored in the repo; --force to re-pull)
python src/build_dataset.py  # staging + 8 checks → data/processed/quarterly.parquet
python src/analysis.py       # bridge + book split + sensitivity → outputs/
python src/figures.py        # four figures, light + dark → reports/figures/ + docs/img/
python src/build_workbook.py # rebuilds outputs/quick_check.xlsx
```

Then check `outputs/yearly_bridge.csv`: the 2025 row reads **Δ +96.5 = volume +63.9 + rate +32.6**, and opening `outputs/quick_check.xlsx` on its default selection (2026 Q2) shows write-offs **138.1** with a 4-quarter sum of **543.4** — the builder asserts the formula's row window produces that number in Python. No network needed: the raw files are committed. Data as of the 2026-10-03 pull — a later re-pull can move the newest quarters.

## Caveats

- **All issuers in Singapore, not one bank** — system aggregates from MAS via data.gov.sg.
- **"Volume" is not a clean bill of health.** Balances grow with spending *and* with slower repayment — including stress not yet written off (write-offs lag). The split measures how much of the change is balance vs rate; it cannot say which part of the balance growth is a warning.
- Write-offs are a flow with issuer timing; the newest quarters can be restated — the compared years are calendar-complete but not revision-final.
- **A flagged break in the card series:** principal cardholders fell **−4.0% in a single quarter at 2025 Q3** (−254,027 — the largest one-quarter move in the file) and stayed down; 2025 card averages are read with that break in mind. Not explained by anything in this dataset.
- The published quarterly rate is rounded to 0.1 pt and computed on monthly balances; the bridge uses the recomputed annual basis (reconciles ±0.05 pt annually) — both are shown.
- The midpoint split choice is visible: the base-weighted alternative shifts +4.4 S$M into a joint term (≈5% of the change).
- Descriptive only — no forecast, no causal claim. Drivers (interest rates, credit standards, relief measures) are out of scope.

## Out of scope

A default forecast or early-warning model, issuer-level attribution, monthly nowcasting, and cross-country comparisons built from this file.

## Licence

Code: MIT. Data: Singapore Open Data Licence — © Monetary Authority of Singapore / SingStat, via data.gov.sg. This is an independent, unofficial analysis.

---

*More Singapore public-data analysis: [hdb-resale-mart](https://github.com/faizsaifulnizam/hdb-resale-mart).*
