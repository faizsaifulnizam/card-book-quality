"""Reader-facing scope and historical-release distinctions."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]


class AuditCopyTests(unittest.TestCase):
    def test_legacy_release_status_is_explicit_without_claiming_publication(self):
        for name in ('README.md', 'docs/index.html'):
            text = (ROOT / name).read_text(encoding='utf-8')
            self.assertIn('v1.0/v1.0.1', text)
            self.assertIn('superseded', text.lower())
            self.assertIn('releases/tag/v1.0.2', text)
        ledger = (ROOT / 'docs/releases.md').read_text(encoding='utf-8')
        self.assertIn('153ccf4abff49d5147b6868e099ea3d5a2131af4817c31582c70a3bc07d2d91d', ledger)
        self.assertIn('Public release-description updates remain pending', ledger)
        self.assertIn('cause and timing unknown', ledger)


    def test_sensitivity_and_card_contribution_copy_is_bounded_and_unit_bearing(self):
        text = (ROOT / 'docs/sensitivity.md').read_text(encoding='utf-8')
        self.assertIn('In H1 2026 versus H1 2025', text)
        self.assertIn('recomputed-ratio component offsets 3.5 S$M', text)
        self.assertNotIn('the charge-off rate is no longer contributing', text)
        self.assertNotIn('split barely moves', text)
        site = (ROOT / 'docs/index.html').read_text(encoding='utf-8')
        self.assertIn('Card-count term: −S$32m or +S$30m', site)

    def test_current_assurance_distinguishes_selector_use_from_native_edits(self):
        for name in ('README.md', 'docs/index.html'):
            text = (ROOT / name).read_text(encoding='utf-8')
            self.assertIn('LibreOffice 26.2.5.2', text)
            self.assertIn('47', text)
            self.assertIn('selector-only', text)
            self.assertIn('averaging/write-off treatment', text)
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn('physical quarter headers', readme)
        self.assertIn('moving freshness', readme)


if __name__ == '__main__':
    unittest.main()
