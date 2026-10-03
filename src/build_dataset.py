"""Build the processed dataset: raw wide CSV -> staging (sql/01) -> checks (sql/03) -> parquet.

Run (repo root): python src/build_dataset.py
Receipts printed: in/out cell counts, exclusion breakdown, check results. Exit 1 if any check fails.

Order matters: every check runs BEFORE the parquet is produced, and the file is written
to a temp path then atomically replaced — a failing run never touches the existing output.
Paths are absolute (the staging SQL's raw path is substituted below), so the script works
from any working directory.
"""
import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / "sql/01_staging.sql"
CHECKS = ROOT / "sql/03_checks.sql"
OUT_DIR = ROOT / "data/processed"
RAW = (ROOT / "data/raw/credit-charge-cards-quarterly.csv").as_posix()

# Exclusion rules — must mirror the WHERE clause in sql/01. A cell is excluded if ANY rule matches.
SERIES_LIST = ("'Principal Cardholders', 'Supplementary Cardholders', 'Total Card Billings', "
               "'Rollover Balance', 'Bad Debts Written Off', 'Charge-Off Rates'")
RULES = [
    ("quarter label unparseable", "NOT regexp_matches(q_label, '^[0-9]{4}[1-4]Q$')"),
    ("value not numeric", "TRY_CAST(value AS DOUBLE) IS NULL"),
    ("unexpected series", f"DataSeries NOT IN ({SERIES_LIST})"),
]
ANY_RULE = "(" + " OR ".join(expr for _, expr in RULES) + ")"

UNPIVOT = (f"UNPIVOT (SELECT * FROM read_csv_auto('{RAW}')) "
           "ON COLUMNS(* EXCLUDE (DataSeries)) INTO NAME q_label VALUE value")


def q(con, sql):
    return con.sql(sql).fetchall()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    raw_cells = q(con, f"SELECT count(*) FROM ({UNPIVOT})")[0][0]
    con.execute("CREATE OR REPLACE VIEW raw_long AS " + UNPIVOT)
    # The staging SQL references the raw file by a repo-relative path; substitute the
    # absolute path so no step depends on the process working directory.
    staging_sql = STAGING.read_text(encoding="utf-8").replace("data/raw/credit-charge-cards-quarterly.csv", RAW)
    con.execute(staging_sql)

    quarters = q(con, "SELECT count(*) FROM quarterly")[0][0]
    staged_cells = q(con, """SELECT count(principal_cardholders) + count(supplementary_cardholders)
                                  + count(billings_sgd_m) + count(rollover_sgd_m)
                                  + count(write_offs_sgd_m) + count(charge_off_rate_pct)
                             FROM quarterly""")[0][0]
    excl_any = q(con, f"SELECT count(*) FROM raw_long WHERE {ANY_RULE}")[0][0]
    print(f"raw cells:    {raw_cells}  (6 series × {raw_cells // 6} quarters)")
    print(f"staged:       {quarters} quarters · {staged_cells} cells")
    print(f"excluded:     {raw_cells - staged_cells}  ({100 * (raw_cells - staged_cells) / raw_cells:.3f}%)")
    print("exclusion rules (per-rule counts; a cell may match more than one):")
    for rule, expr in RULES:
        k = q(con, f"SELECT count(*) FROM raw_long WHERE {expr}")[0][0]
        print(f"    rule [{rule}]: {k}")
    ok_recon = (staged_cells + excl_any) == raw_cells
    print(f"    [{'PASS' if ok_recon else 'FAIL'}] retained + excluded == raw cells "
          f"({staged_cells} + {excl_any} vs {raw_cells})")

    print("checks:")
    failed = not ok_recon
    for name, v in con.execute(CHECKS.read_text(encoding="utf-8")).fetchall():
        status = "PASS" if v == 0 else "FAIL"
        print(f"    [{status}] {name}  (violations: {v})")
        if v:
            failed = True

    if failed:
        print("checks failed — parquet NOT written (existing file left untouched)")
        sys.exit(1)

    pq = OUT_DIR / "quarterly.parquet"
    tmp = OUT_DIR / "quarterly.parquet.tmp"
    con.sql(f"COPY quarterly TO '{tmp.as_posix()}' (FORMAT PARQUET)")
    os.replace(tmp, pq)
    print(f"wrote: {pq.as_posix()}  ({pq.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
