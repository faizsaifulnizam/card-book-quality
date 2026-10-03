"""Regressions at the rendered-chart seam; no final assets are written."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import duckdb
import matplotlib.pyplot as plt
from src import figures as f


def connection():
    con = duckdb.connect()
    con.execute(f"CREATE VIEW quarterly AS SELECT * FROM read_parquet('{f.PARQUET}')")
    f.run_script(con, f.ROOT / 'sql/02_metrics.sql')
    return con


class FigureTests(unittest.TestCase):
    def tearDown(self):
        plt.close('all')

    def test_peak_falls_back_to_proxy_when_published_source_has_no_overlap(self):
        with patch.object(f, 'ANNUAL_RAW', f.ROOT / 'absent-annual.csv'):
            latest, peak, pairs = f._panel_years(connection())
        self.assertEqual(latest, 2025)
        self.assertEqual(peak, 2020)
        self.assertIn((2020, 2019), pairs)

    def test_f2_falling_change_uses_single_sign_and_explains_negative_colours(self):
        con = connection()
        con.execute('DELETE FROM annual WHERE year > 2016')
        captured = []
        with patch.object(f, 'save', side_effect=lambda fig, name: captured.append(fig)):
            f.fig2_bridge(con)
        fig = captured[0]
        self.assertNotIn('+-', fig.axes[0].get_title(loc='left'))
        self.assertIn('negative volume = grey', fig.texts[-1].get_text())
        self.assertIn('negative ratio = violet', fig.texts[-1].get_text())

    def test_f3_legend_identifies_both_negative_colours(self):
        captured = []
        with patch.object(f, 'save', side_effect=lambda fig, name: captured.append(fig)):
            f.fig3_contributions(connection())
        labels = [t.get_text() for t in captured[0].axes[0].get_legend().get_texts()]
        self.assertIn('volume (negative)', labels)
        self.assertIn('ratio (negative)', labels)

    def test_left_panel_titles_clear_suptitle_in_both_themes(self):
        for palette in (f.LIGHT, f.DARK):
            f.use_palette(palette)
            f.use_series_style(dark=palette is f.DARK)
            captured = []
            with patch.object(f, 'save', side_effect=lambda fig, name: captured.append(fig)):
                for render in (f.fig1_timeline, f.fig2_bridge, f.fig3_contributions, f.fig4_book):
                    render(connection())
            for fig in captured:
                fig.canvas.draw()
                renderer = fig.canvas.get_renderer()
                for ax in fig.axes:
                    if ax.get_title(loc='left'):
                        self.assertFalse(fig._suptitle.get_window_extent(renderer).overlaps(ax._left_title.get_window_extent(renderer)))

    def test_f4_displayed_percent_and_supplementary_period_match_inputs(self):
        captured = []
        with patch.object(f, 'save', side_effect=lambda fig, name: captured.append(fig)):
            f.fig4_book(connection())
        fig = captured[0]
        self.assertIn('68.3 → 83.5 (+22.4%)', fig.axes[2].get_title(loc='left'))
        self.assertIn('2015–2025 annual averages', fig.axes[0].get_title(loc='left'))
        self.assertIn('Card counts', fig.axes[0].get_title(loc='left'))

    def test_f4_break_uses_q2_to_q3_and_quarter_end_labels(self):
        captured = []
        with patch.object(f, 'save', side_effect=lambda fig, name: captured.append(fig)):
            f.fig4_book(connection())
        fig = captured[0]
        annotation = next(t for t in fig.axes[0].texts if 'flagged' in t.get_text())
        self.assertIn('6.35M → 6.10M (-4.0%)', annotation.get_text())
        self.assertEqual(annotation.xy[0].isoformat(), '2025-07-01')
        self.assertIn('quarter-end observations', fig.texts[-1].get_text())
        self.assertIn('principal-only', fig.axes[1].texts[0].get_text())
        self.assertIn('annual-average', fig.axes[1].texts[0].get_text())
        self.assertIsNotNone(fig.axes[1].texts[0].get_bbox_patch(), 'gridlines must not run through explanatory text')
        self.assertIn('denominator', fig.axes[1].get_title(loc='left'))


if __name__ == '__main__':
    unittest.main()
