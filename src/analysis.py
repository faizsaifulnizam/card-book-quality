"""Analysis runner — annual metrics → rate-vs-volume bridge → book (per-card) split → sensitivity.

Run: python src/analysis.py   (from anywhere; reads data/processed/quarterly.parquet)

The bridge (the core): Δ write-offs = ΔR·r̄ (volume) + Δr·R̄ (rate), with midpoint
weights (r̄, R̄ = averages of the two periods). Midpoint weights make the two terms
exhaust the change exactly — that is ALGEBRAIC CLOSURE, not an empirical finding:
the interaction is split symmetrically and reports as 0 by construction. The
base-weighted alternative (volume = ΔR·r0, rate = Δr·R0, interaction = ΔR·Δr)
surfaces the joint term (+4.4 S$M) in the sensitivity table. The empirical
receipts live elsewhere: the raw-CSV recompute, the published-rate
reconciliation, and the flow/stock reconciliation against the published annual file.

Receipts printed:
  1. annual table (complete years only)
  2. hand-checks: EVERY complete year recomputed from the RAW CSV with stdlib only
  3. closure asserts per bridge row + published-vs-recomputed rate tolerance (0.05 pt)
  4. flow/stock reconciliation: flows (Σ quarters) vs annual ≤ 0.1; stocks == Q4 exactly
  5. headline + rate path + book split (Δrollover = cards effect + balance-per-card effect)
  6. sensitivity (window · basis · weighting; joint term and rounding residual kept apart)

Validation runs BEFORE any output file is written; a failing run leaves existing
outputs untouched. Writes: outputs/yearly_bridge.csv · outputs/book_split.csv · outputs/sensitivity.csv
"""
import csv
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
PARQUET = (ROOT / "data/processed/quarterly.parquet").as_posix()
RAWQ = ROOT / "data/raw/credit-charge-cards-quarterly.csv"
RAWA = ROOT / "data/raw/credit-charge-cards-annual.csv"
OUT = ROOT / "outputs"

RATE_TOL = 0.05    # pt — recomputed annual rate vs published annual rate (max observed 0.049)


def q(con, sql):
    return con.sql(sql).fetchall()


