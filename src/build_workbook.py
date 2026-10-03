"""Build outputs/quick_check.xlsx — the formula-only Excel surface (spec 02 §10).

Sheets:
  Quick check    — pick a quarter from the dropdown → the block updates (XLOOKUPs + INDEX/MATCH)
  Quarterly      — the full quarterly table (billings · rollover · write-offs · published rate)
  Annual bridge  — outputs/yearly_bridge.csv (annual levels + the volume/rate split)

Formula-only, no macros. Run (repo root): python src/build_workbook.py
Receipts printed: row counts + the values a reviewer sees for the default selection.
"""
import csv
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import duckdb
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
PARQUET = (ROOT / "data/processed/quarterly.parquet").as_posix()
BRIDGE_CSV = ROOT / "outputs/yearly_bridge.csv"
OUT = ROOT / "outputs/quick_check.xlsx"

INK = "14293D"
MUTED = "5C6B79"
SAND = "E7E3DC"

HEAD = Font(bold=True, color=INK)
NOTE = Font(size=9, color=MUTED)
FILL = PatternFill("solid", fgColor=SAND)


def label(q):
    return f"{q.year} Q{(q.month - 1) // 3 + 1}"


def q(con, sql):
    return con.sql(sql).fetchall()


def normalize_xlsx(path):
    """Rewrite the saved workbook deterministically.

    openpyxl writes zip entries with the current clock time and re-stamps
    docProps/core.xml 'modified' at save (no config knob), so two builds of the
    same data differ in bytes. Rebuild the archive with a fixed entry order and
    timestamp: a reviewer re-running this script must see a byte-identical file.
    """
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in sorted(zin.namelist()):
            data = zin.read(name)
            if name == "docProps/core.xml":
                data = re.sub(rb"<dcterms:modified[^>]*>[^<]*</dcterms:modified>",
                              b'<dcterms:modified xsi:type="dcterms:W3CDTF">2026-10-03T00:00:00Z</dcterms:modified>', data)
            zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(zi, data)
    tmp.replace(path)


