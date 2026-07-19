"""Render the price-trend chart: one muted line per depart date
(cheapest total for that departure each day) plus a bold line for the
overall cheapest total each day."""
from collections import defaultdict
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# Categorical slots 1-5 (light mode) from the validated reference palette
SERIES_COLORS = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

MAX_DEPART_LINES = 5


def render(rows: list[dict], out_path: str) -> bool:
    """Render history rows for one route to out_path. Returns False if
    there is nothing to plot."""
    if not rows:
        return False

    # min total per (run_date, depart) and per run_date
    per_depart = defaultdict(dict)  # depart -> {run_date: min_total}
    overall = {}  # run_date -> min_total
    for r in rows:
        run, depart, total = r["run_date"], r["depart"], float(r["total"])
        cur = per_depart[depart].get(run)
        per_depart[depart][run] = total if cur is None else min(cur, total)
        cur = overall.get(run)
        overall[run] = total if cur is None else min(cur, total)

    currency = rows[-1]["currency"]
    start, end = rows[-1]["start"], rows[-1]["end"]

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    def dates_values(series: dict):
        runs = sorted(series)
        return [datetime.strptime(d, "%Y-%m-%d") for d in runs], [series[d] for d in runs]

    for i, depart in enumerate(sorted(per_depart)[:MAX_DEPART_LINES]):
        x, y = dates_values(per_depart[depart])
        day = datetime.strptime(depart, "%Y-%m-%d").strftime("%b %d")
        ax.plot(
            x, y,
            color=SERIES_COLORS[i % len(SERIES_COLORS)],
            linewidth=1.4, alpha=0.65,
            marker="o", markersize=3.5,
            label=f"Depart {day}",
        )

    x, y = dates_values(overall)
    ax.plot(
        x, y,
        color=INK, linewidth=2.5,
        marker="o", markersize=5,
        label="Cheapest overall",
    )
    # Direct-label the latest overall point
    ax.annotate(
        f"{currency} {y[-1]:g}",
        (x[-1], y[-1]),
        textcoords="offset points", xytext=(8, -3),
        fontsize=9, fontweight="bold", color=INK,
    )

    ax.set_title(f"{start} ⇄ {end} — cheapest round-trip total per day", color=INK, fontsize=11)
    ax.set_ylabel(f"Price ({currency})", color=MUTED, fontsize=9)
    ax.grid(True, axis="y", color=GRID, linewidth=0.7)
    ax.tick_params(colors=MUTED, labelsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASELINE)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
    legend = ax.legend(fontsize=8, frameon=False, labelcolor=INK)

    fig.tight_layout()
    fig.savefig(out_path, facecolor=SURFACE)
    plt.close(fig)
    return True
