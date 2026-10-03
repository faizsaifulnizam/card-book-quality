"""One entrypoint for the whole pipeline, in order: download → dataset → analysis → figures → workbook.

Run: python src/run_all.py   (any cwd; every stage keeps its own receipts)

Stages run as separate processes so a failure stops the chain with that stage's own
error output; every stage validates before writing, so a failed run never leaves a
half-updated output. The download stage skips when the (vendored) raw files are
present — run src/download.py --force first to re-pull.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGES = ["download.py", "build_dataset.py", "analysis.py", "figures.py", "build_workbook.py"]


def main():
    for stage in STAGES:
        print(f"\n===== {stage} =====")
        r = subprocess.run([sys.executable, str(ROOT / "src" / stage)], cwd=str(ROOT))
        if r.returncode != 0:
            sys.exit(f"{stage} failed (exit {r.returncode}) — later stages did not run")
    print("\nrun_all: every stage completed")


if __name__ == "__main__":
    main()
