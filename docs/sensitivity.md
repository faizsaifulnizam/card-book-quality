# Sensitivity — the bridge across windows, bases and weights

**Fixed snapshot: 2026-10-03 pull, quarterly coverage through 2026 Q2.** Headline: **2025 vs 2024** — write-offs **+96.5 S$M = balance +63.9 + recomputed proxy ratio +32.6** (midpoint weights). Every variant below re-runs the same arithmetic on a different window, rate basis, or weighting. Machine-readable: [`outputs/sensitivity.csv`](../outputs/sensitivity.csv) · regenerate with `python src/analysis.py`. All money figures S$M.

**Two kinds of leftover term — kept apart, because they are not the same thing:**
- **joint term** — ΔR × Δr, the true second-order term. Midpoint weights split it symmetrically (reports as 0); base weights surface it (+4.4).
- **basis-and-rounding residual** — the closure gap when published annual rates are substituted into our quarter-end-average balance bridge (−0.46). The unobserved publisher averaging basis and published rounding cannot be separated here; it is not justified to attribute all of it to rounding, or call it an interaction.

| variant | window (new side) | Δ write-offs | volume | rate | joint term | residual | what it tests |
|---|---|---|---|---|---|---|---|
| annual 2025 vs 2024 (base) | 2025 | +96.5 | +63.9 | +32.6 | 0 | — | the headline split |
| annual 2020 vs 2019 (peak year) | 2020 | +31.8 | −41.2 | +73.0 | 0 | — | the opposite shape — rate-led on a shrinking book |
| trailing 4 quarters | 2025 Q3 – 2026 Q2 | +79.3 | +58.4 | +20.9 | 0 | — | freshest data (includes 2 quarters outside the annual table) |
| same two quarters, year apart | H1 2026 vs H1 2025 | +23.7 | +27.2 | −3.5 | 0 | — | a same-season short read — the ratio term subtracts |
| published annual-rate basis | 2025 | +96.5 | +63.6 | +33.4 | — | −0.46 | rates read off the rounded published table |
| base-weighted 3-term | 2025 | +96.5 | +61.7 | +30.4 | +4.4 | 0 | anchor-year weights; the joint term surfaced |

## How to read it

- **Dollars still rising; the mix is moving.** Every variant shows a positive change, and volume outweighs rate — except 2020, where the book *shrank* and the rate alone drove the rise (volume −41.2, rate +73.0). But the freshest reads narrow: on the trailing window volume is ~three-quarters; on the H1 read the **rate term is negative (−3.5)** — the charge-off rate is no longer contributing.
- **The rate is a shelf, not a drift.** The annual-average line 5.44% → 5.83% is a *lagging* average of a step that already happened: the published quarterly rate has sat at 5.9–6.0% for six quarters. Read it as "the level reset in 2024", not "the rate is still climbing".
- **The two quarters not yet in any annual figure** (2026 H1) show the same dollar direction — the trailing window uses them and the split barely moves (58.4 / 20.9).
- **Basis check:** reading rates from the published annual table (5.4% → 5.8%) changes the balance term by **−0.350665 S$M** and the ratio term by **+0.812415 S$M**. The old “within ±0.5 S$M” claim was false for the ratio term. The separate **basis-and-rounding residual is −0.461750 S$M**; see the full-precision calculation below.
- **Weighting choice, made visible:** with midpoint weights the two terms close exactly and the joint term reports as 0; with base-year weights it surfaces at +4.4 S$M (≈5% of the change). Both variants ship in the table so the choice of midpoints is auditable, not an assumption to take on faith.
- **Not a forecast.** Variants re-describe the same fixed history; none projects. A refresh or source revision requires reviewing outputs and maintained text together.

## Independent published-rate calculation

Raw quarterly data give average rollover **7,785.475 → 8,920.300** and summed write-offs **423.2 → 519.7**. Proxy ratios are `423.2 / 7785.475` and `519.7 / 8920.3`; they are not observed monthly-average ratios.

| Contribution | Proxy basis | Published basis | Published minus proxy |
|---|---:|---:|---:|
| Balance: Δbalance × average ratio | 63.900865 | 63.550200 | **−0.350665** |
| Ratio: Δratio × average balance | 32.599135 | 33.411550 | **+0.812415** |

`96.5 − 63.550200 − 33.411550 = −0.461750` is the closure residual, separate from each contribution's change. Independent raw-CSV regression: [`tests/test_narrative.py`](../tests/test_narrative.py).

## Card denominator and aggregation sensitivity

The midpoint balance split is `Δbalance = Δcount × average(balance/count) + Δ(balance/count) × average(count)`. These values were independently calculated from the raw quarterly file; year-end rows decompose a different balance total from annual-average rows.

| 2025 vs 2024 basis | Δbalance | Count component | Per-card proxy component | Count change |
|---|---:|---:|---:|---:|
| Annual-average, total reported cards | +1,134.825 | **−31.808** | +1,166.633 | −0.380% |
| Annual-average, principal only | +1,134.825 | **+30.149** | +1,104.676 | +0.362% |
| Year-end Q4, total reported cards | +1,101.400 | **−228.379** | +1,329.779 | −2.545% |
| Year-end Q4, principal only | +1,101.400 | **−194.779** | +1,296.179 | −2.175% |

Supplementary declines affect the annual-average total-card sign. Principal averages rise slightly while year-end principal counts fall. The unexplained **2025 Q2 → Q3 principal-count break** affects both measures differently; no adjustment is invented. The per-card proxy component dominates each row, but principal counts are not deduplicated customers. Aggregate rollover per reported card includes non-revolving cards and is not average debt among revolving borrowers.

**Same-season is not seasonality-free:** H1-vs-H1 avoids different quarter positions; pooled quarter means do not isolate seasonality from changing levels or unusual years. A ratio change does not isolate credit quality, and balance growth does not prove stress. Unique customers, repayment, utilisation and borrower/vintage information are unavailable.
