"""Download the raw datasets from data.gov.sg into data/raw/.

Two official files (both MAS, via data.gov.sg):
  - credit-charge-cards-quarterly.csv  (primary — quarterly wide format: one row per series, one column per quarter)
  - credit-charge-cards-annual.csv     (cross-check — annual wide format)

Flow: initiate-download -> poll-download -> signed URL (v1 public API).
Run: python src/download.py [--force]   (skips if the files already exist)

Downloads land in .part files and are structurally validated BEFORE replacing any
existing CSV (validate-before-write; a failed pull leaves existing files untouched):
header shape, the six expected series present, per-row value counts, numeric values
(annual may carry 'na'), quarter contiguity, and a freshness floor (the latest quarter
within two quarters of today — a fixed floor goes stale silently). On success writes
data/raw/pull_manifest.json: sha256 is over the RAW FILE BYTES (so it matches
sha256sum), plus rows, coverage, series and the retrieval time.

The two CSVs + the manifest are committed to the repo as vendored copies (small files;
the Singapore Open Data Licence allows redistribution with attribution — given in the
README and data/raw/README.md). CI runs the pipeline on them without any network.
"""
import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.request as u
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
MANIFEST = RAW / "pull_manifest.json"

UA = "card-book-quality (https://github.com/faizsaifulnizam/card-book-quality; data.gov.sg pull script)"

SERIES = [
    "Principal Cardholders",
    "Supplementary Cardholders",
    "Total Card Billings",
    "Rollover Balance",
    "Bad Debts Written Off",
    "Charge-Off Rates",
]
QCOL = re.compile(r"^(\d{4})([1-4])Q$")     # '20262Q' -> year 2026, quarter 2Q
YCOL = re.compile(r"^\d{4}$")
NUM = re.compile(r"^-?\d+(\.\d+)?$")

DATASETS = [
    {
        "key": "quarterly",
        "role": "primary",
        "dataset_id": "d_5c8e5801c2a64e2e6b16608296ef3e02",
        "file": "credit-charge-cards-quarterly.csv",
    },
    {
        "key": "annual",
        "role": "cross-check",
        "dataset_id": "d_b40deadbdc470e97b9e16de99c5e6ee2",
        "file": "credit-charge-cards-annual.csv",
    },
]

# Freshness floor for the quarterly file: the latest quarter must be within two
# quarters of today, so a truncated or stale pull fails loudly instead of shipping
# quietly (a hard-coded floor silently goes stale as the series advances).
Q_CONTIG_MIN = 40       # at least this many quarters overall


def freshness_floor(today=None):
    """Lowest acceptable latest-quarter index (year*4 + quarter), computed from today."""
    today = today or datetime.now(timezone.utc)
    current_q = today.year * 4 + (today.month - 1) // 3 + 1
    return current_q - 2


def get(url, ref="https://data.gov.sg/"):
    r = u.Request(url, headers={"User-Agent": UA, "Accept": "*/*", "Referer": ref})
    with u.urlopen(r, timeout=180) as resp:
        return resp.read()


def fetch_to_part(dataset_id, part):
    base = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}"
    url = ""
    try:
        j = json.loads(get(base + "/poll-download"))
        url = (j.get("data") or {}).get("url") or ""
    except Exception as e:  # the pre-initiate poll is optional — say why it produced nothing
        print(f"  poll-download before initiate failed: {e}", file=sys.stderr)
    if not url:
        get(base + "/initiate-download")
        for attempt in range(15):
            time.sleep(1.5)
            try:
                j = json.loads(get(base + "/poll-download"))
                url = (j.get("data") or {}).get("url") or ""
            except Exception as e:
                print(f"  poll-download retry {attempt + 1} failed: {e}", file=sys.stderr)
                continue
            if url:
                break
    if not url:
        return None, "no signed URL returned — try again in a minute"
    data = get(url)
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(data)
    return data, None


def _shape(text):
    """Parse CSV text with the csv module — ONE parser for the whole script (a quoted
    comma passes here but would break a naive split; download and analysis must agree)."""
    rows = [r for r in csv.reader(text.splitlines()) if r and any(c.strip() for c in r)]
    header = rows[0] if rows else []
    return header, rows[1:]


def validate_quarterly(data):
    """Structural validation + summary for the quarterly wide CSV (raw bytes in;
    the hash is over those bytes, so it matches `sha256sum` on the file)."""
    text = data.decode("utf-8", errors="replace")
    header, body = _shape(text)
    problems = []
    if not header or header[0] != "DataSeries":
        return None, ["first header column is not 'DataSeries'"]
    qcols = [c for c in header[1:] if QCOL.match(c)]
    if len(qcols) != len(header) - 1:
        bad = [c for c in header[1:] if not QCOL.match(c)]
        problems.append(f"non-quarter header columns: {bad[:5]}")
    if len(qcols) < Q_CONTIG_MIN:
        problems.append(f"only {len(qcols)} quarter columns (< {Q_CONTIG_MIN})")
    names = [r[0] for r in body]
    if sorted(names) != sorted(SERIES):
        problems.append(f"series rows are {names}, expected {SERIES}")
    for r in body:
        if len(r) != len(header):
            problems.append(f"row '{r[0]}' has {len(r)} values, expected {len(header)}")
        nonnum = [v for v in r[1:] if not NUM.match(v)]
        if nonnum:
            problems.append(f"row '{r[0]}' has non-numeric values: {nonnum[:3]}")
    idx = []
    for c in qcols:
        m = QCOL.match(c)
        idx.append(int(m.group(1)) * 4 + int(m.group(2)))
    idx_sorted = sorted(idx)
    if idx_sorted and len(set(idx_sorted)) != len(idx_sorted):
        problems.append("duplicate quarter columns")
    if idx_sorted and any(b - a != 1 for a, b in zip(idx_sorted, idx_sorted[1:])):
        problems.append("quarter columns are not contiguous")
    latest = max(idx) if idx else 0
    floor = freshness_floor()
    if latest < floor:
        problems.append(f"latest quarter index {latest} is below the freshness floor {floor} "
                        f"(latest quarter must be within two quarters of today)")
    if problems:
        return None, problems
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "rows": len(body),
        "quarters": len(qcols),
        "quarter_min": _fmt_q(idx_sorted[0]),
        "quarter_max": _fmt_q(idx_sorted[-1]),
        "series": names,
    }, []