def run_script(con, path):
    """Execute a .sql file as-is: DuckDB parses comments and multi-statement files
    natively — no comment stripping, no manual statement splitting."""
    con.execute(Path(path).read_text(encoding="utf-8"))


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
    OUT.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW quarterly AS SELECT * FROM read_parquet('{PARQUET}')")
    failed = False

    print("== annual metrics (sql/02) ==")
    run_script(con, ROOT / "sql/02_metrics.sql")
    raw_q, raw_a = load_raw()  # independent stdlib path; the published ANNUAL rate is the comparator
    ann_rate = {int(k): float(v) for k, v in raw_a["Charge-Off Rates"].items() if v != "na"}
    ann_num = {s: {int(k): float(v) for k, v in raw_a[s].items() if v != "na"}
               for s in ("Total Card Billings", "Bad Debts Written Off",
                         "Rollover Balance", "Principal Cardholders")}
    years = q(con, "SELECT year, quarters, write_offs_sgd_m, avg_rollover_sgd_m, rate_pct_recomputed, rate_pct_avg_quarterly FROM annual ORDER BY year")
    total_years = q(con, "SELECT count(*) FROM (SELECT DISTINCT year(quarter) FROM quarterly)")[0][0]
    print(f"complete years: {len(years)} of {total_years} calendar years present (partial years excluded)")
    for y, nq, w, r, rc, pubq in years:
        puba = ann_rate.get(int(y))
        print(f"   {y}: {int(nq)}q · write-offs {w:>6,.1f} S$M · avg rollover {r:>7,.1f} S$M "
              f"· rate {rc:.3f}% (pub annual {f'{puba:.1f}' if puba is not None else 'n/a'}% · avg of qtr {pubq:.2f}%)")

    print()
    print("== hand-checks (independent recompute from the RAW CSV, stdlib only; every complete year) ==")
    for y in [int(y_[0]) for y_ in years]:
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

    # flow/stock reconciliation vs the published annual file (rules in docs/data_audit.md):
    # flows (billings, write-offs) are yearly SUMS — Σ quarters must match within 0.1;
    # stocks (rollover, principal cardholders) are YEAR-END — must equal Q4 exactly.
    qsum = {int(r[0]): (float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in q(con, """
        SELECT year(quarter), sum(billings_sgd_m), sum(write_offs_sgd_m),
               max(CASE WHEN quarter = make_date(year(quarter), 10, 1) THEN rollover_sgd_m END),
               max(CASE WHEN quarter = make_date(year(quarter), 10, 1) THEN principal_cardholders END)
        FROM quarterly GROUP BY 1 HAVING count(*) = 4 ORDER BY 1""")}
    dflow, dstocks = 0.0, 0.0
    for y in complete:
        b_q, w_q, r_q4, p_q4 = qsum[y]
        dflow = max(dflow, abs(w_q - ann_num["Bad Debts Written Off"][y]),
                    abs(b_q - ann_num["Total Card Billings"][y]))
        dstocks = max(dstocks, abs(r_q4 - ann_num["Rollover Balance"][y]),
                      abs(p_q4 - ann_num["Principal Cardholders"][y]))
    ok_flow, ok_stock = round(dflow, 9) <= 0.1, dstocks == 0
    print(f"   [{'PASS' if ok_flow else 'FAIL'}] flows vs published annual: max |Δ| {dflow:.2f} S$M over {len(complete)} years "
          f"(write-offs + billings — quarterly sums vs annual; tolerance 0.1)")
    print(f"   [{'PASS' if ok_stock else 'FAIL'}] stocks == Q4 exactly: rollover & principal cardholders vs published annual "
          f"(max |Δ| {dstocks:.0f} — year-end values; the bridge's balance is the average of the four quarter-ends, not this)")
    failed |= not (ok_flow and ok_stock)

    # ---- the bridge, year over year (algebraic closure: volume + rate ≡ Δ by construction) ----
    print()
    print("== the bridge (yearly, midpoint weights — closure, not an empirical finding) ==")
    bridges = []
    for y in complete[1:]:
        old = window_stats(con, year_quarters(y - 1))
        new = window_stats(con, year_quarters(y))
        b = bridge(old, new)
        eps = 1e-9 * max(1.0, abs(b["dW"]))
        ok = abs(b["volume"] + b["rate"] + b["inter"] - b["dW"]) <= eps and abs(b["inter"]) <= eps
        failed |= not ok
        bridges.append((y, old, new, b, ok))
        print(fmt_row(str(y), b) + ("" if ok else "   [FAIL closure]"))

    latest_year = complete[-1]
    yrow = {int(r[0]): r for r in years}
    w_new, r_new = yrow[latest_year][2], yrow[latest_year][3]
    w_old, r_old = yrow[latest_year - 1][2], yrow[latest_year - 1][3]
    print(f"   headline: {latest_year} vs {latest_year - 1} — write-offs {w_old:,.1f} → {w_new:,.1f} S$M "
          f"(+{w_new - w_old:,.1f}); rate {yrow[latest_year - 1][4]:.2f}% → {yrow[latest_year][4]:.2f}%")
    step1 = yrow[latest_year - 1][4] - yrow[latest_year - 2][4]
    step2 = yrow[latest_year][4] - yrow[latest_year - 1][4]
    print(f"   rate path: {yrow[latest_year - 2][4]:.2f}% ({latest_year - 2}) → {yrow[latest_year - 1][4]:.2f}% "
          f"(+{step1:.2f} pt) → {yrow[latest_year][4]:.2f}% (+{step2:.2f} pt) — the step-up landed in {latest_year - 1}")

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

    # ---- the book, per card: Δrollover split into cards effect × balance-per-card effect ----
    print()
    print("== the book, per card (Δrollover = cards effect + balance-per-card effect; midpoint) ==")
    cards = {int(r[0]): r for r in q(con, """
        SELECT year(quarter) AS y, avg(principal_cardholders), avg(supplementary_cardholders),
               avg(rollover_sgd_m), avg(billings_sgd_m), sum(write_offs_sgd_m)
        FROM quarterly GROUP BY 1 HAVING count(*) = 4 ORDER BY 1""")}
    book_rows = []
    for y in complete[1:]:
        y0 = y - 1
        p0, s0, r_0, b_0 = (float(cards[y0][i]) for i in range(1, 5))
        p1, s1, r_1, b_1, w_1 = (float(cards[y][i]) for i in range(1, 6))
        c0, c1 = p0 + s0, p1 + s1
        pc0, pc1 = r_0 * 1e6 / c0, r_1 * 1e6 / c1
        d_r = r_1 - r_0
        cards_eff = (c1 - c0) * (pc0 + pc1) / 2 / 1e6
        bpc_eff = (pc1 - pc0) * (c0 + c1) / 2 / 1e6
        ok = abs(cards_eff + bpc_eff - d_r) <= 1e-6 * max(1.0, abs(d_r))
        failed |= not ok
        book_rows.append({
            "year": y, "previous_year": y0,
            "avg_principal_cards": int(round(p1)),
            "avg_supplementary_cards": int(round(s1)),
            "avg_total_cards": int(round(c1)),
            "rollover_per_card_sgd": int(round(pc1)),
            "write_offs_per_principal_card_sgd": int(round(w_1 * 1e6 / p1)),
            "rollover_to_billings": round(r_1 / b_1, 3),
            "delta_rollover_sgd_m": round(d_r, 2),
            "cards_effect_sgd_m": round(cards_eff, 2),
            "balance_per_card_effect_sgd_m": round(bpc_eff, 2)})
        print(f"   {y} vs {y0}: rollover {d_r:+8.1f} = cards {cards_eff:+7.1f} + balance/card {bpc_eff:+7.1f} S$M "
              f"· S${pc1:,.0f}/card · write-offs S${w_1 * 1e6 / p1:,.0f}/principal card "
              f"· rollover/billings {r_1 / b_1:.3f}" + ("" if ok else "  [FAIL closure]"))

    # ---- sensitivity ----
    print()
    print("== sensitivity: window · basis · weighting (joint term vs rounding residual kept apart) ==")
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
                "joint_sgd_m": round(b["inter"], 2),
                "residual_sgd_m": round(b["dW"] - b["volume"] - b["rate"] - b["inter"], 2),
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
        "joint_sgd_m": "",  # published rates don't define the joint term — the closure gap below is a residual
        "residual_sgd_m": round((new["w"] - old["w"]) - vol_p - rate_p, 2),
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
        "joint_sgd_m": round(b["inter_b"], 2),  # the true joint (interaction) term, surfaced by base weights
        "residual_sgd_m": round(b["dW"] - b["volume_b"] - b["rate_b"] - b["inter_b"], 2),
        "rate_old_pct": round(old["rate_pct"], 2), "rate_new_pct": round(new["rate_pct"], 2),
    })
    for r_ in rows_s:
        jt = r_["joint_sgd_m"]
        jt_s = f"{jt:+7.2f}" if isinstance(jt, (int, float)) else "     — "
        print(f"   {r_['variant']:<44} Δ {r_['delta_sgd_m']:+7.2f} = vol {r_['volume_sgd_m']:+7.2f} "
              f"+ rate {r_['rate_sgd_m']:+7.2f} + joint {jt_s} + resid {float(r_['residual_sgd_m']):+.2f}")

    if failed:
        print()
        print("validation failed — output files NOT written (existing outputs left untouched)")
        sys.exit(1)

    # ---- all validation passed: write the outputs (bridge · book split · sensitivity) ----
    path = OUT / "yearly_bridge.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=cols)
        wcsv.writeheader()
        wcsv.writerows(rows_out)
    print("wrote:", path.as_posix(), f"({path.stat().st_size} bytes, {len(rows_out)} rows)")

    bs = OUT / "book_split.csv"
    with bs.open("w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=list(book_rows[0].keys()))
        wcsv.writeheader()
        wcsv.writerows(book_rows)
    print("wrote:", bs.as_posix(), f"({bs.stat().st_size} bytes, {len(book_rows)} rows)")

    cols_s = ["variant", "window_old", "window_new", "write_offs_old_sgd_m", "write_offs_new_sgd_m",
              "delta_sgd_m", "volume_sgd_m", "rate_sgd_m", "joint_sgd_m", "residual_sgd_m",
              "rate_old_pct", "rate_new_pct"]
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
