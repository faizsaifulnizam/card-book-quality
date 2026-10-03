"""S3 figures — code-generated, series style, light + dark (theme-adaptive). Run: python src/figures.py (repo root).

Produces (reports/figures/), each as a light/dark pair for `<picture>` README embeds:
  f1_timeline[-dark].png  — three panels 2015 Q1 – 2026 Q2: billings · write-offs (+4-quarter sum) · charge-off rate & rollover
  f2_bridge[-dark].png    — two-panel waterfall: 2025 vs 2024 (volume-led) · 2019 → 2020 (rate-led)

Reads the parquet via DuckDB; re-runs sql/02 so figures always match the SQL. Long titles and
footnotes are width-checked at render size by pixel extent (not eyeballed).
"""
import json
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.style import use_series_style  # noqa: E402

use_series_style()

import duckdb  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402

from src.analysis import bridge as split_bridge  # noqa: E402
from src.analysis import run_script, window_stats, year_quarters  # noqa: E402

PARQUET = (ROOT / "data/processed/quarterly.parquet").as_posix()
FIGDIR = ROOT / "reports/figures"
DPI = 200
MARGIN_PX = 40  # keep text this far from the canvas edge

LIGHT = dict(ink="#14293D", petrol="#22607B", burnt="#C0552B", teal="#2E7D6B",
             violet="#8A6EAF", brass="#B9975B", muted="#5C6B79", light="#C9C6BF",
             edge="white", suffix="")
DARK = dict(ink="#E7E3DC", petrol="#4C93B5", burnt="#D97E4F", teal="#45A08B",
            violet="#A78FC8", brass="#D4B87A", muted="#8B98A5", light="#435D73",
            edge="#14293D", suffix="-dark")
T = LIGHT


def use_palette(p):
    global T
    T = p


MANIFEST = ROOT / "data/raw/pull_manifest.json"


def _source_date():
    try:
        ts = json.loads(MANIFEST.read_text(encoding="utf-8")).get("retrieved_at", "")
        return ts[:10] or None
    except Exception:
        return None


SRC = f"Source: MAS credit & charge cards (data.gov.sg), pulled {_source_date() or 'n/a'}"


def q(con, sql):
    return con.sql(sql).fetchall()


def foot(fig, text):
    return fig.text(0.01, 0.012, text, fontsize=7.5, color=T["muted"], va="bottom")


def assert_clear(fig, pairs, label):
    """Receipt for text clearance: none of these (artist, artist) bboxes may overlap."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for a, b in pairs:
        ba, bb = a.get_window_extent(r), b.get_window_extent(r)
        ok = not ba.overlaps(bb)
        print(f"   [{'PASS' if ok else 'FAIL'}] clearance {label}")
        assert ok, f"{label}: text boxes overlap"


def assert_inbounds(fig, label, pad=3):
    """Receipt: every visible text artist sits fully inside the canvas (no clipping)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    w, h = fig.canvas.get_width_height()
    bad = []
    for t in fig.findobj(matplotlib.text.Text):
        if not t.get_text().strip() or not t.get_visible():
            continue
        bb = t.get_window_extent(r)
        if bb.x0 < pad or bb.y0 < pad - 2 or bb.x1 > w - pad or bb.y1 > h - pad:
            bad.append((t.get_text()[:44].replace("\n", " / "), round(bb.x0), round(bb.y0), round(bb.x1), round(bb.y1)))
    ok = not bad
    print(f"   [{'PASS' if ok else 'FAIL'}] in-bounds {label} ({len(bad)} clipped)")
    for b in bad[:6]:
        print("       clipped:", b)
    assert ok, f"{label}: {len(bad)} text artist(s) clipped"


