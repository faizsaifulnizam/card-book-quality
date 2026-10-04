"""Review regressions through real offline stage boundaries in scratch copies."""
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


class ReviewFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.root = Path(self.tmp.name) / 'repo'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__'))

    def tearDown(self):
        self.tmp.cleanup()

    def run_stage(self, stage):
        return subprocess.run([sys.executable, str(self.root / 'src' / stage)],
                              cwd=self.root, capture_output=True, text=True)

    def run_code(self, code):
        return subprocess.run([sys.executable, '-c', code], cwd=self.root,
                              capture_output=True, text=True)

    def test_duplicate_annual_year_rejected_before_refresh_publication(self):
        raw = self.root / 'data/raw'
        before = {p.name: p.read_bytes() for p in raw.iterdir() if p.is_file()}
        result = self.run_code('''
import csv, io, sys
from unittest.mock import patch
from src import download
original = {ds['dataset_id']: (download.RAW / ds['file']).read_bytes() for ds in download.DATASETS}
rows = list(csv.reader(io.StringIO(original[download.DATASETS[1]['dataset_id']].decode())))
rows[0].append('2025')
for row in rows[1:]:
    row.append('na')
out = io.StringIO()
csv.writer(out).writerows(rows)
bad = out.getvalue().encode()
def fetch(dataset, part):
    data = bad if dataset == download.DATASETS[1]['dataset_id'] else original[dataset] + b'\\n'
    part.write_bytes(data)
    return data, None
sys.argv = ['download.py', '--force']
with patch.object(download, 'freshness_floor', return_value=8106), patch.object(download, 'fetch_to_part', fetch):
    download.main()
''')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('duplicate annual-year columns', result.stdout + result.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in raw.iterdir() if p.is_file()})

    def test_analysis_io_failures_preserve_complete_csv_generation(self):
        built = self.run_stage('build_dataset.py')
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        for boundary in ('staging', 'publication'):
            with self.subTest(boundary=boundary):
                out = self.root / 'outputs'
                names = ('yearly_bridge.csv', 'book_split.csv', 'sensitivity.csv')
                before = {name: ('previous generation: ' + name).encode() for name in names}
                for name, data in before.items():
                    (out / name).write_bytes(data)
                result = self.run_code('''
import os
from pathlib import Path
from unittest.mock import patch
from src import analysis
boundary = BOUNDARY
opened, replaced = Path.open, os.replace
installed = 0
def fail_open(path, mode='r', *args, **kwargs):
    if boundary == 'staging' and path.name == 'book_split.csv' and mode == 'w':
        raise OSError('injected staging failure')
    return opened(path, mode, *args, **kwargs)
def fail_replace(src, dst):
    global installed
    if Path(dst).parent == analysis.OUT and Path(src).parent.name.startswith('.analysis-'):
        if boundary == 'publication' and installed == 2:
            raise OSError('injected publication failure after two CSV installs')
        installed += 1
    return replaced(src, dst)
with patch.object(Path, 'open', fail_open), patch.object(os, 'replace', fail_replace):
    analysis.main()
'''.replace('BOUNDARY', repr(boundary)))
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('injected ' + boundary + ' failure', result.stderr)
                self.assertEqual(before, {name: (out / name).read_bytes() for name in names})
                self.assertFalse(list(out.glob('.publish-backup-*')))
                self.assertFalse(list(self.root.glob('.analysis-*')))

    def test_apostrophe_checkout_runs_every_sql_path_stage(self):
        built = self.run_stage('build_dataset.py')
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        quoted = self.root.with_name("card-book-O'Brien")
        self.root.rename(quoted)
        self.root = quoted
        before = {p.name: p.read_bytes() for p in (self.root / 'outputs').glob('*.csv')}
        for stage in ('build_dataset.py', 'analysis.py', 'figures.py', 'build_workbook.py'):
            with self.subTest(stage=stage):
                result = self.run_stage(stage)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root / 'outputs').glob('*.csv')})
        for image in (self.root / 'reports/figures').glob('*.png'):
            self.assertEqual(image.read_bytes(), (self.root / 'docs/img' / image.name).read_bytes())

    def test_nonfinite_numeric_cells_rejected_before_parquet_replacement(self):
        built = self.run_stage('build_dataset.py')
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        output = self.root / 'data/processed/quarterly.parquet'
        before = output.read_bytes()
        raw = self.root / 'data/raw/credit-charge-cards-quarterly.csv'
        rows = list(csv.reader(io.StringIO(raw.read_text(encoding='utf-8'))))
        for index in range(1, len(rows)):
            for value in ('NaN', 'Infinity', '-Infinity'):
                with self.subTest(series=rows[index][0], value=value):
                    changed = [row[:] for row in rows]
                    changed[index][1] = value
                    with raw.open('w', newline='', encoding='utf-8') as f:
                        csv.writer(f).writerows(changed)
                    result = self.run_stage('build_dataset.py')
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    if 'checks:' in result.stdout:
                        self.assertIn('[FAIL] numeric fields finite  (violations: 1)', result.stdout)
                    self.assertEqual(before, output.read_bytes())

    def test_executable_receipts_do_not_claim_verified_seasonality_or_monthly_basis(self):
        built = self.run_stage('build_dataset.py')
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        for stage in ('audit.py', 'analysis.py'):
            with self.subTest(stage=stage):
                result = self.run_stage(stage)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if stage == 'audit.py':
                    self.assertNotIn('annual windows absorb THIS', result.stdout)
                    self.assertIn('Pooled quarter means mix seasonal position, changing annual levels and unusual years;', result.stdout)
                    self.assertIn('like-position windows are not proof of seasonal adjustment.', result.stdout)
                    for quarter in range(1, 5):
                        self.assertRegex(result.stdout, rf'Q{quarter}: mean \d+\.\d{{2}}%  \(11 years\)')
                else:
                    self.assertNotIn('computed on monthly balances', result.stdout)
                    self.assertIn('publisher averaging-basis differences are not independently verified here', result.stdout)
                    self.assertIn('the max |Δ| is 0.218 pt', result.stdout)

    def test_f1_complete_bar_geometry_in_both_themes(self):
        built = self.run_stage('build_dataset.py')
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        for theme in ('LIGHT', 'DARK'):
            with self.subTest(theme=theme):
                result = self.run_code('''
from unittest.mock import patch
import duckdb
from src import figures as f
con = duckdb.connect()
parquet = f.PARQUET.replace("'", "''")
con.execute(f"CREATE VIEW quarterly AS SELECT * FROM read_parquet('{parquet}')")
f.run_script(con, f.ROOT / 'sql/02_metrics.sql')
f.use_palette(f.THEME)
f.use_series_style(dark=THEME_DARK)
def inspect(fig, name):
    fig.canvas.draw()
    for ax in fig.axes[:2]:
        left, right = ax.get_xlim()
        first = ax.patches[0]
        visible = min(first.get_x() + first.get_width(), right) - max(first.get_x(), left)
        print('first bar visible fraction:', visible / first.get_width())
        for bar in ax.patches:
            assert left <= bar.get_x() + 1e-9, (left, bar.get_x())
            assert bar.get_x() + bar.get_width() <= right + 1e-9
        last = ax.patches[-1]
        assert abs(right - (last.get_x() + last.get_width() / 2) - 250) < 1e-9
    f.plt.close(fig)
with patch.object(f, 'save', inspect):
    f.fig1_timeline(con)
con.close()
'''.replace('THEME_DARK', str(theme == 'DARK')).replace('THEME', theme))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(result.stdout.count('first bar visible fraction: 1.0'), 2)


if __name__ == '__main__':
    unittest.main()
