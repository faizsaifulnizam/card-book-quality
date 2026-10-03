"""Re-run locally and hash-compare all generated deliverables in one environment.

This checks repeat determinism, not pixel equality across operating systems and
not spreadsheet-engine formula evaluation. It uses the normal pipeline entrypoint.
"""
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def artifact_hashes():
    paths = sorted((ROOT / "outputs").glob("*.csv"))
    paths += [ROOT / "outputs" / "quick_check.xlsx"]
    paths += sorted((ROOT / "reports" / "figures").glob("*.png"))
    paths += sorted((ROOT / "docs" / "img").glob("f*.png"))
    if len(paths) != 20:
        raise AssertionError(f"Expected 3 CSVs, workbook, and 16 chart copies; got {len(paths)}")
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    before = artifact_hashes()
    subprocess.run([sys.executable, str(ROOT / "src" / "run_all.py")], cwd=ROOT, check=True)
    after = artifact_hashes()
    changed = [name for name in before if before[name] != after.get(name)]
    if changed:
        raise AssertionError(f"Regeneration changed artifact bytes: {changed}")
    for source in (ROOT / "reports" / "figures").glob("*.png"):
        target = ROOT / "docs" / "img" / source.name
        if source.read_bytes() != target.read_bytes():
            raise AssertionError(f"Site chart differs: {source.name}")
    print(f"PASS: {len(after)} artifact SHA-256 hashes unchanged; all site chart copies match")


if __name__ == "__main__":
    main()
