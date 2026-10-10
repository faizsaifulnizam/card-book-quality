"""Figures — code-generated, series style, light + dark (theme-adaptive). Run: python src/figures.py (any cwd).

Produces reports/figures/, and copies every chart + the banners into docs/img/ in the
same run, so the Pages site can never go stale behind a chart regeneration.

  f1_timeline[-dark].png      — four panels, 2015 Q1 – 2026 Q2: billings · write-offs (quarterly) ·
                                trailing-4-quarter write-offs (own panel; full windows only) ·
                                charge-off rate (axis from 0, single scale)
  f2_bridge[-dark].png        — three-panel waterfall, years driven by the data: latest year ·
                                the 2024 step-up · the 2020 peak; bars coloured by sign
  f3_contributions[-dark].png — one stacked bar per year, 2016–2025: each change split into
                                volume + rate (the same bridge as outputs/yearly_bridge.csv)
  f4_book[-dark].png          — three panels: cardholders (principal + supplementary) ·
                                rollover balance · write-offs per principal card

Reads the parquet via DuckDB; re-runs sql/02 so figures always match the SQL. Long titles and
footnotes are width-checked at render size by pixel extent (not eyeballed); annotation overlap,
text clearance and canvas-bounds checks run on every figure.
"""
import csv
import json
import shutil
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
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402

from src.analysis import bridge as split_bridge  # noqa: E402
from src.analysis import book_split, run_script, window_stats, year_quarters  # noqa: E402

PARQUET = (ROOT / "data/processed/quarterly.parquet").as_posix()
PARQUET_SQL = PARQUET.replace("'", "''")
FIGDIR = ROOT / "reports/figures"
DOCS_IMG = ROOT / "docs/img"
ANNUAL_RAW = ROOT / "data/raw/credit-charge-cards-annual.csv"
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


def annual_years(con):
    return [int(r[0]) for r in q(con, "SELECT year FROM annual ORDER BY year")]


