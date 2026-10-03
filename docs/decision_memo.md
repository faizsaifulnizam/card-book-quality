# Decision memo — Singapore card write-offs, 2025 vs 2024

**The answer: mostly the book grew — but the rate moved too.** Write-offs rose **+96.5 S$M to 519.7 S$M** in 2025 (up from 423.2). Splitting the change with the arithmetic below: **+63.9 S$M (~two-thirds) from growth in the rollover balance** and **+32.6 S$M from the charge-off rate** rising (5.44% → 5.83% recomputed annual). This is **not a repeat of 2020**: at the 2020 peak the book *shrank* and the rate alone drove the rise (+31.8 = volume **−41.2** + rate **+73.0**).

**Scope.** All credit & charge-card issuers in Singapore, not one bank; quarterly aggregates (MAS via data.gov.sg), 2014 Q4 – 2026 Q2. Write-offs and balances are S$M per quarter; the charge-off rate is annualised — bad debts written off ÷ average rollover balance (the balance carried and charged interest).

**The arithmetic (stated, not implied):** write-offs = rate × average rollover balance in any period, so

```text
Δ write-offs = Δrollover × avg rate   (volume — the book grew)
             + Δrate × avg rollover   (rate — lending quality changed)
```

with midpoint averages, the two terms exhaust the change exactly (interaction ≡ 0 by construction; the base-weighted alternative shows a +4.4 S$M joint term — see [`sensitivity.md`](sensitivity.md)).

**Comparison, so one year is not framed as a record:** the 2020 rate peak (7.1% published) was a rate event on a shrinking book; 2025 is a balance-growth event with a smaller rate drift. Across the trailing-4-quarter window (+79.3 = volume +58.4 + rate +20.9) and the freshest two-quarter read (+23.7 = +27.2 − 3.5), the direction holds: volume-led.

**What a reader should NOT conclude.** This file cannot name a bank, a card product, or a borrower group; it cannot say *why* the rate moved (pricing, credit standards, relief unwinding — all out of scope); it cannot time defaults; and none of it is a forecast. Write-offs are an accounting flow — a quarter of timing decisions by issuers — not a distress clock. Numbers: [`../outputs/yearly_bridge.csv`](../outputs/yearly_bridge.csv); method: [`data_audit.md`](data_audit.md); robustness: [`sensitivity.md`](sensitivity.md).
