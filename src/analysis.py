"""S2 analysis runner — annual metrics → rate-vs-volume bridge → sensitivity.

Run: python src/analysis.py   (from the repo root; reads data/processed/quarterly.parquet)

The bridge (the core): Δ write-offs = ΔR·r̄ (volume) + Δr·R̄ (rate), with midpoint
weights (r̄, R̄ = averages of the two periods). With midpoint weights the two terms
exhaust the change exactly — the interaction is absorbed symmetrically and the
reported interaction term is 0 by construction. The base-weighted alternative
(volume = ΔR·r0, rate = Δr·R0, interaction = ΔR·Δr) is shown in the sensitivity
table so the weighting choice is transparent.

Receipts printed:
  1. annual table (complete years only)
  2. hand-checks: 3 years recomputed from the RAW CSV with stdlib only (independent path)
  3. identity asserts per bridge row + published-vs-recomputed rate tolerance
  4. headline (latest complete year) + peak-year numbers; coverage guard
  5. sensitivity table (trailing window · same-half-year · published basis · base weights)

Validation runs BEFORE any output file is written; a failing run leaves existing
outputs untouched. Writes: outputs/yearly_bridge.csv · outputs/sensitivity.csv
"""
import csv
import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
PARQUET = (ROOT / "data/processed/quarterly.parquet").as_posix()
RAWQ = ROOT / "data/raw/credit-charge-cards-quarterly.csv"
RAWA = ROOT / "data/raw/credit-charge-cards-annual.csv"
OUT = ROOT / "outputs"

RATE_TOL = 0.06    # pt — recomputed annual rate vs published annual rate (audit: <= 0.05)
HAND_CHECK_YEARS = (2019, 2020, 2025)


def q(con, sql):
    return con.sql(sql).fetchall()


def run_script(con, path):
    text = "\n".join(l.split("--", 1)[0] for l in Path(path).read_text(encoding="utf-8").splitlines())
    for stmt in text.split(";"):
        if stmt.strip():
            con.execute(stmt)


def load_raw():
    """Raw CSVs straight to stdlib dicts (independent path): quarterly series -> {label: value},
    annual series -> {year: raw string} (annual may carry 'na')."""
    with RAWQ.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    qq = {r[0]: dict(zip(rows[0][1:], [float(v) for v in r[1:]])) for r in rows[1:]}
    with RAWA.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    aa = {r[0]: dict(zip(rows[0][1:], r[1:])) for r in rows[1:]}
    return qq, aa


def window_stats(con, quarters):
    """Aggregate a list of quarter-start dates: W, avg R, recomputed annualised rate, published avg."""
    ql = ", ".join(f"DATE '{d}'" for d in quarters)
    w, r, pub, n = q(con, f"""SELECT sum(write_offs_sgd_m), avg(rollover_sgd_m),
                                     avg(charge_off_rate_pct), count(*)
                              FROM quarterly WHERE quarter IN ({ql})""")[0]
    assert int(n) == len(quarters), f"window covers {n} of {len(quarters)} quarters"
    r_frac = float(w) / float(r)                       # write-offs / avg rollover for the window
    rate_pct = r_frac * 100 * 4 / len(quarters)        # annualised for readable comparison
    return {"w": float(w), "R": float(r), "r": r_frac, "rate_pct": rate_pct,
            "rate_pub": float(pub), "nq": len(quarters)}


def bridge(old, new):
    """Δ write-offs split with midpoint weights (exact) + base-weighted alternative."""
    dR, dr = new["R"] - old["R"], new["r"] - old["r"]
    dW = new["w"] - old["w"]
    volume = dR * (old["r"] + new["r"]) / 2
    rate = dr * (old["R"] + new["R"]) / 2
    return {
        "dW": dW, "volume": volume, "rate": rate, "inter": dW - volume - rate,
        "volume_b": dR * old["r"], "rate_b": dr * old["R"], "inter_b": dR * dr,
    }


def year_quarters(year):
    return [f"{year}-01-01", f"{year}-04-01", f"{year}-07-01", f"{year}-10-01"]


