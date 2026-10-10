"""Compact publisher notes must distinguish the source series from our proxy."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import build_workbook, figures
import duckdb


class PublisherNoteTests(unittest.TestCase):
    def test_workbook_note_qualifies_unverified_publisher_method(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as temp:
            path = Path(temp) / 'check.xlsx'
            with contextlib.redirect_stdout(io.StringIO()):
                build_workbook.build(path)
            wb = load_workbook(path)
            notes = '\n'.join(str(c.value) for row in wb['Quick check'] for c in row if c.value)
            self.assertIn('publisher averaging/write-off treatment unverified', notes)
            self.assertIn('Proxy = annual write-offs / mean quarter-end rollover', notes)
            self.assertNotIn('as published: bad debts written off ÷ average rollover balance, annualised', notes)


    def test_rendered_timeline_qualifies_publisher_definition(self):
        con = duckdb.connect()
        con.execute(f"CREATE VIEW quarterly AS SELECT * FROM read_parquet('{figures.PARQUET_SQL}')")
        figures.run_script(con, ROOT / 'sql/02_metrics.sql')
        text = []
        def capture(fig, name):
            text.extend(t.get_text() for t in fig.findobj(figures.matplotlib.text.Text))
            figures.plt.close(fig)
        with patch.object(figures, 'save', capture), contextlib.redirect_stdout(io.StringIO()):
            figures.fig1_timeline(con)
        notes = '\n'.join(text)
        self.assertIn('publisher averaging/write-off treatment unverified', notes)
        self.assertNotIn('as published: bad debts written off ÷ average rollover balance, annualised', notes)


    def test_source_trail_distinguishes_recovered_notes_from_unknowns(self):
        text = (ROOT / 'docs/data_audit.md').read_text(encoding='utf-8')
        self.assertIn('M701071', text)
        self.assertIn("reporting entities' total billings of cardholders in and outside Singapore", text)
        self.assertIn('Blank rate/write-off footnotes', text)
        self.assertIn('Archival copies, not a fresh retrieval', text)


    def test_archived_response_bytes_survive_windows_checkout(self):
        import hashlib
        import json
        import subprocess
        receipt = json.loads((ROOT / 'docs/source-evidence/receipt.json').read_text())
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as temp:
            for item in receipt:
                relative = 'docs/source-evidence/' + item['file']
                result = subprocess.run(['git', '-c', 'core.autocrlf=true', 'checkout-index',
                                         '--prefix=' + Path(temp).as_posix() + '/', '--', relative],
                                        cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                body = (Path(temp) / relative).read_bytes()
                self.assertEqual(hashlib.sha256(body).hexdigest(), item['body_sha256'])


if __name__ == '__main__':
    unittest.main()
