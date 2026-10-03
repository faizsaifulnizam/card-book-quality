# Decision memo — Singapore card write-offs

**Reader:** credit-risk analyst reviewing system-level trends. **Decision:** what to investigate next, not whether to change lending policy. **Fixed snapshot:** pulled 2026-10-03; quarterly coverage through 2026 Q2. All issuers in Singapore, not one bank.

## Finding

2025 quarterly write-offs sum to **S$519.7 million**, up **S$96.5 million** from 2024. The arithmetic split is **balance +63.9 / recomputed proxy ratio +32.6 S$M**. The larger ratio step happened in 2024 (+1.42 percentage points on the annual proxy), and the published rate has since sat at **5.9–6.0% for six quarters**, 2025 Q1–2026 Q2. H1 2026 vs H1 2025 is a same-season comparison: **+23.7 = +27.2 − 3.5**. The ratio term subtracts in that window; this is not a forecast of the next quarter.

Average reported total card count fell 0.4%, while aggregate rollover balance per reported card rose 15%. The balance split's card term is about **−32 S$M using total cards** but **+30 S$M using principal cards alone**; per-card terms dominate either basis. These are proxies, not deduplicated customers or balances among revolving borrowers. Principal counts fell 4.0% from 2025 Q2 to Q3, an unexplained break that affects both comparisons.

## Recommended next action

1. **Monitor balances alongside repayment and delinquency**, not write-offs alone. Obtain utilisation, revolving-account counts and borrower/vintage information before interpreting rising balances as stress or healthy expansion.
2. **Investigate the Q3 2025 principal-count break** with publisher or issuer definitions. Retain the unadjusted data and compare annual-average with year-end measures meanwhile; do not invent an adjustment.
3. **Seek issuer-level evidence before any lending-policy change.** This aggregate arithmetic identifies where the dollar change sits, not its cause or the institution responsible.

## What would change this reading

A source revision; a published ratio moving away from its observed 5.9–6.0% range; or repayment/delinquency evidence that distinguishes spending-led balances from slower repayment. Average quarter-end rollover divided by average quarterly billings rose **0.321 → 0.344** in 2024–2025. That stock-to-flow pattern **could indicate slower repayment and warrants investigation**, but is neither the share of spending unpaid nor proof of accumulating stress.

## Limits and evidence

The recomputed proxy ratio uses average **quarter-end** balances; close agreement with published annual rates does not establish identical denominators. Ratio changes may involve mix, accounting, write-off timing, recoveries or denominator movement, not only credit quality. No borrower-level, issuer, product, vintage or recovery attribution is available here. Midpoint closure is algebra, not independent evidence of a causal story.

[Annual bridge](../outputs/yearly_bridge.csv) · [Card/balance split](../outputs/book_split.csv) · [Window and denominator sensitivity](sensitivity.md) · [Data audit and source trail](data_audit.md).
