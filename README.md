# card-book-quality

> **Did credit-card write-offs rise because the book grew — or because a larger share of it went bad?**

**Status:** scaffolded — question, data and approach are locked; analysis, figures and reproduce steps pending. Part of a six-repo series on Singapore's public data.

## The question

A credit-card book can write off more dollars for two different reasons: it got bigger (more billings and balances), or a larger share of it went bad (a higher charge-off rate). This repo bridges the year-on-year change in write-offs into those two components, using Singapore's system-wide card statistics — all issuers, not one bank.

## The data

- **Credit and charge cards, quarterly** — MAS, via [data.gov.sg](https://data.gov.sg/datasets/d_5c8e5801c2a64e2e6b16608296ef3e02/view). Fields: total card billings, rollover balance, bad debts written off, charge-off rate. Billings, rollover and write-offs are in S$ millions; charge-off rates are as published (annualised, per MAS's stated formula).
- Licence: Singapore Open Data Licence (© Monetary Authority of Singapore / Singapore Department of Statistics).
- The file is small; if the licence allows, the CSV is committed, otherwise a download script fetches it.

## Planned approach

- Table (and one chart) of the charge-off rate over time — the rate, not only dollars written off.
- Rate-vs-volume bridge: split the change in write-offs into a book-growth component and a rate component; state the formula.
- Rollover balance shown next to the rate; never conflate rollover with default.
- Compare the latest year against an earlier peak, so a one-year rise is not framed as a record.
- One-page memo: the answer, the comparison, and the limits — all issuers in Singapore, not one bank; broad data cannot name a product or time a default.

## Done when

The memo's number matches the CSV; units are stated; the repo never implies a single bank's portfolio; no forecast.

## Out of scope

A default model, customer-level data, and policy recommendations.

## Licence

Code: MIT. Data: Singapore Open Data Licence — © Monetary Authority of Singapore / SingStat, via data.gov.sg. This is an independent, unofficial analysis.

---

*Part of a six-repo series on Singapore's public data.* **The others:** [hdb-resale-mart](https://github.com/faizsaifulnizam/hdb-resale-mart) · [coe-quota-premium](https://github.com/faizsaifulnizam/coe-quota-premium) · [retail-sales-split](https://github.com/faizsaifulnizam/retail-sales-split) · [coe-category-break](https://github.com/faizsaifulnizam/coe-category-break) · [hdb-lease-slope](https://github.com/faizsaifulnizam/hdb-lease-slope)