def published_annual_rates():
    """Published annual charge-off rates from the (vendored) raw annual file."""
    if not ANNUAL_RAW.exists():
        return {}
    with ANNUAL_RAW.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[0][1:]
    for r in rows[1:]:
        if r[0] == "Charge-Off Rates":
            return {int(y): float(v) for y, v in zip(header, r[1:]) if v.strip() != "na"}
    return {}


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
    dst = DOCS_IMG / p.name
    shutil.copy2(p, dst)  # Pages copy in the same run — docs/img can never go stale
    print(f"wrote {p.as_posix()}  ({p.stat().st_size} bytes) → copied to docs/img/")


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
                            charge_off_rate_pct
                     FROM quarterly_metrics WHERE quarter >= DATE '2015-01-01' ORDER BY quarter""")
    xs = [r[0] for r in rows]
    bill = [float(r[1]) for r in rows]
    wo = [float(r[2]) for r in rows]
    wo4 = [float(r[3]) if r[3] is not None else float("nan") for r in rows]
    rate = [float(r[4]) for r in rows]
    first_full = next(i for i, v in enumerate(wo4) if v == v)
    # the file starts 2014 Q4; the plot starts 2015 Q1, so the first full window is 2015 Q3 (index 2)
    assert first_full == 2, f"trailing-4 window must start at 2015 Q3 (got index {first_full})"
    print(f"   [PASS] trailing-4 sum is null for the first {first_full} plotted quarters (no partial windows plotted)")

    title = "Spending, losses and the charge-off rate — Singapore's card book, 2015 Q1 – 2026 Q2"
    foottext = ("All issuers in Singapore, not one bank · published rate: source percentage; publisher averaging/write-off treatment unverified\n"
                f"{SRC}")
    assert_fits(title, 12.5, "F1 title", canvas_in)
    assert_fits(foottext, 7.5, "F1 footnote", canvas_in)

    fig, axs = plt.subplots(4, 1, figsize=(canvas_in, 10.8), sharex=True)
    st = fig.suptitle(title, x=0.012, y=0.988, ha="left", fontsize=12.5, color=T["ink"])

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
    ax1.set_ylim(0, max(wo) * 1.18)
    ax1.set_ylabel("S$M per quarter", fontsize=9)
    ax1.set_title("Bad debts written off — quarterly", fontsize=10, color=T["muted"])
    i_peak = wo.index(max(wo))
    is_last = i_peak == len(wo) - 1
    ax1.annotate(f"{'highest' if is_last else 'peak'} {xs[i_peak].year} Q{(xs[i_peak].month - 1) // 3 + 1}: {wo[i_peak]:,.1f}",
                 (xs[i_peak], wo[i_peak]), xytext=(-4, 10), textcoords="offset points", ha="center",
                 fontsize=8, color=T["ink"])

    ax2 = axs[2]
    ax2.plot(xs, wo4, color=T["ink"], lw=1.8)
    ax2.set_ylim(0, max(w for w in wo4 if w == w) * 1.18)
    ax2.set_ylabel("S$M, trailing 4 quarters", fontsize=9)
    ax2.set_title("Write-offs, trailing 4-quarter sum — starts once four quarters exist (no partial windows)",
                  fontsize=10, color=T["muted"])
    ax2.annotate(f"{wo4[-1]:,.0f}", (xs[-1], wo4[-1]), xytext=(6, -2), textcoords="offset points",
                 fontsize=8, color=T["ink"], va="top")

    ax3 = axs[3]
    ax3.plot(xs, rate, color=T["petrol"], lw=2.2)
    ax3.set_ylim(0, 10.5)
    ax3.set_ylabel("charge-off rate, % annualised", fontsize=9)
    ax3.set_title("Charge-off rate (as published) — after the 2024 step-up it sits near 5.9–6.0%",
                  fontsize=10, color=T["muted"])
    i_max = rate.index(max(rate))
    ax3.annotate(f"{xs[i_max].year} Q{(xs[i_max].month - 1) // 3 + 1}: {rate[i_max]:.1f}%",
                 (xs[i_max], rate[i_max]), xytext=(0, 9), textcoords="offset points", ha="center",
                 fontsize=8, color=T["ink"])
    ax3.annotate(f"{rate[-1]:.1f}%", (xs[-1], rate[-1]), xytext=(7, -3), textcoords="offset points",
                 fontsize=8, color=T["ink"])

    axs[3].set_xlim(mdates.date2num(xs[0]) - bw / 2,
                    mdates.date2num(xs[-1]) + 250)
    axs[3].set_xticks([date(y, 1, 1) for y in range(2016, 2027, 2)])
    axs[3].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.subplots_adjust(left=0.105, right=0.90, top=0.935, bottom=0.075, hspace=0.34)
    ftxt = foot(fig, foottext)
    assert_clear(fig, [(st, axs[0]._left_title), (ftxt, axs[3].get_xticklabels()[-1])], "F1 suptitle/title + footnote/ticks")
    assert_inbounds(fig, "F1")
    assert_texts_clear(fig, "F1")
    print(f"F1: {len(xs)} quarters plotted · rate {rate[0]:.1f} → {rate[-1]:.1f}% · "
          f"write-offs {wo[0]:,.1f} → {wo[-1]:,.1f} S$M/qtr · trailing-4 {wo4[-1]:,.1f} S$M")
    save(fig, "f1_timeline.png")


def _panel_years(con):
    """(latest, peak, pairs) from the data — nothing hard-coded."""
    years = annual_years(con)
    pub = published_annual_rates()
    latest = years[-1]
    overlap = [y for y in years if y in pub]
    proxy = dict(q(con, "SELECT year, rate_pct_recomputed FROM annual"))
    peak = max(overlap, key=pub.get) if overlap else max(years, key=proxy.get)
    pairs, seen = [], set()
    for y in (latest, latest - 1, peak):
        if y - 1 in years and (y, y - 1) not in seen:
            seen.add((y, y - 1))
            pairs.append((y, y - 1))
    return latest, peak, pairs


def fig2_bridge(con, canvas_in=9.0):
    _latest, peak, pairs = _panel_years(con)
    panels = []
    for y_new, y_old in pairs:
        old = window_stats(con, year_quarters(y_old))
        new = window_stats(con, year_quarters(y_new))
        b = split_bridge(old, new)
        shape = "rate-led" if abs(b["rate"]) > abs(b["volume"]) else "volume-led"
        panels.append((y_new, y_old, old, new, b, shape))

    peak_rate = published_annual_rates().get(peak)
    peak_basis = f"{peak_rate:.1f}% published annual" if peak_rate is not None else "recomputed proxy ratio"
    title = "Where the change came from — write-offs split into rollover balance and the proxy loss ratio"
    foottext = ("S$M · midpoint split: Δrollover × average proxy ratio + Δratio × average rollover\n"
                "Positive volume = blue; positive ratio = orange; negative volume = grey; negative ratio = violet\n"
                f"{peak} = peak among available annual-rate years ({peak_basis}) · {SRC}")
    assert_fits(title, 12.5, "F2 title", canvas_in)
    assert_fits(foottext, 7.5, "F2 footnote", canvas_in)

    fig, axs = plt.subplots(1, len(panels), figsize=(canvas_in, 5.0), sharey=True)
    if len(panels) == 1:
        axs = [axs]
    st = fig.suptitle(title, x=0.012, y=0.98, ha="left", fontsize=12.5, color=T["ink"])
    ymax = max(max(old["w"], new["w"]) for _y_new, _y_old, old, new, _b, _shape in panels)

    for ax, (y_new, y_old, old, new, b, shape) in zip(axs, panels):
        bars = [("start", old["w"], T["ink"], T["ink"]),
                ("volume", b["volume"], T["petrol"], T["muted"]),
                ("rate", b["rate"], T["burnt"], T["violet"])]
        cum = 0.0
        for i, (name, val, col_pos, col_neg) in enumerate(bars):
            color = col_pos if val >= 0 else col_neg
            if name == "start":
                ax.bar(0, abs(val), bottom=0, color=color, width=0.62, zorder=3)
                ax.annotate(f"{y_old}\n{val:,.1f}", (0, val), xytext=(0, 6),
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
        ax.annotate(f"{y_new}\n{cum:,.1f}", (3, cum), xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=8, color=T["ink"])
        ax.plot([2 + 0.31, 3 - 0.31], [cum, cum], color=T["light"], lw=0.9, ls="--", zorder=2)
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels(["start", "volume", "rate", "end"], fontsize=9)
        ax.set_ylim(0, ymax * 1.22)
        ax.xaxis.grid(False)
        extra = " · series peak" if y_new == peak else ""
        ax.set_title(f"{y_new} vs {y_old} — {shape}{extra}\n{b['dW']:+.1f} S$M = volume {b['volume']:+.1f} + rate {b['rate']:+.1f}",
                     fontsize=10, color=T["muted"])
    axs[0].set_ylabel("write-offs, S$M per year", fontsize=9)
    fig.subplots_adjust(left=0.085, right=0.985, top=0.78, bottom=0.18, wspace=0.12)
    ftxt = foot(fig, foottext)
    assert_clear(fig, [(st, axs[0]._left_title), (ftxt, axs[0].get_xticklabels()[-1])], "F2 suptitle/title + footnote/ticks")
    assert_inbounds(fig, "F2")
    assert_texts_clear(fig, "F2")
    for y_new, y_old, _old, _new, b, shape in panels:
        print(f"F2 [{shape}]: {y_new} vs {y_old} Δ {b['dW']:+.1f} = volume {b['volume']:+.1f} + rate {b['rate']:+.1f} S$M")
    save(fig, "f2_bridge.png")


def fig3_contributions(con, canvas_in=9.0):
    """One stacked bar per year: each year's change in write-offs split into volume + rate."""
    years = annual_years(con)
    data = []
    for y in years[1:]:
        old = window_stats(con, year_quarters(y - 1))
        new = window_stats(con, year_quarters(y))
        data.append((y, split_bridge(old, new)))

    title = f"Annual write-off changes split into rollover balance and the proxy loss ratio, {data[0][0]}–{data[-1][0]}"
    foottext = ("Midpoint split: volume = Δrollover × average proxy ratio · ratio = Δratio × average rollover · labels = net change (S$M)\n"
                f"Negative contributions reduce write-offs (grey: volume; violet: ratio) · {SRC}")
    assert_fits(title, 12.5, "F3 title", canvas_in)
    assert_fits(foottext, 7.5, "F3 footnote", canvas_in)

    fig, ax = plt.subplots(figsize=(canvas_in, 4.8))
    st = fig.suptitle(title, x=0.012, y=0.975, ha="left", fontsize=12.5, color=T["ink"])
    lo, hi = 0.0, 0.0
    for y, b in data:
        pos_c, neg_c = 0.0, 0.0
        for val, col_pos, col_neg in ((b["volume"], T["petrol"], T["muted"]),
                                      (b["rate"], T["burnt"], T["violet"])):
            if val >= 0:
                ax.bar(y, val, bottom=pos_c, width=0.62, color=col_pos, zorder=3)
                pos_c += val
            else:
                ax.bar(y, val, bottom=neg_c, width=0.62, color=col_neg, zorder=3)
                neg_c += val
        hi, lo = max(hi, pos_c), min(lo, neg_c)
        top = pos_c if b["dW"] >= 0 else neg_c
        ax.annotate(f"{b['dW']:+.0f}", (y, top), xytext=(0, 7 if b["dW"] >= 0 else -13),
                    textcoords="offset points", ha="center",
                    va="bottom" if b["dW"] >= 0 else "top", fontsize=7.5, color=T["muted"])
    ax.axhline(0, color=T["light"], lw=1)
    ax.set_xticks([y for y, _ in data])
    ax.set_xticklabels([str(y) for y, _ in data], fontsize=9)
    ax.set_ylim(lo * 1.28, hi * 1.22)
    ax.set_ylabel("contribution to Δ write-offs, S$M", fontsize=9)
    ax.legend(handles=[Patch(color=T["petrol"], label="volume (positive)"),
                       Patch(color=T["burnt"], label="ratio (positive)"),
                       Patch(color=T["muted"], label="volume (negative)"),
                       Patch(color=T["violet"], label="ratio (negative)")],
              loc="best", fontsize=8.5)
    fig.subplots_adjust(left=0.095, right=0.985, top=0.80, bottom=0.14)
    ftxt = foot(fig, foottext)
    assert_clear(fig, [(st, ax.get_xticklabels()[-1])], "F3 suptitle + last tick")
    assert_inbounds(fig, "F3")
    assert_texts_clear(fig, "F3")
    for y, b in data:
        print(f"F3 {y}: Δ {b['dW']:+7.1f} = volume {b['volume']:+7.1f} + rate {b['rate']:+7.1f} S$M")
    save(fig, "f3_contributions.png")


