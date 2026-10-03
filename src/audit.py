"""Data audit for the raw MAS card files.

Profiles the two raw CSVs in data/raw/ (stdlib only — independent of DuckDB by
design), prints the profile receipts, and cross-checks the quarterly file against
the published annual file under an explicit dictionary:

  - FLOWS (Total Card Billings, Bad Debts Written Off) are yearly SUMS —
    the four quarters must add up to the annual figure (≤0.1, rounding).
  - STOCKS (Rollover Balance, cardholders) are YEAR-END values —
    the annual figure equals Q4, NOT the average the bridge uses.

Also prints the seasonal index and the flags carried into the write-up.
Output feeds docs/data_audit.md.

Run (any cwd):  python src/audit.py
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
Q_FILE = RAW / "credit-charge-cards-quarterly.csv"
A_FILE = RAW / "credit-charge-cards-annual.csv"
QCOL = re.compile(r"^(\d{4})([1-4])Q$")
SERIES = ["Principal Cardholders", "Supplementary Cardholders", "Total Card Billings",
          "Rollover Balance", "Bad Debts Written Off", "Charge-Off Rates"]


def load_wide(path):
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    body = {r[0]: r[1:] for r in rows[1:]}
    return header[1:], body


def main():
    qcols_raw, qdata = load_wide(Q_FILE)
    ycols, ydata = load_wide(A_FILE)

    def qidx(c):
        m = QCOL.match(c)
        return int(m.group(1)) * 4 + int(m.group(2))

    qs = sorted(qcols_raw, key=qidx)
    qmap = {s: dict(zip(qcols_raw, qdata[s])) for s in SERIES}  # series -> {quarter: raw string}
    print(f"== quarterly file: {len(qs)} quarters, {qs[0]} → {qs[-1]} ==")
    gaps = [b for a, b in zip(qs, qs[1:]) if qidx(b) - qidx(a) != 1]
    print(f"gaps: {gaps or 'none'} · series rows: {len(qdata)}")
    print("   (committed to the repo as a vendored copy: sha256 of the exact bytes lives in")
    print("    pull_manifest.json, so a stranger re-running gets the file this analysis used)")

    print("\nper-series ranges (quarterly):")
    for s in SERIES:
        vals = [float(v) for v in qdata[s]]
        print(f"  {s:<28} min {min(vals):>10,.1f}  max {max(vals):>10,.1f}  nulls {sum(1 for v in qdata[s] if not v.strip())}")

    def qvals(series, year):
        return [float(v) for c, v in qmap[series].items() if int(c[:4]) == year]

    print("\n== cross-check vs the published annual file — flows (yearly SUMS) ==")
    print(f"{'year':>5} {'ΔΣ write-offs':>14} {'ΔΣ billings':>12} {'rate%':>8} {'pub%':>6} {'Δrate':>7}")
    for ystr in sorted(ycols, key=int):
        y = int(ystr)
        if y < 2015:
            continue  # 2014 partial: no full calendar year in the quarterly file
        w = qvals("Bad Debts Written Off", y)
        r = qvals("Rollover Balance", y)
        b = qvals("Total Card Billings", y)
        if len(w) != 4:
            print(f"{y:>5} partial-year skip ({len(w)} quarters)")
            continue
        dw = sum(w) - float(ydata["Bad Debts Written Off"][ycols.index(ystr)])
        db = sum(b) - float(ydata["Total Card Billings"][ycols.index(ystr)])
        rate = sum(w) / (sum(r) / 4) * 100
        pub = float(ydata["Charge-Off Rates"][ycols.index(ystr)])
        print(f"{y:>5} {dw:>14.2f} {db:>12.2f} {rate:>8.2f} {pub:>6.1f} {rate - pub:>+7.2f}")
    print("   both flow gaps must stay within 0.1 (quarterly cells are published to 0.1);")
    print("   the rate is recomputed as Σ write-offs ÷ the AVERAGE of the four quarter-end balances.")

    print("\n== cross-check vs the published annual file — stocks (year-end = Q4) ==")
    print(f"{'year':>5} {'R Q4':>10} {'R avg-of-4':>11} {'cards Q4':>12} {'cards avg':>11}")
    for y in (2024, 2025):
        r_q4 = float(qmap["Rollover Balance"][f"{y}4Q"])
        r_avg = sum(qvals("Rollover Balance", y)) / 4
        p_q4 = float(qmap["Principal Cardholders"][f"{y}4Q"])
        p_avg = sum(qvals("Principal Cardholders", y)) / 4
        print(f"{y:>5} {r_q4:>10,.1f} {r_avg:>11,.1f} {p_q4:>12,.0f} {p_avg:>11,.0f}")
    print("   the annual file's 2025 rollover (9,400.2) is the year-end stock; the bridge's 8,920.3 is the")
    print("   average of the four quarter-ends — different quantities, both correct; never interchange them.")

    print("\n== headline numbers (recomputed from quarterly, full precision) ==")
    for y in (2019, 2020, 2024, 2025):
        w, r = qvals("Bad Debts Written Off", y), qvals("Rollover Balance", y)
        print(f"  {y}: write-offs Σ {sum(w):,.1f} S$M · avg rollover {sum(r)/4:,.1f} S$M · rate {sum(w)/(sum(r)/4)*100:.3f}%")

    print("\n== seasonality: published rate by quarter-of-year (complete years 2015–2025) ==")
    for qq in (1, 2, 3, 4):
        vs = [float(qmap["Charge-Off Rates"][c]) for c in qs if c.endswith(f"{qq}Q") and 2015 <= int(c[:4]) <= 2025]
        print(f"  Q{qq}: mean {sum(vs) / len(vs):.2f}%  ({len(vs)} years)")
    print("  typical range ≈0.3 pt — annual windows absorb THIS. 2024's within-year move (5.0 → 6.5) is not")
    print("  this pattern — it's a level shift plus a spike. The annual window is used because the rate")
    print("  changed LEVEL (2024 step-up), not because seasonality is large.")
    recent = [c for c in qs if qidx(c) >= qidx("20251Q")]
    print("  recent quarters: " + " · ".join(f"{c} {qmap['Charge-Off Rates'][c]}%" for c in recent))

    print("\n== flags carried into the write-up ==")
    pc = {c: float(qmap["Principal Cardholders"][c]) for c in qs}
    _mag, a, b = max((abs(pc[b] - pc[a]), a, b) for a, b in zip(qs, qs[1:]))
    print(f"  principal cardholders, largest one-quarter move in the file: {a} → {b}: "
          f"{pc[a]:,.0f} → {pc[b]:,.0f} ({pc[b] - pc[a]:+,.0f}, {(pc[b] / pc[a] - 1) * 100:+.1f}%) — "
          f"flagged, not explained by anything in this file")
    supp_year = {y: sum(qvals("Supplementary Cardholders", y)) / 4 for y in range(2015, 2026)}
    drops = sum(1 for y in range(2016, 2026) if supp_year[y] < supp_year[y - 1])
    print(f"  supplementary cards: {supp_year[2015]:,.0f} (2015 avg) → {supp_year[2025]:,.0f} (2025 avg), "
          f"{(supp_year[2025] / supp_year[2015] - 1) * 100:+.1f}% over the decade; down in {drops}/10 years since 2015")
    print("  'volume' caveat: balance growth can be slower repayment (stress) as well as expansion — "
          "write-offs lag stress; see the README Limits.")


if __name__ == "__main__":
    main()
