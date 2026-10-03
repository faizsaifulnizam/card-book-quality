# Sensitivity — the bridge across windows, bases and weights

Headline: **2025 vs 2024** — write-offs **+96.5 S$M = volume +63.9 + rate +32.6** (midpoint weights; the interaction is 0 by construction). Every variant below re-runs the same arithmetic on a different window, rate basis, or weighting. Machine-readable: [`outputs/sensitivity.csv`](../outputs/sensitivity.csv) · regenerate with `python src/analysis.py`. All money figures S$M.

| variant | window (new side) | Δ write-offs | volume | rate | interaction | what it tests |
|---|---|---|---|---|---|---|
| annual 2025 vs 2024 (base) | 2025 | +96.5 | +63.9 | +32.6 | 0 | the headline split |
| annual 2020 vs 2019 (peak year) | 2020 | +31.8 | −41.2 | +73.0 | 0 | the opposite shape — rate-led |
| trailing 4 quarters | 2025 Q3 – 2026 Q2 | +79.3 | +58.4 | +20.9 | 0 | freshest data (includes 2 quarters outside the annual table) |
| same two quarters, year apart | H1 2026 vs H1 2025 | +23.7 | +27.2 | −3.5 | 0 | seasonality-free short read |
| published annual-rate basis | 2025 | +96.5 | +63.6 | +33.4 | −0.46 | rates read off the published table instead of recomputed |
| base-weighted 3-term | 2025 | +96.5 | +61.7 | +30.4 | +4.4 | anchor-year weights; the joint term surfaced |

## How to read it

- **Direction is stable; the mix moves a little.** In every variant the change is positive, and volume outweighs rate — except 2020, where the book *shrank* and the rate alone drove the rise (volume −41.2, rate +73.0). The 2025/24 rise is not that shape: on the base split, volume is ~two-thirds; on the trailing window, ~three-quarters of the change; on the freshest half-vs-half read the change is volume-only (rate −3.5).
- **The two quarters not yet in any annual figure** (2026 H1) show the same direction — the trailing window uses them and the split barely moves (58.4 / 20.9).
- **Basis check:** reading rates straight off the published annual table (5.4% → 5.8%) instead of the recomputed values reproduces the split within ±0.5 S$M — the rounding in published rates lands in the small residual column, shown rather than hidden.
- **Weighting choice, made visible:** with midpoint weights the two terms are exact and the interaction closes to zero; with base-year weights the joint term is +4.4 S$M (≈5% of the change). Both variants are in the table so the choice of midpoints is auditable, not an assumption to take on faith.
- **Not a forecast.** Variants re-describe the same history; none of them projects. A re-pull can move the two newest quarters (registrations of write-offs can be restated upward briefly).