def fig4_book(con, canvas_in=9.0):
    rows = q(con, """SELECT quarter, principal_cardholders, supplementary_cardholders, rollover_sgd_m
                     FROM quarterly WHERE quarter >= DATE '2015-01-01' ORDER BY quarter""")
    xs = [r[0] for r in rows]
    prin = [float(r[1]) / 1e6 for r in rows]
    supp = [float(r[2]) / 1e6 for r in rows]
    roll = [float(r[3]) for r in rows]
    yr = q(con, """SELECT year(quarter) AS y, sum(write_offs_sgd_m) * 1e6 / avg(principal_cardholders)
                   FROM quarterly GROUP BY 1 HAVING count(*) = 4 ORDER BY 1""")
    ys = [int(r[0]) for r in yr]
    wpc = [float(r[1]) for r in yr]

    title = "Card counts, revolving balances, and annual write-offs per principal card"
    supp_avg = q(con, "SELECT year(quarter), avg(supplementary_cardholders) FROM quarterly GROUP BY 1 HAVING count(*) = 4 ORDER BY 1")
    supp_change = (supp_avg[-1][1] / supp_avg[0][1] - 1) * 100
    ib = xs.index(date(2025, 7, 1))
    break_pct = (prin[ib] / prin[ib - 1] - 1) * 100
    foottext = ("Cards and rollover lines: quarter-end observations · annual bars: annual write-offs ÷ average quarter-end principal count\n"
                f"2025 Q2 → Q3 principal-count break ({break_pct:+.1f}%) flagged, not explained · counts are not unique customers\n"
                f"{SRC}")
    assert_fits(title, 12.5, "F4 title", canvas_in)
    assert_fits(foottext, 7.5, "F4 footnote", canvas_in)

    fig, axs = plt.subplots(3, 1, figsize=(canvas_in, 8.8), sharex=True)
    st = fig.suptitle(title, x=0.012, y=0.985, ha="left", fontsize=12.5, color=T["ink"])

    ax0 = axs[0]
    ax0.plot(xs, prin, color=T["petrol"], lw=2.0, label="principal")
    ax0.plot(xs, supp, color=T["teal"], lw=2.0, ls="--", label="supplementary")
    ax0.set_ylim(0, 7.4)
    ax0.set_ylabel("millions of cards", fontsize=9)
    ax0.set_title(f"Card counts — supplementary {supp_change:+.0f}% ({supp_avg[0][0]}–{supp_avg[-1][0]} annual averages)",
                  fontsize=10, color=T["muted"])
    ax0.legend(loc="best", fontsize=8.5)
    ax0.annotate(f"2025 Q2 → Q3: {prin[ib - 1]:.2f}M → {prin[ib]:.2f}M ({break_pct:+.1f}%) — flagged",
                 (xs[ib], prin[ib]), xytext=(-10, 16), textcoords="offset points", ha="right",
                 fontsize=8, color=T["ink"])

    ax1 = axs[1]
    ax1.plot(xs, roll, color=T["petrol"], lw=2.0)
    ax1.set_ylim(0, 11200)
    ax1.set_ylabel("S$M, quarter-end", fontsize=9)
    ax1.set_title("Rollover balance — revolving balance used as the charge-off-ratio denominator",
                  fontsize=10, color=T["muted"])
    split = book_split(con)[-1]
    ax1.text(0.012, 0.94,
             f"{split['year']} annual-average Δrollover {split['delta_rollover_sgd_m']:+,.0f} S$M: total-card count {split['cards_effect_sgd_m']:+,.0f} + per-card {split['balance_per_card_effect_sgd_m']:+,.0f}\n"
             f"principal-only: count {split['principal_cards_effect_sgd_m']:+,.0f} + per-principal {split['balance_per_principal_card_effect_sgd_m']:+,.0f} S$M (denominator-sensitive)",
             transform=ax1.transAxes, fontsize=8, color=T["muted"], va="top",
             bbox=dict(facecolor=ax1.get_facecolor(), edgecolor="none", pad=2))
    ax1.annotate(f"{roll[-1]:,.0f}", (xs[-1], roll[-1]), xytext=(6, -2), textcoords="offset points",
                 fontsize=8, color=T["ink"], va="top")

    ax2 = axs[2]
    ax2.bar([date(y, 7, 1) for y in ys], wpc, width=300, color=T["burnt"])
    ax2.set_ylim(0, max(wpc) * 1.22)
    ax2.set_ylabel("S$ per principal card", fontsize=9)
    wpc_change = (wpc[-1] / wpc[-2] - 1) * 100
    ax2.set_title(f"Annual write-offs per principal card — {wpc[-2]:.1f} → {wpc[-1]:.1f} ({wpc_change:+.1f}%), {ys[-2]} → {ys[-1]}",
                  fontsize=10, color=T["muted"])
    ax2.annotate(f"{wpc[-1]:,.0f}", (date(ys[-1], 7, 1), wpc[-1]), xytext=(0, 6), textcoords="offset points",
                 ha="center", fontsize=8, color=T["ink"])

    axs[2].set_xlim(xs[0], mdates.date2num(xs[-1]) + 250)
    axs[2].set_xticks([date(y, 1, 1) for y in range(2016, 2027, 2)])
    axs[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.subplots_adjust(left=0.095, right=0.90, top=0.90, bottom=0.12, hspace=0.42)
    ftxt = foot(fig, foottext)
    assert_clear(fig, [(st, axs[0]._left_title), (ftxt, axs[2].get_xticklabels()[-1])], "F4 suptitle/title + footnote/ticks")
    assert_inbounds(fig, "F4")
    assert_texts_clear(fig, "F4")
    print(f"F4: cards {prin[-1]:.2f}M principal / {supp[-1]:.2f}M supplementary · rollover {roll[0]:,.0f} → {roll[-1]:,.0f} S$M "
          f"· write-offs per principal card {wpc[0]:,.0f} → {wpc[-1]:,.0f} S$")
    save(fig, "f4_book.png")


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    DOCS_IMG.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW quarterly AS SELECT * FROM read_parquet('{PARQUET_SQL}')")
    run_script(con, ROOT / "sql/02_metrics.sql")
    for palette in (LIGHT, DARK):
        use_palette(palette)
        use_series_style(dark=(palette is DARK))
        print(f"-- rendering {'dark' if palette['suffix'] else 'light'} set --")
        fig1_timeline(con)
        fig2_bridge(con)
        fig3_contributions(con)
        fig4_book(con)
    for name in ("banner.svg", "banner-dark.svg"):
        src = ROOT / "assets" / name
        if src.exists():
            shutil.copy2(src, DOCS_IMG / name)
            print(f"synced {name} → docs/img/")
    print("figures done — light + dark; docs/img/ synced")


if __name__ == "__main__":
    main()
