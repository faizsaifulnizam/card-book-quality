"""Offline pipeline regressions; all writes occur in disposable scratch copies."""
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.root = Path(self.tmp.name) / 'repo'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__'))

    def tearDown(self):
        self.tmp.cleanup()

    def run_stage(self, stage, *args):
        return subprocess.run([sys.executable, str(self.root / 'src' / stage), *args],
                              cwd=self.root, capture_output=True, text=True)

    def mutate_cell(self, value):
        path = self.root / 'data/raw/credit-charge-cards-quarterly.csv'
        with path.open(newline='', encoding='utf-8') as f:
            rows = list(csv.reader(f))
        rows[1][1] = value
        with path.open('w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(rows)

    def test_fractional_counts_rejected_before_cast(self):
        self.mutate_cell('100.5')
        output = self.root / 'data/processed/quarterly.parquet'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b'previous parquet')
        result = self.run_stage('build_dataset.py')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('card counts whole', result.stdout)
        self.assertEqual(output.read_bytes(), b'previous parquet')

    def test_missing_cell_counted_in_physical_grid(self):
        self.mutate_cell('')
        result = self.run_stage('build_dataset.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stdout, r'raw cells:\s+282')
        self.assertRegex(result.stdout, r'missing:\s+1')

    def test_failed_refresh_preserves_source_pair(self):
        raw = self.root / 'data/raw'
        before = {p.name: p.read_bytes() for p in raw.iterdir() if p.is_file()}
        script = '''
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, 'src')
import download
original = (download.RAW / download.DATASETS[0]['file']).read_bytes()
def fetch(dataset, part):
    data = original + b'\\n' if dataset == download.DATASETS[0]['dataset_id'] else b'bad annual'
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(data)
    return data, None
sys.argv = ['download.py', '--force']
with patch.object(download, 'freshness_floor', return_value=8106), patch.object(download, 'fetch_to_part', fetch):
    download.main()
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=self.root,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        after = {p.name: p.read_bytes() for p in raw.iterdir() if p.is_file()}
        self.assertEqual(before, after)

    def test_source_overlap_missing_annual_year_stops_refresh(self):
        raw = self.root / 'data/raw'
        before = {p.name: p.read_bytes() for p in raw.iterdir() if p.is_file()}
        script = '''
import sys, csv, io
from unittest.mock import patch
sys.path.insert(0, 'src')
import download
original = {ds['dataset_id']: (download.RAW / ds['file']).read_bytes() for ds in download.DATASETS}
def fetch(dataset, part):
    data = original[dataset]
    if dataset == download.DATASETS[1]['dataset_id']:
        rows = list(csv.reader(io.StringIO(data.decode())))
        latest = max(range(1, len(rows[0])), key=lambda i: rows[0][i])
        for row in rows:
            del row[latest]
        out = io.StringIO()
        csv.writer(out).writerows(rows)
        data = out.getvalue().encode()
    part.write_bytes(data)
    return data, None
sys.argv = ['download.py', '--force']
with patch.object(download, 'freshness_floor', return_value=8106), patch.object(download, 'fetch_to_part', fetch):
    download.main()
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=self.root,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('annual cross-check unavailable', result.stdout + result.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in raw.iterdir() if p.is_file()})

    def output_snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for sub in ('data/processed', 'outputs', 'reports/figures', 'docs/img')
                for p in (self.root / sub).rglob('*') if p.is_file()}

    def test_failed_later_stage_preserves_all_outputs(self):
        before = self.output_snapshot()
        # Executable scripts are a subprocess-boundary fault injection, not module mocks.
        (self.root / 'src/analysis.py').write_text(
            "from pathlib import Path\nPath('outputs').mkdir(exist_ok=True)\nPath('outputs/yearly_bridge.csv').write_text('partial')\n")
        (self.root / 'src/figures.py').write_text("raise SystemExit('injected figure failure')\n")
        result = self.run_stage('run_all.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('figures.py failed', result.stdout + result.stderr)
        self.assertEqual(before, self.output_snapshot())

    def test_complete_run_publishes_validated_outputs(self):
        sentinel = self.root / 'outputs/old-generation.txt'
        sentinel.write_text('old')
        result = self.run_stage('run_all.py')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('complete validated output set published', result.stdout)
        self.assertFalse(sentinel.exists())
        for name in ('yearly_bridge.csv', 'book_split.csv', 'sensitivity.csv', 'quick_check.xlsx'):
            self.assertTrue((self.root / 'outputs' / name).is_file())

    def test_missing_manifest_stops_without_inventing_retrieval(self):
        manifest = self.root / 'data/raw/pull_manifest.json'
        manifest.unlink()
        result = self.run_stage('download.py')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse(manifest.exists())

    def test_publish_failure_rolls_back_generated_directories(self):
        before = self.output_snapshot()
        script = '''
import sys, os
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, 'src')
import run_all
replace = os.replace
failed = False
def fail_publish(src, dst):
    global failed
    if Path(dst) == run_all.ROOT / 'outputs' and '.pipeline-stage-' in str(src) and not failed:
        failed = True
        raise OSError('injected publication failure')
    return replace(src, dst)
with patch.object(os, 'replace', fail_publish):
    run_all.main()
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=self.root,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('injected publication failure', result.stderr)
        self.assertEqual(before, self.output_snapshot())
        self.assertFalse(list((self.root / 'data').glob('.publish-backup-*')))

    def test_completed_run_validation_failure_preserves_outputs(self):
        before = self.output_snapshot()
        builder = self.root / 'src/build_workbook.py'
        builder.write_text(builder.read_text(encoding='utf-8') +
                           "\n(ROOT / 'outputs/yearly_bridge.csv').unlink()\n", encoding='utf-8')
        result = self.run_stage('run_all.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('yearly_bridge.csv', result.stderr)
        self.assertEqual(before, self.output_snapshot())

    def test_fixture_refresh_stays_valid_when_real_clock_advances(self):
        path = self.root / 'src/download.py'
        path.write_text(path.read_text(encoding='utf-8').replace(
            'today = today or datetime.now(timezone.utc)',
            'today = today or datetime(2030, 1, 1, tzinfo=timezone.utc)'), encoding='utf-8')
        self.test_valid_offline_refresh_publishes_pair_with_matching_hashes()

    def test_valid_offline_refresh_publishes_pair_with_matching_hashes(self):
        script = '''
import sys
from unittest.mock import patch
sys.path.insert(0, 'src')
import download
original = {ds['dataset_id']: (download.RAW / ds['file']).read_bytes() for ds in download.DATASETS}
def fetch(dataset, part):
    data = original[dataset] + b'\\n'
    part.write_bytes(data)
    return data, None
sys.argv = ['download.py', '--force']
with patch.object(download, 'freshness_floor', return_value=8106), patch.object(download, 'fetch_to_part', fetch):
    download.main()
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=self.root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        raw = self.root / 'data/raw'
        manifest = json.loads((raw / 'pull_manifest.json').read_text())
        for name, info in manifest['files'].items():
            self.assertEqual(info['sha256'], hashlib.sha256((raw / name).read_bytes()).hexdigest())
        self.assertEqual(self.run_stage('download.py').returncode, 0)

    def test_missing_raw_stops_before_download_stage(self):
        (self.root / 'data/raw/credit-charge-cards-annual.csv').unlink()
        downloader = self.root / 'src/download.py'
        # Existing main is replaced at the subprocess boundary to forbid network.
        text = downloader.read_text(encoding='utf-8').replace('    sys.exit(main())',
                                                            "    raise SystemExit('download stage attempted')")
        downloader.write_text(text, encoding='utf-8')
        result = self.run_stage('run_all.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires vendored raw pair and manifest', result.stdout + result.stderr)
        self.assertNotIn('download stage attempted', result.stdout + result.stderr)

    def test_source_publish_failure_rolls_back_pair_and_manifest(self):
        raw = self.root / 'data/raw'
        before = {p.name: p.read_bytes() for p in raw.iterdir() if p.is_file()}
        script = '''
import sys, os
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, 'src')
import download
original = {ds['dataset_id']: (download.RAW / ds['file']).read_bytes() for ds in download.DATASETS}
replace = os.replace
failed = False
def fetch(dataset, part):
    data = original[dataset] + b'\\n'
    part.write_bytes(data)
    return data, None
def fail_manifest(src, dst):
    global failed
    if Path(dst) == download.MANIFEST and '.source-stage-' in str(src) and not failed:
        failed = True
        raise OSError('injected manifest publication failure')
    return replace(src, dst)
sys.argv = ['download.py', '--force']
with patch.object(download, 'freshness_floor', return_value=8106), patch.object(download, 'fetch_to_part', fetch), patch.object(os, 'replace', fail_manifest):
    download.main()
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=self.root,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('injected manifest publication failure', result.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in raw.iterdir() if p.is_file()})

    def test_hash_mismatch_stops(self):
        path = self.root / 'data/raw/credit-charge-cards-quarterly.csv'
        path.write_bytes(path.read_bytes() + b'\n')
        result = self.run_stage('download.py')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('manifest', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
