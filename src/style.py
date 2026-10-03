"""Series style loader — registers the bundled Inter fonts and applies the shared matplotlib style.

Usage (from repo root):
    from src.style import use_series_style
    use_series_style()

Fonts live in ONE place: docs/fonts/ (with both families' OFL licences) — the same
directory the Pages site serves, so the repo ships each font exactly once.
Falls back to matplotlib defaults (DejaVu) if font files are missing — charts still render.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager

ASSETS = Path(__file__).resolve().parent.parent / "assets"
FONTS = Path(__file__).resolve().parent.parent / "docs" / "fonts"  # single font home (site + figures)


def use_series_style(dark: bool = False):
    """Apply the shared portfolio style — light by default, `dark=True` for the dark twin. Safe to call more than once."""
    for ttf in ("Inter-Regular.ttf", "Inter-SemiBold.ttf"):
        f = FONTS / ttf
        if f.exists():
            font_manager.fontManager.addfont(str(f))
    plt.style.use(str(ASSETS / ("style-dark.mplstyle" if dark else "style.mplstyle")))


if __name__ == "__main__":
    use_series_style()
    names = sorted({f.name for f in font_manager.fontManager.ttflist if "Inter" in f.name})
    print("series style applied — Inter families visible to matplotlib:", names)