def _fmt_q(index):
    """Quarter index (year*4 + quarter) -> '2026 Q2'."""
    return f"{(index - 1) // 4} Q{((index - 1) % 4) + 1}"


def validate_annual(data):
    """Structural validation + summary for the annual wide CSV (raw bytes in; byte hash)."""
    text = data.decode("utf-8", errors="replace")
    header, body = _shape(text)
    problems = []
    if not header or header[0] != "DataSeries":
        return None, ["first header column is not 'DataSeries'"]
    ycols = [c for c in header[1:] if YCOL.match(c)]
    if len(ycols) != len(header) - 1:
        bad = [c for c in header[1:] if not YCOL.match(c)]
        problems.append(f"non-year header columns: {bad[:5]}")
    names = [r[0] for r in body]
    if sorted(names) != sorted(SERIES):
        problems.append(f"series rows are {names}, expected {SERIES}")
    for r in body:
        if len(r) != len(header):
            problems.append(f"row '{r[0]}' has {len(r)} values, expected {len(header)}")
        nonnum = [v for v in r[1:] if not (NUM.match(v) or v == "na")]
        if nonnum:
            problems.append(f"row '{r[0]}' has unexpected values: {nonnum[:3]}")
    if problems:
        return None, problems
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "rows": len(body),
        "years": len(ycols),
        "year_min": min(ycols),
        "year_max": max(ycols),
        "series": names,
    }, []


def write_manifest(infos, retrieved_at):
    m = {
        "source": "data.gov.sg — api-open v1 public API (signed URL flow)",
        "retrieved_at": retrieved_at,
        "files": {},
    }
    for ds in DATASETS:
        info = infos[ds["key"]]
        m["files"][ds["file"]] = {
            "dataset_id": ds["dataset_id"],
            "dataset_url": f"https://data.gov.sg/datasets/{ds['dataset_id']}/view",
            "role": ds["role"],
            **info,
        }
    MANIFEST.write_text(json.dumps(m, indent=2), encoding="utf-8")
    print("manifest:", MANIFEST.as_posix())
    for fname, info in m["files"].items():
        cov = (f"{info['quarter_min']} → {info['quarter_max']}" if "quarter_max" in info
               else f"{info['year_min']} → {info['year_max']}")
        print(f"    {fname}: {info['bytes']} bytes · sha256 {info['sha256'][:12]}… · coverage {cov}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download even if the files exist")
    args = ap.parse_args()

    present = {ds["key"]: (RAW / ds["file"]) for ds in DATASETS}
    if all(p.exists() for p in present.values()) and not args.force:
        print("raw files already present — use --force to refresh")
        for p in present.values():
            print("  ", p.as_posix())
        if not MANIFEST.exists():
            infos = {}
            ok = True
            for ds in DATASETS:
                data = present[ds["key"]].read_bytes()
                info, problems = (validate_quarterly if ds["key"] == "quarterly" else validate_annual)(data)
                if problems:
                    ok = False
                    print(f"  [FAIL] existing {ds['file']}: {problems}")
                infos[ds["key"]] = info
            if ok:
                mtime = datetime.fromtimestamp(present["quarterly"].stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
                write_manifest(infos, mtime)
        else:
            # byte-level receipt on the no-op path: files must still match the manifest
            m = json.loads(MANIFEST.read_text(encoding="utf-8"))
            for ds in DATASETS:
                want = (m["files"].get(ds["file"]) or {}).get("sha256", "")
                got = hashlib.sha256(present[ds["key"]].read_bytes()).hexdigest()
                print(f"   [{'OK' if got == want else 'MISMATCH'}] {ds['file']} sha256 {got[:12]}…")
                if got != want:
                    print("          differs from the manifest — re-run with --force to re-pull and refresh it")
        return

    infos = {}
    for ds in DATASETS:
        out = RAW / ds["file"]
        part = out.with_name(out.name + ".part")
        print(f"downloading {ds['dataset_id']} ({ds['role']}) …")
        data, err = fetch_to_part(ds["dataset_id"], part)
        if err:
            part.unlink(missing_ok=True)
            raise SystemExit(f"{ds['file']}: {err} — existing files left untouched")
        data = part.read_bytes()
        info, problems = (validate_quarterly if ds["key"] == "quarterly" else validate_annual)(data)
        if problems:
            part.unlink(missing_ok=True)
            raise SystemExit(f"{ds['file']} failed structure validation — kept existing file:\n  - " + "\n  - ".join(problems))
        part.replace(out)
        infos[ds["key"]] = info
        cov = (f"{info['quarter_min']} → {info['quarter_max']}" if "quarter_max" in info else f"{info['year_min']} → {info['year_max']}")
        print(f"  ok: {info['bytes']} bytes · {info['rows']} series rows · coverage {cov}")

    write_manifest(infos, datetime.now(timezone.utc).isoformat(timespec="seconds"))


if __name__ == "__main__":
    sys.exit(main())
