"""Fixed-snapshot narrative checks, independent of analysis.py and DuckDB.

These check raw arithmetic and maintained claims, not Excel evaluation or visual QA.
Run: python -m unittest discover -s tests -p test_narrative.py
"""
import csv
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def wide(name):
    with (ROOT / 'data/raw' / name).open(encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    return {r[0]: dict(zip(rows[0][1:], r[1:])) for r in rows[1:]}


def midpoint(old_balance, new_balance, old_ratio, new_ratio):
    return ((new_balance - old_balance) * (old_ratio + new_ratio) / 2,
            (new_ratio - old_ratio) * (old_balance + new_balance) / 2)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.images = []
        self.links = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
            self.stack.append(attrs.get('href', ''))
        if tag == 'img':
            self.images.append((attrs, self.stack[-1] if self.stack else None))

    def handle_endtag(self, tag):
        if tag == 'a' and self.stack:
            self.stack.pop()


class NarrativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = wide('credit-charge-cards-quarterly.csv')
        cls.a = wide('credit-charge-cards-annual.csv')
        cls.readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        cls.site = (ROOT / 'docs/index.html').read_text(encoding='utf-8')
        cls.sensitivity = (ROOT / 'docs/sensitivity.md').read_text(encoding='utf-8')

    def avg(self, series, year):
        values = [float(self.q[series][f'{year}{quarter}Q']) for quarter in range(1, 5)]
        return sum(values) / 4

    def test_headline_matches_raw_and_csv(self):
        balances = [self.avg('Rollover Balance', y) for y in (2024, 2025)]
        losses = [4 * self.avg('Bad Debts Written Off', y) for y in (2024, 2025)]
        v, r = midpoint(*balances, *(w / b for w, b in zip(losses, balances)))
        self.assertAlmostEqual(losses[1] - losses[0], 96.5)
        self.assertAlmostEqual(v, 63.900864520285)
        self.assertAlmostEqual(r, 32.599135479715)
        with (ROOT / 'outputs/yearly_bridge.csv').open(newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        # Check the published values without coupling to every optional output column.
        row = next(row for row in rows if row['year'] == '2025')
        for value in ('96.5', '63.9', '32.6'):
            self.assertIn(value, row.values())
        for text in (self.readme, self.site):
            for value in ('96.5', '63.9', '32.6'):
                self.assertIn(value, text)

    def test_published_basis_differences_not_half_million(self):
        b0, b1 = [self.avg('Rollover Balance', y) for y in (2024, 2025)]
        w0, w1 = [4 * self.avg('Bad Debts Written Off', y) for y in (2024, 2025)]
        v, r = midpoint(b0, b1, w0 / b0, w1 / b1)
        pv, pr = midpoint(b0, b1, *(float(self.a['Charge-Off Rates'][str(y)]) / 100
                                   for y in (2024, 2025)))
        for actual, expected in ((pv - v, -0.350664520285),
                                 (pr - r, 0.812414520285),
                                 (w1 - w0 - pv - pr, -0.46175)):
            self.assertAlmostEqual(actual, expected)
            self.assertIn(f'{expected:+.6f}'.replace('-', '−'), self.sensitivity)
        self.assertGreater(abs(pr - r), 0.5)
        self.assertIn('basis-and-rounding residual', self.sensitivity)

    def test_denominator_and_year_end_sensitivity(self):
        for end, principal, expected in ((False, False, -31.808419822455),
                                        (False, True, 30.148644653896),
                                        (True, False, -228.378909802536),
                                        (True, True, -194.779180682559)):
            def get(series, year):
                return (float(self.q[series][f'{year}4Q']) if end
                        else self.avg(series, year))
            balances = [get('Rollover Balance', y) for y in (2024, 2025)]
            counts = [get('Principal Cardholders', y) +
                      (0 if principal else get('Supplementary Cardholders', y))
                      for y in (2024, 2025)]
            cards, per = midpoint(*counts, *(b / c for b, c in zip(balances, counts)))
            self.assertAlmostEqual(cards, expected)
            self.assertAlmostEqual(cards + per, balances[1] - balances[0])
            self.assertIn(f'{expected:+.3f}'.replace('-', '−'), self.sensitivity)

    def test_default_workbook_inputs_not_formula_evaluation(self):
        loss = self.q['Bad Debts Written Off']
        window = sum(float(loss[q]) for q in ('20253Q', '20254Q', '20261Q', '20262Q'))
        rate = self.q['Charge-Off Rates']
        change = float(rate['20262Q']) - float(rate['20252Q'])
        self.assertAlmostEqual(window, 543.4)
        self.assertAlmostEqual(change, -0.1)
        for text in (self.readme, self.site):
            self.assertIn('543.4', text)
            self.assertIn('−0.1 pt', text)
            self.assertIn('spreadsheet-engine', text)

    def test_claim_limits_and_snapshot(self):
        for text in (self.readme, self.site):
            for phrase in ('2026-10-03', 'Hermes-assisted', 'unique customers',
                           'non-revolving', 'slower repayment', 'same-season',
                           'proxy ratio', 'basis-and-rounding residual',
                           'python -m pip install --require-hashes -r requirements.lock'):
                self.assertIn(phrase.lower(), text.lower())
            for misleading in ('not more customers', 'lending quality changed',
                               'stress accumulating', 'figures re-render byte-identical'):
                self.assertNotIn(misleading, text)
        self.assertIn('https://faizsaifulnizam.github.io/card-book-quality/',
                      self.readme[:2500])

    def test_site_full_size_accessibility_and_local_links(self):
        page = Page()
        page.feed(self.site)
        self.assertIn('main', page.tags)
        self.assertEqual(page.tags.count('h1'), 1)
        self.assertIn('a:focus-visible', self.site)
        self.assertIn('grid-template-columns:1fr;gap:26px', self.site)
        charts = [(attrs, link) for attrs, link in page.images
                  if re.search(r'img/f[1-4]_', attrs.get('src', ''))]
        self.assertEqual(len(charts), 4)
        for attrs, link in charts:
            self.assertTrue(attrs.get('alt'))
            self.assertEqual(link, attrs['src'])
        for link in page.links:
            if link and not link.startswith(('https:', 'http:', '#')):
                self.assertTrue((ROOT / 'docs' / link).is_file(), link)
        self.assertEqual(self.site.count('View full-size chart</a>'), 4)

    def test_review_inventory_complete(self):
        report = (ROOT / 'docs/review-remediation.md').read_text(encoding='utf-8')
        ids = re.findall(r'^\| (\d+) \|', report, flags=re.M)
        self.assertEqual([int(n) for n in ids], list(range(1, 45)))


if __name__ == '__main__':
    unittest.main()
