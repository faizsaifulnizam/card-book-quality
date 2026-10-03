"""Smoke tests for the committed artifacts — stdlib only, no network.

Run (repo root):  python tests/smoke_test.py
In CI:            same command, on every push + PR (.github/workflows/ci.yml)

These do NOT re-run the pipeline (that needs the raw download); they check the
repo's committed outputs, figures and workbook are present, parse, and keep
their expected shape. Regenerating the outputs should still keep these green:
required-column SUBSETS only, no headline numbers, figures = existence + size floor.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BRIDGE_CSV = ROOT / "outputs" / "yearly_bridge.csv"
SENS_CSV = ROOT / "outputs" / "sensitivity.csv"
WORKBOOK = ROOT / "outputs" / "quick_check.xlsx"

BRIDGE_REQUIRED_COLS = {
    "year", "previous_year", "write_offs_sgd_m", "avg_rollover_sgd_m", "rate_pct",
    "delta_write_offs_sgd_m", "volume_sgd_m", "rate_sgd_m", "interaction_sgd_m",
}
SENS_REQUIRED_COLS = {
    "variant", "window_old", "window_new", "delta_sgd_m", "volume_sgd_m",
    "rate_sgd_m", "interaction_sgd_m",
}
EXPECTED_FIGURES = [
    "f1_timeline.png", "f1_timeline-dark.png",
    "f2_bridge.png", "f2_bridge-dark.png",
]

MIN_FIGURE_BYTES = 5000
MIN_WORKBOOK_BYTES = 5000


def _load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_bridge_csv() -> None:
    rows = _load_csv(BRIDGE_CSV)
    assert rows, f"{BRIDGE_CSV.name} has no data rows"
    missing = BRIDGE_REQUIRED_COLS - set(rows[0].keys())
    assert not missing, f"{BRIDGE_CSV.name} missing columns: {sorted(missing)}"
    assert len(rows) >= 9, f"only {len(rows)} year rows — expected the full set"
    for r in rows:
        for col in ("write_offs_sgd_m", "avg_rollover_sgd_m", "rate_pct",
                    "volume_sgd_m", "rate_sgd_m", "interaction_sgd_m"):
            float(r[col])
        assert 0 < float(r["rate_pct"]) < 50
        assert float(r["write_offs_sgd_m"]) > 0 and float(r["avg_rollover_sgd_m"]) > 0


def test_sensitivity_csv() -> None:
    rows = _load_csv(SENS_CSV)
    assert rows, f"{SENS_CSV.name} has no data rows"
    missing = SENS_REQUIRED_COLS - set(rows[0].keys())
    assert not missing, f"{SENS_CSV.name} missing columns: {sorted(missing)}"
    assert len(rows) >= 5, f"only {len(rows)} variant row(s) — expected 6"
    assert rows[0]["variant"].startswith("annual "), "base variant should be first"
    for r in rows:
        float(r["delta_sgd_m"])
        float(r["volume_sgd_m"])
        float(r["rate_sgd_m"])
        float(r["interaction_sgd_m"])


def test_figures_present() -> None:
    fig_dir = ROOT / "reports" / "figures"
    missing = [n for n in EXPECTED_FIGURES if not (fig_dir / n).is_file()]
    assert not missing, f"missing figures: {missing}"
    small = [n for n in EXPECTED_FIGURES if (fig_dir / n).stat().st_size < MIN_FIGURE_BYTES]
    assert not small, f"suspiciously small figures: {small}"


def test_workbook_present() -> None:
    assert WORKBOOK.is_file(), f"{WORKBOOK.name} missing"
    data = WORKBOOK.read_bytes()
    assert len(data) > MIN_WORKBOOK_BYTES, f"workbook suspiciously small ({len(data)} bytes)"
    assert data[:2] == b"PK", "workbook is not a zip/xlsx"


def test_banner_assets_present() -> None:
    for name in ("banner.svg", "banner-dark.svg"):
        p = ROOT / "assets" / name
        assert p.is_file(), f"missing asset: {name}"
        assert p.stat().st_size > 500, f"{name} suspiciously small"


def main() -> int:
    checks = [test_bridge_csv, test_sensitivity_csv, test_figures_present,
              test_workbook_present, test_banner_assets_present]
    failed = 0
    for fn in checks:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001 — report, don't crash the runner
            failed += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    print(f"{len(checks) - failed}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
