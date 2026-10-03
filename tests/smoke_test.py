"""Smoke tests for the committed artifacts — stdlib only, no network.

Run (repo root):  python tests/smoke_test.py
In CI:            same command, on every push + PR (.github/workflows/ci.yml)

These do NOT re-run the pipeline (CI does that separately, on the vendored raw
files). They check that the committed outputs, figures and workbook are present,
parse, and keep their shape — plus the receipts that matter:

  * the vendored raw files still hash to the SHA-256 values in pull_manifest.json
  * this pull's headline numbers are LOCKED (96.5 = 63.9 + 32.6; the 4-quarter
    default 543.4 is asserted by build_workbook.py itself) — a fresh pull updates
    these constants alongside the committed data.

Regeneration keeps these green: required-column SUBSETS only, figures = existence
+ size floor.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BRIDGE_CSV = ROOT / "outputs" / "yearly_bridge.csv"
SENS_CSV = ROOT / "outputs" / "sensitivity.csv"
BOOK_CSV = ROOT / "outputs" / "book_split.csv"
WORKBOOK = ROOT / "outputs" / "quick_check.xlsx"
MANIFEST = ROOT / "data" / "raw" / "pull_manifest.json"

BRIDGE_REQUIRED_COLS = {
    "year", "previous_year", "write_offs_sgd_m", "avg_rollover_sgd_m", "rate_pct",
    "delta_write_offs_sgd_m", "volume_sgd_m", "rate_sgd_m", "interaction_sgd_m",
}
SENS_REQUIRED_COLS = {
    "variant", "window_old", "window_new", "delta_sgd_m", "volume_sgd_m",
    "rate_sgd_m", "joint_sgd_m", "residual_sgd_m",
}
BOOK_REQUIRED_COLS = {
    "year", "previous_year", "avg_principal_cards", "avg_supplementary_cards", "avg_total_cards",
    "rollover_per_card_sgd", "write_offs_per_principal_card_sgd", "rollover_to_billings",
    "delta_rollover_sgd_m", "cards_effect_sgd_m", "balance_per_card_effect_sgd_m",
}
EXPECTED_FIGURES = [
    "f1_timeline.png", "f1_timeline-dark.png",
    "f2_bridge.png", "f2_bridge-dark.png",
    "f3_contributions.png", "f3_contributions-dark.png",
    "f4_book.png", "f4_book-dark.png",
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
    # LOCKED for the committed 2026-10-03 pull (update alongside a fresh pull):
    row25 = next(r for r in rows if r["year"] == "2025")
    assert abs(float(row25["delta_write_offs_sgd_m"]) - 96.5) < 0.01, "2025 Δ moved — update the lock with the new pull"
    assert abs(float(row25["volume_sgd_m"]) - 63.9) < 0.01
    assert abs(float(row25["rate_sgd_m"]) - 32.6) < 0.01


def test_sensitivity_csv() -> None:
    rows = _load_csv(SENS_CSV)
    assert rows, f"{SENS_CSV.name} has no data rows"
    missing = SENS_REQUIRED_COLS - set(rows[0].keys())
    assert not missing, f"{SENS_CSV.name} missing columns: {sorted(missing)}"
    assert len(rows) >= 6, f"only {len(rows)} variant row(s) — expected 6"
    assert rows[0]["variant"].startswith("annual "), "base variant should be first"
    for r in rows:
        for col in ("delta_sgd_m", "volume_sgd_m", "rate_sgd_m", "residual_sgd_m"):
            float(r[col])
        if r["joint_sgd_m"]:  # blank only where the term is undefined (published basis)
            float(r["joint_sgd_m"])
    pub = next(r for r in rows if r["variant"].startswith("published"))
    assert pub["joint_sgd_m"] == "" and float(pub["residual_sgd_m"]) < 0, "the published-basis gap is a residual, not a joint term"


def test_book_split_csv() -> None:
    rows = _load_csv(BOOK_CSV)
    assert rows, f"{BOOK_CSV.name} has no data rows"
    missing = BOOK_REQUIRED_COLS - set(rows[0].keys())
    assert not missing, f"{BOOK_CSV.name} missing columns: {sorted(missing)}"
    assert len(rows) >= 10
    r25 = next(r for r in rows if r["year"] == "2025")
    # the split closes: cards effect + per-card effect == Δrollover
    assert abs(float(r25["cards_effect_sgd_m"]) + float(r25["balance_per_card_effect_sgd_m"])
               - float(r25["delta_rollover_sgd_m"])) < 0.01
    assert float(r25["cards_effect_sgd_m"]) < 0 < float(r25["balance_per_card_effect_sgd_m"]), "2025: cards down, per-card up"


def test_figures_present() -> None:
    for sub in ("reports/figures", "docs/img"):
        fig_dir = ROOT.joinpath(*sub.split("/"))
        missing = [n for n in EXPECTED_FIGURES if not (fig_dir / n).is_file()]
        assert not missing, f"{sub} missing figures: {missing}"
    small = [n for n in EXPECTED_FIGURES if (ROOT / "reports" / "figures" / n).stat().st_size < MIN_FIGURE_BYTES]
    assert not small, f"suspiciously small figures: {small}"


def test_workbook_present() -> None:
    assert WORKBOOK.is_file(), f"{WORKBOOK.name} missing"
    data = WORKBOOK.read_bytes()
    assert len(data) > MIN_WORKBOOK_BYTES, f"workbook suspiciously small ({len(data)} bytes)"
    assert data[:2] == b"PK", "workbook is not a zip/xlsx"


def test_raw_files_match_manifest() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for fname, info in m["files"].items():
        p = ROOT / "data" / "raw" / fname
        assert p.is_file(), f"missing vendored raw file: {fname}"
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        assert got == info["sha256"], f"{fname}: sha256 {got[:12]}… != manifest {info['sha256'][:12]}…"


def test_banner_assets_present() -> None:
    for name in ("banner.svg", "banner-dark.svg"):
        p = ROOT / "assets" / name
        assert p.is_file(), f"missing asset: {name}"
        assert p.stat().st_size > 500, f"{name} suspiciously small"


def main() -> int:
    checks = [test_bridge_csv, test_sensitivity_csv, test_book_split_csv, test_figures_present,
              test_workbook_present, test_raw_files_match_manifest, test_banner_assets_present]
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
