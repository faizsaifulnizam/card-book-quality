"""Analysis regressions through the real runner, with output I/O in scratch."""
import contextlib
import csv
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import analysis as a

# Hermes scratch on the local machine; ordinary tempfile location on CI.
SCRATCH = Path.home() / 'AppData/Local/hermes/cache/scratch'
TEMP_DIR = SCRATCH if SCRATCH.is_dir() else None


class AnalysisTests(unittest.TestCase):
    def run_analysis(self, annual=None):
        with tempfile.TemporaryDirectory(dir=TEMP_DIR) as tmp:
            out = Path(tmp)
            with patch.object(a, 'OUT', out), patch.object(a, 'RAWA', annual or a.RAWA), contextlib.redirect_stdout(io.StringIO()) as log:
                with self.assertRaises(SystemExit) as exit_:
                    a.main()
            self.assertEqual(exit_.exception.code, 0, log.getvalue())
            tables = {}
            for name in ('book_split', 'yearly_bridge', 'sensitivity'):
                with (out / f'{name}.csv').open(encoding='utf-8', newline='') as file:
                    tables[name] = list(csv.DictReader(file))
            return tables, log.getvalue()

    def test_no_annual_overlap_fails_without_overwriting_outputs(self):
        with tempfile.TemporaryDirectory(dir=TEMP_DIR) as tmp:
            out = Path(tmp)
            annual = out / 'annual.csv'
            with a.RAWA.open(encoding='utf-8', newline='') as file:
                rows = list(csv.reader(file))
            rows = [r[:1] + ['1900'] if i == 0 else r[:1] + [r[1]] for i, r in enumerate(rows)]
            with annual.open('w', encoding='utf-8', newline='') as file:
                csv.writer(file).writerows(rows)
            target = out / 'yearly_bridge.csv'
            target.write_text('preserved', encoding='utf-8')
            with patch.object(a, 'OUT', out), patch.object(a, 'RAWA', annual), contextlib.redirect_stdout(io.StringIO()) as log:
                with self.assertRaises(SystemExit) as exit_:
                    a.main()
            self.assertEqual(exit_.exception.code, 1)
            self.assertIn('annual source overlap: 0', log.getvalue())
            self.assertEqual(target.read_text(encoding='utf-8'), 'preserved')

    def test_published_basis_retains_separate_contributions_and_residual(self):
        tables, log = self.run_analysis()
        published = next(r for r in tables['sensitivity'] if r['variant'].startswith('published annual'))
        self.assertEqual(published['volume_sgd_m'], '63.55')
        self.assertEqual(published['rate_sgd_m'], '33.41')
        self.assertEqual(published['residual_sgd_m'], '-0.46')
        self.assertEqual(published['joint_sgd_m'], '')
        self.assertIn('basis-and-rounding residual', log)
        for table in tables.values():
            for row in table:
                self.assertNotIn('-0.0', row.values())

    def test_annual_source_lag_is_pending_not_a_crash_or_substituted_rate(self):
        with tempfile.TemporaryDirectory(dir=TEMP_DIR) as tmp:
            path = Path(tmp) / 'annual.csv'
            with a.RAWA.open(encoding='utf-8', newline='') as file:
                rows = list(csv.reader(file))
            index = rows[0].index('2025')
            for row in rows:
                del row[index]
            with path.open('w', encoding='utf-8', newline='') as file:
                csv.writer(file).writerows(rows)
            tables, log = self.run_analysis(path)
        latest = tables['yearly_bridge'][-1]
        self.assertEqual(latest['year'], '2025')
        self.assertEqual(latest['rate_pct_pub_annual'], '')
        self.assertEqual(latest['annual_crosscheck_status'], 'pending')
        self.assertIn('pending', log)
        pub = next(r for r in tables['sensitivity'] if r['variant'].startswith('published annual'))
        self.assertEqual(pub['window_new'], '2024')
        base = next(r for r in tables['sensitivity'] if r['variant'].startswith('base-weighted'))
        self.assertEqual(base['window_new'], '2025')

    def test_principal_and_year_end_splits_expose_denominator_sensitivity(self):
        tables, _ = self.run_analysis()
        row = next(r for r in tables['book_split'] if r['year'] == '2025')
        self.assertIn('principal_cards_effect_sgd_m', row)
        self.assertAlmostEqual(float(row['principal_cards_effect_sgd_m']), 30.15, places=2)
        self.assertAlmostEqual(float(row['balance_per_principal_card_effect_sgd_m']), 1104.68, places=2)
        self.assertIn('year_end_principal_cards_effect_sgd_m', row)
        self.assertLess(float(row['year_end_principal_cards_change_pct']), 0)
        self.assertAlmostEqual(float(row['year_end_principal_cards_effect_sgd_m']) + float(row['year_end_balance_per_principal_card_effect_sgd_m']), float(row['year_end_delta_rollover_sgd_m']), delta=0.01)


if __name__ == '__main__':
    unittest.main()