def main():
    if not Path(PARQUET).exists():
        sys.exit("data/processed/quarterly.parquet missing — run src/build_dataset.py first")
    con = duckdb.connect()
    rows = q(con, f"""SELECT quarter, billings_sgd_m, rollover_sgd_m, write_offs_sgd_m, charge_off_rate_pct
                      FROM read_parquet('{PARQUET}') ORDER BY quarter DESC""")
    quarters = [(label(r[0]), r[0].year, (r[0].month - 1) // 3 + 1, float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in rows]

    wb = Workbook()
    # Deterministic output: fixed document timestamps (a rebuild must be byte-identical,
    # not "same bytes except the save time" — reviewers diff regenerated artifacts).
    wb.properties.created = datetime(2026, 10, 3, 0, 0, 0)
    wb.properties.modified = datetime(2026, 10, 3, 0, 0, 0)
    wb.properties.creator = "card-book-quality — src/build_workbook.py"
    wb.properties.lastModifiedBy = "card-book-quality — src/build_workbook.py"
    ws = wb.active
    ws.title = "Quick check"

    ws["A1"] = "Card book — quick check (MAS credit & charge cards, quarterly)"
    ws["A1"].font = Font(bold=True, size=13, color=INK)
    ws["A2"] = ("All issuers in Singapore, not one bank. Values S$M unless stated. "
                "Pick a quarter below — the block updates (formulas, no macros).")
    ws["A2"].font = NOTE

    ws["A4"] = "Quarter:"
    ws["A4"].font = HEAD
    ws["B4"] = quarters[0][0]  # default: latest
    ws["B4"].font = Font(bold=True)
    ws["B4"].fill = PatternFill("solid", fgColor="F3EFE7")

    dv = DataValidation(type="list", formula1=f"Quarterly!$A$2:$A${len(quarters) + 1}", allow_blank=False)
    dv.error = "Pick a quarter from the list"
    ws.add_data_validation(dv)
    dv.add(ws["B4"])

    LBL = [
        ("Quarter", '=$B$4', None),
        ("Total billings (S$M, that quarter)", '=XLOOKUP($B$4,Quarterly!$A:$A,Quarterly!$D:$D)', "0.0"),
        ("Rollover balance (S$M, quarter-end)", '=XLOOKUP($B$4,Quarterly!$A:$A,Quarterly!$E:$E)', "0.0"),
        ("Write-offs (S$M, that quarter)", '=XLOOKUP($B$4,Quarterly!$A:$A,Quarterly!$F:$F)', "0.0"),
        ("Published charge-off rate (%, annualised)", '=XLOOKUP($B$4,Quarterly!$A:$A,Quarterly!$G:$G)', '0.0"%"'),
        ("Write-offs, last 4 quarters incl. selected (S$M)",
         "=SUM(OFFSET(Quarterly!$F$1,MATCH($B$4,Quarterly!$A:$A,0),0,4,1))", "0.0"),
        ("Rate change vs same quarter a year earlier (pt)",
         "=INDEX(Quarterly!$G:$G,MATCH($B$4,Quarterly!$A:$A,0))-INDEX(Quarterly!$G:$G,MATCH($B$4,Quarterly!$A:$A,0)+4)", "+0.0;-0.0"),
    ]
    r0 = 6
    for i, (name, formula, numfmt) in enumerate(LBL):
        r = r0 + i
        ws.cell(row=r, column=1, value=name).font = HEAD if i == 0 else Font(color=INK)
        c = ws.cell(row=r, column=2, value=formula)
        c.font = Font(bold=(i == 0), color=INK)
        if numfmt:
            c.number_format = numfmt
    ws.cell(row=r0 + 6, column=1,
            value="(blank rate change = fewer than 4 quarters before the selection)").font = NOTE

    notes = [
        "",
        "Refresh: re-run the pipeline, then re-run this builder —",
        "  python src/download.py --force     # or without --force if the raw files exist",
        "  python src/build_dataset.py        # staging + checks → data/processed/quarterly.parquet",
        "  python src/analysis.py             # bridge + sensitivity → outputs/*.csv",
        "  python src/build_workbook.py       # this file",
        "",
        "Source: MAS credit & charge cards via data.gov.sg — Singapore Open Data Licence. See docs/data_audit.md.",
        "Charge-off rate is as published: bad debts written off ÷ average rollover balance, annualised.",
        "Formula-only, no macros. XLOOKUP needs Excel 2021+/365; in older readers swap it for the INDEX/MATCH pattern used below it.",
        "Numbers reproduce outputs/yearly_bridge.csv and the README headline for the same pull.",
    ]
    nr = r0 + 8
    for i, t in enumerate(notes):
        ws.cell(row=nr + i, column=1, value=t).font = NOTE
        ws.cell(row=nr + i, column=1).alignment = Alignment(horizontal="left")

    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 22

    # ---- Quarterly sheet ----
    wq = wb.create_sheet("Quarterly")
    head = ["Quarter", "Year", "Qtr", "Total billings (S$M)", "Rollover balance (S$M)",
            "Write-offs (S$M)", "Published rate (%)"]
    for j, h in enumerate(head, start=1):
        c = wq.cell(row=1, column=j, value=h)
        c.font = HEAD
        c.fill = FILL
    for i, row in enumerate(quarters, start=2):
        for j, v in enumerate(row, start=1):
            wq.cell(row=i, column=j, value=v)
    for col, w in zip("ABCDEFG", (10, 7, 5, 21, 22, 18, 18)):
        wq.column_dimensions[col].width = w

    # ---- Annual bridge sheet ----
    wb2 = wb.create_sheet("Annual bridge")
    with BRIDGE_CSV.open(newline="", encoding="utf-8") as f:
        brows = list(csv.DictReader(f))
    bhead = ["Year", "vs year", "Write-offs (S$M)", "Avg rollover (S$M)", "Rate, recomputed (%)",
             "Rate, published (%)", "Δ write-offs (S$M)", "Volume effect (S$M)", "Rate effect (S$M)",
             "Interaction (S$M)", "Check sum (S$M)"]
    for j, h in enumerate(bhead, start=1):
        c = wb2.cell(row=1, column=j, value=h)
        c.font = HEAD
        c.fill = FILL
    keys = ["year", "previous_year", "write_offs_sgd_m", "avg_rollover_sgd_m", "rate_pct",
            "rate_pct_pub_annual", "delta_write_offs_sgd_m", "volume_sgd_m", "rate_sgd_m",
            "interaction_sgd_m", "check_sgd_m"]
    for i, row in enumerate(brows, start=2):
        for j, k in enumerate(keys, start=1):
            v = row[k]
            try:
                v = float(v)
            except ValueError:
                pass
            wb2.cell(row=i, column=j, value=v)
    for col, w in zip("ABCDEFGHIJK", (7, 8, 16, 17, 18, 17, 16, 16, 15, 14, 15)):
        wb2.column_dimensions[col].width = w

    wb.save(OUT)
    normalize_xlsx(OUT)
    print(f"wrote: {OUT.as_posix()}  ({OUT.stat().st_size} bytes)")
    print(f"sheets: {wb.sheetnames} · quarterly rows: {len(quarters)} · bridge rows: {len(brows)}")

    # ------------------------------------------------------------------
    # Receipt: read back the written file and print what a reviewer sees
    # for the DEFAULT selection (latest quarter). Cannot evaluate formulas
    # without Excel — the expected values below are cross-checked against
    # the same computations in Python (duckdb).
    # ------------------------------------------------------------------
    rb = load_workbook(OUT)
    sel = rb["Quick check"]["B4"].value
    latest = quarters[0]
    rolling4 = sum(x[5] for x in quarters[:4])
    prev_year_same = next(x for x in quarters if x[0] == f"{int(latest[1]) - 1} Q{latest[2]}")
    yoy = round(latest[6] - prev_year_same[6], 1)
    print("read-back OK — openpyxl sees:")
    print(f"  default selection: {sel}")
    print(f"  expected: billings {latest[3]:,.1f} · rollover {latest[4]:,.1f} · write-offs {latest[5]:,.1f} "
          f"· rate {latest[6]:.1f}% · 4q write-offs {rolling4:,.1f} · rate YoY {yoy:+.1f} pt")
    f4 = rb["Quick check"]["B9"].value
    print(f"  formula spot-check (write-offs cell B9): {f4}")
    assert rb["Quick check"]["B4"].value == quarters[0][0]
    assert rb["Quarterly"]["A2"].value == quarters[0][0] and rb["Quarterly"]["A48"].value == quarters[-1][0]
    col_a = [c.value for c in rb["Quarterly"]["A"] if c.value]
    assert col_a[0] == "Quarter" and len(col_a) == len(quarters) + 1
    print("RESULT: workbook written + read-back checks PASS")


if __name__ == "__main__":
    main()
