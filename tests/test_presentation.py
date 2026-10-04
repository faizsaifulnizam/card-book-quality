"""Small offline contracts; actual GitHub sanitization/theme selection is browser-verified separately."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class PresentationTests(unittest.TestCase):
    def test_timeline_picture_uses_github_safe_standalone_block(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        match = re.search(r"(?m)^<picture>\n(?:(?!</picture>).)*f1_timeline\.png(?:(?!</picture>).)*</picture>", readme, re.S)
        self.assertIsNotNone(match, "F1 needs a standalone picture, not a multiline anchor wrapper")
        self.assertIn('srcset="reports/figures/f1_timeline-dark.png"', match.group())
        self.assertIn("[View full-size timeline]", readme)
        self.assertIn("[dark version](reports/figures/f1_timeline-dark.png)", readme)

    def test_data_provenance_is_an_image_badge_link(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertRegex(readme, r"\[!\[Data: MAS via data\.gov\.sg\]\([^)]*\)\]\(https://data\.gov\.sg/datasets/d_5c8e5801c2a64e2e6b16608296ef3e02/view\)")

    def test_banner_labels_do_not_equate_ratio_with_lending_quality(self):
        for name in ("banner.svg", "banner-dark.svg"):
            with self.subTest(theme=name):
                source = (ROOT / "assets" / name).read_bytes()
                self.assertEqual(source, (ROOT / "docs/img" / name).read_bytes())
                # Trusted tracked local SVG only; no untrusted XML or external entity loading.
                text = " ".join(ET.fromstring(source).itertext())
                self.assertNotIn("rate = lending quality", text)
                self.assertIn("balance = rollover", text)
                self.assertIn("ratio = loss proxy", text)


if __name__ == "__main__":
    unittest.main()