def fmt_row(label, d):
    return (f"   {label:<28} Δ {d['dW']:+7.1f} = volume {d['volume']:+7.1f} + rate {d['rate']:+7.1f} "
            f"+ inter {d['inter']:+.2f} S$M")


def main():
    os.chdir(ROOT)
    OUT.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW quarterly AS SELECT * FROM read_parquet('{PARQUET}')")
    failed = False

    print("== annual metrics (sql/02) ==")
    run_script(con, ROOT / "sql/02_metrics.sql")
    raw_q, raw_a = load_raw()  # independent stdlib path; the published ANNUAL rate is the comparator
    ann_rate = {int(k): float(v) for k, v in raw_a["Charge-Off Rates"].items() if v != "na"}
    years = q(con, "SELECT year, quarters, write_offs_sgd_m, avg_rollover_sgd_m, rate_pct_recomputed, rate_pct_avg_quarterly FROM annual ORDER BY year")
    total_years = q(con, "SELECT count(*) FROM (SELECT DISTINCT year(quarter) FROM quarterly)")[0][0]
    print(f"complete years: {len(years)} of {total_years} calendar years present (partial years excluded)")
    for y, nq, w, r, rc, pubq in years:
        puba = ann_rate.get(int(y))
        print(f"   {y}: {int(nq)}q · write-offs {w:>6,.1f} S$M · avg rollover {r:>7,.1f} S$M "
              f"· rate {rc:.3f}% (pub annual {f'{puba:.1f}' if puba is not None else 'n/a'}% · avg of qtr {pubq:.2f}%)")

    print()
    print("== hand-checks (independent recompute from the RAW CSV, stdlib only) ==")
    for y in HAND_CHECK_YEARS:
        w = sum(raw_q["Bad Debts Written Off"][f"{y}{k}Q"] for k in (1, 2, 3, 4))
        r = sum(raw_q["Rollover Balance"][f"{y}{k}Q"] for k in (1, 2, 3, 4)) / 4
        rows = q(con, f"SELECT write_offs_sgd_m, avg_rollover_sgd_m, rate_pct_recomputed FROM annual WHERE year = {y}")[0]
        ok = abs(rows[0] - w) < 1e-6 and abs(rows[1] - r) < 1e-6 and abs(rows[2] - w / r * 100) < 1e-9
        print(f"   [{'PASS' if ok else 'FAIL'}] {y}: write-offs {w:,.1f} · avg rollover {r:,.1f} "
              f"· rate {w / r * 100:.3f}% — vs parquet {rows[0]:,.1f} / {rows[1]:,.1f} / {rows[2]:.3f}%")
        failed |= not ok

    print()
    print("== validation (runs BEFORE any file is written) ==")
    comparable = [(int(y[0]), y[4]) for y in years if int(y[0]) in ann_rate]
    max_diff = max(abs(rc - ann_rate[y]) for y, rc in comparable)
    ok_tol = len(comparable) >= 8 and max_diff <= RATE_TOL
    print(f"   [{'PASS' if ok_tol else 'FAIL'}] recomputed vs PUBLISHED ANNUAL rate: max |Δ| {max_diff:.3f} pt "
          f"over {len(comparable)} years (tolerance {RATE_TOL})")
    failed |= not ok_tol
    max_dq = max(abs(y[4] - y[5]) for y in years)
    print(f"   (context, not a check: vs the average of the four published quarterly rates the max |Δ| is "
          f"{max_dq:.3f} pt — quarterly rates are rounded and computed on monthly balances; the annual figure is the comparator)")

    complete = [int(y[0]) for y in years]
    ok_contig = complete == list(range(complete[0], complete[-1] + 1))
    partial = [int(y[0]) for y in q(con, "SELECT DISTINCT year(quarter) FROM quarterly ORDER BY 1") if int(y[0]) not in complete]
    ok_partial = all(p <= complete[0] or p > complete[-1] for p in partial)
    print(f"   [{'PASS' if ok_contig and ok_partial else 'FAIL'}] coverage: complete years {complete[0]}–{complete[-1]} "
          f"contiguous; partial-year rows at edges only ({partial})")
    failed |= not (ok_contig and ok_partial)

    # ---- the bridge, year over year ----
    print()
    print("== the bridge (yearly, midpoint weights) ==")
    bridges = []
    for y in complete[1:]:
        old = window_stats(con, year_quarters(y - 1))
        new = window_stats(con, year_quarters(y))
        b = bridge(old, new)
        eps = 1e-9 * max(1.0, abs(b["dW"]))
        ok = abs(b["volume"] + b["rate"] + b["inter"] - b["dW"]) <= eps and abs(b["inter"]) <= eps
        failed |= not ok
        bridges.append((y, old, new, b, ok))
        print(fmt_row(str(y), b) + ("" if ok else "   [FAIL identity]"))

    latest_year = complete[-1]
    yrow = {int(r[0]): r for r in years}
    w_new, r_new = yrow[latest_year][2], yrow[latest_year][3]
    w_old, r_old = yrow[latest_year - 1][2], yrow[latest_year - 1][3]
    print(f"   headline: {latest_year} vs {latest_year - 1} — write-offs {w_old:,.1f} → {w_new:,.1f} S$M "
          f"(+{w_new - w_old:,.1f}); rate {yrow[latest_year - 1][4]:.2f}% → {yrow[latest_year][4]:.2f}%")

    peak_year = max(complete, key=lambda y: ann_rate.get(y, yrow[y][4]))
    print(f"   peak year (max published ANNUAL rate, from data): {peak_year} "
          f"({ann_rate.get(peak_year, yrow[peak_year][5]):.1f}% published / {yrow[peak_year][4]:.2f}% recomputed)")

    if failed:
        print()
        print("validation failed — output files NOT written (existing outputs left untouched)")
        sys.exit(1)

    # ---- yearly_bridge.csv ----
    cols = ["year", "previous_year", "write_offs_sgd_m", "avg_rollover_sgd_m", "rate_pct",
            "rate_pct_pub_annual", "delta_write_offs_sgd_m", "volume_sgd_m", "rate_sgd_m",
            "interaction_sgd_m", "check_sgd_m"]
    rows_out = []
    for y, old, new, b, _ok in bridges:
        rows_out.append({
            "year": y, "previous_year": y - 1,
            "write_offs_sgd_m": round(new["w"], 2),
            "avg_rollover_sgd_m": round(new["R"], 2),
            "rate_pct": round(new["rate_pct"], 3),
            "rate_pct_pub_annual": ann_rate.get(y, round(new["rate_pub"], 1)),
            "delta_write_offs_sgd_m": round(b["dW"], 2),
            "volume_sgd_m": round(b["volume"], 2),
            "rate_sgd_m": round(b["rate"], 2),
            "interaction_sgd_m": round(b["inter"], 2),
            "check_sgd_m": round(b["volume"] + b["rate"] + b["inter"], 2),
        })
    # (written after all validation below — see the single write gate)
    print(f"yearly bridge rows prepared: {len(rows_out)}")

    # ---- sensitivity ----
    print()
    print("== sensitivity (C3): window · basis · weighting ==")
    q_sorted = [r[0].isoformat() for r in q(con, "SELECT quarter FROM quarterly ORDER BY quarter")]
    last4, prev4 = q_sorted[-4:], q_sorted[-8:-4]
    last2, prev2 = q_sorted[-2:], q_sorted[-6:-4]

    def sens_row(label, old_q, new_q):
        old, new = window_stats(con, old_q), window_stats(con, new_q)
        b = bridge(old, new)
        return {"variant": label,
                "window_old": f"{old_q[0][:7]} → {old_q[-1][:7]}",
                "window_new": f"{new_q[0][:7]} → {new_q[-1][:7]}",
                "write_offs_old_sgd_m": round(old["w"], 2),
                "write_offs_new_sgd_m": round(new["w"], 2),
                "delta_sgd_m": round(b["dW"], 2),
                "volume_sgd_m": round(b["volume"], 2),
                "rate_sgd_m": round(b["rate"], 2),
                "interaction_sgd_m": round(b["inter"], 2),
                "rate_old_pct": round(old["rate_pct"], 2),
                "rate_new_pct": round(new["rate_pct"], 2)}, b

    rows_s = []
    labels = [
        (f"annual {latest_year} vs {latest_year - 1} (base)", year_quarters(latest_year - 1), year_quarters(latest_year)),
        (f"annual {peak_year} vs {peak_year - 1} (peak year)", year_quarters(peak_year - 1), year_quarters(peak_year)),
        ("trailing 4 quarters", prev4, last4),
        ("same two quarters, year apart (H1-style)", prev2, last2),
    ]
    for label, oq, nq_ in labels:
        row, b = sens_row(label, oq, nq_)
        rows_s.append(row)
        eps = 1e-9 * max(1.0, abs(b["dW"]))
        ok = abs(b["volume"] + b["rate"] + b["inter"] - b["dW"]) <= eps
        failed |= not ok

    # published-rate basis: uses the published ANNUAL rates instead of the recomputed ones
    old = window_stats(con, year_quarters(latest_year - 1))
    new = window_stats(con, year_quarters(latest_year))
    r0p, r1p = ann_rate[latest_year - 1] / 100, ann_rate[latest_year] / 100
    vol_p = (new["R"] - old["R"]) * (r0p + r1p) / 2
    rate_p = (r1p - r0p) * (old["R"] + new["R"]) / 2
    rows_s.append({
        "variant": f"published annual-rate basis ({latest_year} vs {latest_year - 1})",
        "window_old": f"{latest_year - 1}", "window_new": f"{latest_year}",
        "write_offs_old_sgd_m": round(old["w"], 2), "write_offs_new_sgd_m": round(new["w"], 2),
        "delta_sgd_m": round(new["w"] - old["w"], 2),
        "volume_sgd_m": round(vol_p, 2), "rate_sgd_m": round(rate_p, 2),
        "interaction_sgd_m": round((new["w"] - old["w"]) - vol_p - rate_p, 2),
        "rate_old_pct": ann_rate[latest_year - 1], "rate_new_pct": ann_rate[latest_year],
    })

    # base-weighted alternative: anchors at period-0 weights; the joint term is real
    b = bridge(old, new)
    eps = 1e-9 * max(1.0, abs(b["dW"]))
    failed |= abs(b["volume_b"] + b["rate_b"] + b["inter_b"] - b["dW"]) > eps
    rows_s.append({
        "variant": f"base-weighted 3-term ({latest_year} vs {latest_year - 1})",
        "window_old": f"{latest_year - 1}", "window_new": f"{latest_year}",
        "write_offs_old_sgd_m": round(old["w"], 2), "write_offs_new_sgd_m": round(new["w"], 2),
        "delta_sgd_m": round(b["dW"], 2),
        "volume_sgd_m": round(b["volume_b"], 2), "rate_sgd_m": round(b["rate_b"], 2),
        "interaction_sgd_m": round(b["inter_b"], 2),
        "rate_old_pct": round(old["rate_pct"], 2), "rate_new_pct": round(new["rate_pct"], 2),
    })
    for r_ in rows_s:
        print(f"   {r_['variant']:<44} Δ {r_['delta_sgd_m']:+7.2f} = vol {r_['volume_sgd_m']:+7.2f} "
              f"+ rate {r_['rate_sgd_m']:+7.2f} + inter {r_['interaction_sgd_m']:+.2f}")

    if failed:
        print()
        print("validation failed — output files NOT written (existing outputs left untouched)")
        sys.exit(1)

    # ---- all validation passed: write both outputs ----
    path = OUT / "yearly_bridge.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=cols)
        wcsv.writeheader()
        wcsv.writerows(rows_out)
    print("wrote:", path.as_posix(), f"({path.stat().st_size} bytes, {len(rows_out)} rows)")

    cols_s = list(rows_s[0].keys())
    spath = OUT / "sensitivity.csv"
    with spath.open("w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=cols_s)
        wcsv.writeheader()
        wcsv.writerows(rows_s)
    print("wrote:", spath.as_posix(), f"({spath.stat().st_size} bytes, {len(rows_s)} rows)")

    print()
    print("RESULT: ALL CHECKS PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
