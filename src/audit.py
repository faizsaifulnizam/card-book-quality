"""Data audit for the raw MAS card files (B2).

Profiles the two raw CSVs in data/raw/ (stdlib only — independent of DuckDB by
design), prints the profile receipts, and cross-checks the quarterly file against
the published annual file. Output feeds docs/data_audit.md.

Run (repo root):  python src/audit.py
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
    qmap = {s: dict(zip(qcols_raw, qdata[s])) for s in SERIES}  # series -> {quarter: value}
    print(f"== quarterly file: {len(qs)} quarters, {qs[0]} → {qs[-1]} ==")
    gaps = [b for a, b in zip(qs, qs[1:]) if qidx(b) - qidx(a) != 1]
    print(f"gaps: {gaps or 'none'} · series rows: {len(qdata)}")

    print("\nper-series ranges (quarterly):")
    for s in SERIES:
        vals = [float(v) for v in qdata[s]]
        print(f"  {s:<28} min {min(vals):>10,.1f}  max {max(vals):>10,.1f}  nulls {sum(1 for v in qdata[s] if not v.strip())}")

    print("\n== cross-check: Σ quarterly vs published annual ==")
    def qvals(series, year):
        return [float(v) for c, v in qmap[series].items() if int(c[:4]) == year]
    print(f"{'year':>5} {'Δwriteoffs(0.1S$M)':>18} {'recalc_rate%':>12} {'pub_rate%':>10} {'Δrate':>7}")
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
        print(f"{y:>5} {dw:>18.2f} {rate:>12.2f} {pub:>10.1f} {rate - pub:>+7.2f}")

    print("\n== headline numbers (recomputed from quarterly, full precision) ==")
    for y in (2019, 2020, 2024, 2025):
        w, r = qvals("Bad Debts Written Off", y), qvals("Rollover Balance", y)
        print(f"  {y}: write-offs Σ {sum(w):,.1f} S$M · avg rollover {sum(r)/4:,.1f} S$M · rate {sum(w)/(sum(r)/4)*100:.3f}%")

    print("\n== seasonality: quarterly published rate, 2024–2026 ==")
    for c in qs:
        if int(c[:4]) >= 2024:
            print(f"  {c}: {qmap['Charge-Off Rates'][c]}%")


if __name__ == "__main__":
    main()