def assert_texts_clear(fig, label):
    """Receipt: no two annotation texts inside the same axes overlap."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bad = []
    for ax in fig.axes:
        texts = [t for t in ax.texts if t.get_text().strip() and t.get_visible()]
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                if texts[i].get_window_extent(r).overlaps(texts[j].get_window_extent(r)):
                    bad.append((texts[i].get_text()[:32], texts[j].get_text()[:32]))
    ok = not bad
    print(f"   [{'PASS' if ok else 'FAIL'}] annotation overlaps {label} ({len(bad)})")
    for b in bad[:6]:
        print("       overlap:", b)
    assert ok, f"{label}: {len(bad)} annotation overlap(s)"


def save(fig, name):
    p = FIGDIR / name.replace(".png", T["suffix"] + ".png")
    fig.savefig(p)
    plt.close(fig)
    print(f"wrote {p.as_posix()}  ({p.stat().st_size} bytes)")


def text_px(s, size_pt):
    """Rendered width of `s` in pixels at the figure DPI (Inter)."""
    fp = FontProperties(family="Inter", size=size_pt)
    return TextPath((0, 0), s, prop=fp).get_extents().width / 72 * DPI


def assert_fits(s, size_pt, label, canvas_in):
    px = max(text_px(line, size_pt) for line in s.split("\n"))
    limit = canvas_in * DPI - MARGIN_PX
    ok = px <= limit
    print(f"   [{'PASS' if ok else 'FAIL'}] width {label}: {px:.0f}px vs {limit:.0f}px limit")
    assert ok, f"{label} too wide: {px:.0f}px > {limit:.0f}px"


def fig1_timeline(con, canvas_in=9.0):
    rows = q(con, """SELECT quarter, billings_sgd_m, write_offs_sgd_m, write_offs_4q_sgd_m,
                            rollover_sgd_m, charge_off_rate_pct
                     FROM quarterly_metrics WHERE quarter >= DATE '2015-01-01' ORDER BY quarter""")
    xs = [r[0] for r in rows]
    bill = [float(r[1]) for r in rows]
    wo = [float(r[2]) for r in rows]
    wo4 = [float(r[3]) if r[3] is not None else float("nan") for r in rows]
    roll = [float(r[4]) for r in rows]
    rate = [float(r[5]) for r in rows]

    title = "Spending, losses and the charge-off rate — Singapore's card book, 2015 Q1 – 2026 Q2"
    foottext = ("All issuers in Singapore, not one bank · charge-off rate as published: bad debts written off ÷ average rollover balance, annualised\n"
                f"{SRC}")
    assert_fits(title, 12.5, "F1 title", canvas_in)
    assert_fits(foottext, 7.5, "F1 footnote", canvas_in)

    fig, axs = plt.subplots(3, 1, figsize=(canvas_in, 8.6), sharex=True)
    st = fig.suptitle(title, x=0.012, y=0.985, ha="left", fontsize=12.5, color=T["ink"])

    bw = 72  # days per bar (~a quarter with a breath between)

    ax0 = axs[0]
    ax0.bar(xs, bill, width=bw, color=T["petrol"])
    ax0.set_ylim(0, max(bill) * 1.18)
    ax0.set_ylabel("S$M per quarter", fontsize=9)
    ax0.set_title("Total card billings — spending on all cards", fontsize=10, color=T["muted"])
    ax0.annotate(f"{bill[-1]:,.0f}", (xs[-1], bill[-1]), xytext=(6, 2), textcoords="offset points",
                 fontsize=8, color=T["ink"], va="bottom")

    ax1 = axs[1]
    ax1.bar(xs, wo, width=bw, color=T["burnt"])
    ax1.plot(xs, wo4, color=T["ink"], lw=1.8)
    ax1.set_ylim(0, max(wo + [w for w in wo4 if w == w]) * 1.18)
    ax1.set_ylabel("S$M per quarter", fontsize=9)
    ax1.set_title("Bad debts written off — quarterly bars, 4-quarter sum (line)", fontsize=10, color=T["muted"])
    i_peak = wo.index(max(wo))
    is_last = i_peak == len(wo) - 1
    ax1.annotate(f"{'highest' if is_last else 'peak'} {xs[i_peak].year} Q{(xs[i_peak].month - 1) // 3 + 1}: {wo[i_peak]:,.1f}",
                 (xs[i_peak], wo[i_peak]), xytext=(-4, 10), textcoords="offset points", ha="center",
                 fontsize=8, color=T["ink"])
    ax1.annotate(f"4-qtr sum: {wo4[-1]:,.0f}", (xs[-1], wo4[-1]), xytext=(6, -2), textcoords="offset points",
                 fontsize=8, color=T["ink"], va="top")
    if not is_last:
        ax1.annotate(f"{wo[-1]:,.1f}", (xs[-1], wo[-1]), xytext=(6, 1), textcoords="offset points",
                     fontsize=8, color=T["muted"], va="bottom")

    ax2 = axs[2]
    ax2.plot(xs, rate, color=T["petrol"], lw=2.2)
    ax2.set_ylim(2.5, 10.2)
    ax2.set_ylabel("charge-off rate, % annualised", fontsize=9)
    ax2.set_title("Charge-off rate (line, left) — with the rollover balance it is charged on (dashed, right)",
                  fontsize=10, color=T["muted"])
    ax2r = ax2.twinx()
    ax2r.plot(xs, roll, color=T["muted"], lw=1.4, ls="--")
    ax2r.set_ylim(4500, 10600)
    ax2r.set_ylabel("S$M (rollover, quarter-end)", fontsize=9)
    for sp in ax2r.spines.values():
        sp.set_visible(False)
    ax2r.tick_params(axis="y", length=0)
    i_max = rate.index(max(rate))
    ax2.annotate(f"{xs[i_max].year} Q{(xs[i_max].month - 1) // 3 + 1}: {rate[i_max]:.1f}%",
                 (xs[i_max], rate[i_max]), xytext=(0, 9), textcoords="offset points", ha="center",
                 fontsize=8, color=T["ink"])
    ax2.annotate(f"{rate[-1]:.1f}%", (xs[-1], rate[-1]), xytext=(7, -3), textcoords="offset points",
                 fontsize=8, color=T["ink"])

    axs[2].set_xlim(xs[0], mdates.date2num(xs[-1]) + 250)
    axs[2].set_xticks([date(y, 1, 1) for y in range(2016, 2027, 2)])
    axs[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.subplots_adjust(left=0.095, right=0.90, top=0.92, bottom=0.085, hspace=0.34)
    ftxt = foot(fig, foottext)
    assert_clear(fig, [(st, axs[0].title), (ftxt, axs[2].get_xticklabels()[-1])], "F1 suptitle/title + footnote/ticks")
    assert_inbounds(fig, "F1")
    assert_texts_clear(fig, "F1")
    print(f"F1: {len(xs)} quarters plotted · rate {rate[0]:.1f} → {rate[-1]:.1f}% · "
          f"write-offs {wo[0]:,.1f} → {wo[-1]:,.1f} S$M/qtr")
    save(fig, "f1_timeline.png")


def fig2_bridge(con, canvas_in=9.0):
    latest, prev = 2025, 2024
    peak, peak_prev = 2020, 2019
    panels = []
    for new_y, old_y, caption in ((latest, prev, "volume-led"), (peak, peak_prev, "rate-led")):
        old = window_stats(con, year_quarters(old_y))
        new = window_stats(con, year_quarters(new_y))
        panels.append((f"{new_y} vs {old_y}", old, new, split_bridge(old, new), caption))

    title = "Where the change came from — write-offs split into book growth (volume) and the charge-off rate"
    foottext = ("S$M · Δ write-offs = Δrollover × avg rate (volume) + Δrate × avg rollover (rate) — midpoint weights; interaction = 0\n"
                f"2020 = the series peak year · {SRC}")
    assert_fits(title, 12.5, "F2 title", canvas_in)
    assert_fits(foottext, 7.5, "F2 footnote", canvas_in)

    fig, axs = plt.subplots(1, 2, figsize=(canvas_in, 5.0), sharey=True)
    st = fig.suptitle(title, x=0.012, y=0.98, ha="left", fontsize=12.5, color=T["ink"])
    ymax = 0
    for _lbl, old, new, _b, _c in panels:
        ymax = max(ymax, old["w"], new["w"])

    for ax, (lbl, old, new, b, caption) in zip(axs, panels):
        bars = [("start", old["w"], T["ink"]), ("volume", b["volume"], T["petrol"]), ("rate", b["rate"], T["burnt"])]
        xs = [0, 1, 2, 3]
        cum = 0.0
        for i, (name, val, color) in enumerate(bars):
            if name == "start":
                ax.bar(0, abs(val), bottom=0, color=color, width=0.62, zorder=3)
                ax.annotate(f"{lbl.split(' ')[2]}\n{val:,.1f}", (0, val), xytext=(0, 6),
                            textcoords="offset points", ha="center", fontsize=8, color=T["ink"])
                cum = val
            else:
                ax.bar(i, abs(val), bottom=min(cum, cum + val), color=color, width=0.62, zorder=3)
                ax.annotate(f"{val:+.1f}", (i, cum + val), xytext=(0, 7 if val > 0 else -14),
                            textcoords="offset points", ha="center",
                            va=("bottom" if val > 0 else "top"), fontsize=8.5, color=T["ink"])
                if i < 2:
                    ax.plot([i + 0.31, i + 1 - 0.31], [cum + val, cum + val], color=T["light"], lw=0.9, ls="--", zorder=2)
                cum += val
        ax.bar(3, abs(cum), bottom=0, color=T["ink"], width=0.62, zorder=3)
        ax.annotate(f"{lbl.split(' ')[0]}\n{cum:,.1f}", (3, cum), xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=8, color=T["ink"])
        ax.plot([2 + 0.31, 3 - 0.31], [cum, cum], color=T["light"], lw=0.9, ls="--", zorder=2)
        ax.set_xticks(xs)
        ax.set_xticklabels(["start", "volume", "rate", "end"], fontsize=9)
        ax.set_ylim(0, ymax * 1.22)
        ax.xaxis.grid(False)
        ax.set_title(f"{lbl} — {caption}\n+{b['dW']:.1f} S$M = volume {b['volume']:+.1f} + rate {b['rate']:+.1f}",
                     fontsize=10, color=T["muted"])
    axs[0].set_ylabel("write-offs, S$M per year", fontsize=9)
    fig.subplots_adjust(left=0.085, right=0.985, top=0.78, bottom=0.12, wspace=0.12)
    ftxt = foot(fig, foottext)
    assert_clear(fig, [(st, axs[0].title), (ftxt, axs[0].get_xticklabels()[-1])], "F2 suptitle/title + footnote/ticks")
    assert_inbounds(fig, "F2")
    assert_texts_clear(fig, "F2")
    for lbl, old, new, b, caption in panels:
        print(f"F2 [{caption}]: {lbl} Δ {b['dW']:+.1f} = volume {b['volume']:+.1f} + rate {b['rate']:+.1f} S$M")
    save(fig, "f2_bridge.png")


def main():
    import os

    os.chdir(ROOT)
    FIGDIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW quarterly AS SELECT * FROM read_parquet('{PARQUET}')")
    run_script(con, ROOT / "sql/02_metrics.sql")
    for palette in (LIGHT, DARK):
        use_palette(palette)
        use_series_style(dark=(palette is DARK))
        print(f"-- rendering {'dark' if palette['suffix'] else 'light'} set --")
        fig1_timeline(con)
        fig2_bridge(con)
    print("figures done — light + dark")


if __name__ == "__main__":
    main()
