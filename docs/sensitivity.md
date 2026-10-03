# Sensitivity — the bridge across windows, bases and weights

Headline: **2025 vs 2024** — write-offs **+96.5 S$M = volume +63.9 + rate +32.6** (midpoint weights). Every variant below re-runs the same arithmetic on a different window, rate basis, or weighting. Machine-readable: [`outputs/sensitivity.csv`](../outputs/sensitivity.csv) · regenerate with `python src/analysis.py`. All money figures S$M.

**Two kinds of leftover term — kept apart, because they are not the same thing:**
- **joint term** — ΔR × Δr, the true second-order term. Midpoint weights split it symmetrically (reports as 0); base weights surface it (+4.4).
- **residual** — the closure gap when *rounded published* rates are substituted into the same arithmetic; a rounding artefact (−0.46), never called an interaction.

| variant | window (new side) | Δ write-offs | volume | rate | joint term | residual | what it tests |
|---|---|---|---|---|---|---|---|
| annual 2025 vs 2024 (base) | 2025 | +96.5 | +63.9 | +32.6 | 0 | — | the headline split |
| annual 2020 vs 2019 (peak year) | 2020 | +31.8 | −41.2 | +73.0 | 0 | — | the opposite shape — rate-led on a shrinking book |
| trailing 4 quarters | 2025 Q3 – 2026 Q2 | +79.3 | +58.4 | +20.9 | 0 | — | freshest data (includes 2 quarters outside the annual table) |
| same two quarters, year apart | H1 2026 vs H1 2025 | +23.7 | +27.2 | −3.5 | 0 | — | a seasonality-free short read — the rate term no longer adds |
| published annual-rate basis | 2025 | +96.5 | +63.6 | +33.4 | — | −0.46 | rates read off the rounded published table |
| base-weighted 3-term | 2025 | +96.5 | +61.7 | +30.4 | +4.4 | 0 | anchor-year weights; the joint term surfaced |

## How to read it

- **Dollars still rising; the mix is moving.** Every variant shows a positive change, and volume outweighs rate — except 2020, where the book *shrank* and the rate alone drove the rise (volume −41.2, rate +73.0). But the freshest reads narrow: on the trailing window volume is ~three-quarters; on the H1 read the **rate term is negative (−3.5)** — the charge-off rate is no longer contributing.
- **The rate is a shelf, not a drift.** The annual-average line 5.44% → 5.83% is a *lagging* average of a step that already happened: the published quarterly rate has sat at 5.9–6.0% for six quarters. Read it as "the level reset in 2024", not "the rate is still climbing".
- **The two quarters not yet in any annual figure** (2026 H1) show the same dollar direction — the trailing window uses them and the split barely moves (58.4 / 20.9).
- **Basis check:** reading rates straight off the published annual table (5.4% → 5.8%) reproduces the split within ±0.5 S$M — the rounding lands in the **residual** column, shown rather than hidden (and separate from the base-weighted variant's joint term).
- **Weighting choice, made visible:** with midpoint weights the two terms close exactly and the joint term reports as 0; with base-year weights it surfaces at +4.4 S$M (≈5% of the change). Both variants ship in the table so the choice of midpoints is auditable, not an assumption to take on faith.
- **Not a forecast.** Variants re-describe the same history; none of them projects. A re-pull can move the two newest quarters (write-off registrations can be restated upward briefly).
