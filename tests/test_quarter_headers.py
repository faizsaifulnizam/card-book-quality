"""Physical-header contract at standalone staging and raw-analysis caller seams."""
import csv
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QuarterHeaderTests(unittest.TestCase):
    def test_standalone_staging_rejects_physical_header_mutations_before_replacement(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as temp:
            root = Path(temp) / 'repo'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__'))
            raw = root / 'data/raw/credit-charge-cards-quarterly.csv'
            original = list(csv.reader(io.StringIO(raw.read_text(encoding='utf-8'))))
            output = root / 'data/processed/quarterly.parquet'
            output.parent.mkdir(parents=True, exist_ok=True)
            # A real previous generation, not a first-output-only assertion.
            subprocess.run([sys.executable, str(root / 'src/build_dataset.py')], check=True, capture_output=True)
            before = output.read_bytes()
            for case in ('malformed', 'duplicate-first', 'duplicate-second', 'duplicate-equal'):
                with self.subTest(case=case):
                    rows = [row[:] for row in original]
                    if case == 'malformed':
                        rows[0][1] = '2026XQ'
                        diagnostic = 'non-quarter header columns'
                    else:
                        for row in rows:
                            row.insert(2, row[1])
                        if case != 'duplicate-equal':
                            index = 1 if case == 'duplicate-first' else 2
                            rows[5][index] = '999'
                        diagnostic = 'duplicate quarter columns'
                    with raw.open('w', newline='', encoding='utf-8') as file:
                        csv.writer(file).writerows(rows)
                    source = raw.read_bytes()
                    result = subprocess.run([sys.executable, str(root / 'src/build_dataset.py')], capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(diagnostic, result.stdout + result.stderr)
                    self.assertEqual(output.read_bytes(), before)
                    self.assertEqual(raw.read_bytes(), source)


    def test_raw_analysis_rejects_ambiguous_headers(self):
        sys.path.insert(0, str(ROOT))
        from src import analysis
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as temp:
            raw = Path(temp) / 'quarterly.csv'
            original = list(csv.reader(io.StringIO(analysis.RAWQ.read_text(encoding='utf-8'))))
            for case in ('malformed', 'duplicate-first', 'duplicate-second', 'duplicate-equal'):
                with self.subTest(case=case):
                    rows = [row[:] for row in original]
                    if case == 'malformed':
                        rows[0][1] = '2026XQ'
                        diagnostic = 'non-quarter header columns'
                    else:
                        for row in rows:
                            row.insert(2, row[1])
                        if case != 'duplicate-equal':
                            rows[5][1 if case == 'duplicate-first' else 2] = '999'
                        diagnostic = 'duplicate quarter columns'
                    with raw.open('w', newline='', encoding='utf-8') as file:
                        csv.writer(file).writerows(rows)
                    with patch.object(analysis, 'RAWQ', raw):
                        with self.assertRaisesRegex(SystemExit, diagnostic):
                            analysis.load_raw()


    def test_wrapper_and_analysis_preserve_complete_previous_generation(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as temp:
            root = Path(temp) / 'repo'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__'))
            raw = root / 'data/raw/credit-charge-cards-quarterly.csv'
            original = list(csv.reader(io.StringIO(raw.read_text(encoding='utf-8'))))
            def snapshot():
                return {str(p.relative_to(root)): p.read_bytes()
                        for sub in ('data/processed', 'outputs', 'reports/figures', 'docs/img')
                        for p in (root / sub).rglob('*') if p.is_file()}
            before = snapshot()
            manifest = (root / 'data/raw/pull_manifest.json').read_bytes()
            for case in ('malformed', 'duplicate-first', 'duplicate-second', 'duplicate-equal'):
                rows = [row[:] for row in original]
                if case == 'malformed':
                    rows[0][1] = '2026XQ'
                else:
                    for row in rows:
                        row.insert(2, row[1])
                    if case != 'duplicate-equal':
                        rows[5][1 if case == 'duplicate-first' else 2] = '999'
                with raw.open('w', newline='', encoding='utf-8') as file:
                    csv.writer(file).writerows(rows)
                source = raw.read_bytes()
                for stage, diagnostic in (('run_all.py', 'manifest'), ('analysis.py', 'quarterly header validation failed')):
                    with self.subTest(case=case, stage=stage):
                        result = subprocess.run([sys.executable, str(root / 'src' / stage)], capture_output=True, text=True)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(diagnostic, result.stdout + result.stderr)
                        self.assertEqual(before, snapshot())
                        self.assertEqual(raw.read_bytes(), source)
                        self.assertEqual((root / 'data/raw/pull_manifest.json').read_bytes(), manifest)

    def test_header_controls_are_order_independent_and_not_clock_dependent(self):
        sys.path.insert(0, str(ROOT))
        from src import download
        from unittest.mock import patch
        original = (ROOT / 'data/raw/credit-charge-cards-quarterly.csv').read_bytes()
        header = list(csv.reader(io.StringIO(original.decode('utf-8'))))[0]
        self.assertEqual(download.validate_quarter_header(header), [])
        self.assertEqual(download.validate_quarter_header([header[0]] + header[:0:-1]), [])
        with patch.object(download, 'freshness_floor', return_value=8121):
            self.assertEqual(download.validate_quarter_header(header), [])
            self.assertIn('freshness floor', str(download.validate_quarterly(original)[1]))
        for header in ([], ['WrongKey'], ['DataSeries', '20262Q\n']):
            self.assertTrue(download.validate_quarter_header(header))


if __name__ == '__main__':
    unittest.main()
