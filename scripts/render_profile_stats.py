import html
import json
from datetime import date, timedelta
from pathlib import Path


DATA_FILE = Path("data/contributions.json")
HEATMAP_FILE = Path("contrib-heatmap.svg")
STATS_FILE = Path("stats.svg")
PALETTE = ("#161B22", "#0E4429", "#006D32", "#26A641", "#39D353", "#69F0A0")


def load_days() -> list[dict[str, int | str]]:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    days = data.get("days")
    if not isinstance(days, list) or not days:
        raise ValueError(f"No contribution days found in {DATA_FILE}")
    return days


def contribution_stats(days: list[dict[str, int | str]]) -> dict[str, int | str]:
    counts = {
        date.fromisoformat(str(day["date"])): int(day["count"])
        for day in days
    }
    total = sum(counts.values())
    active_days = sum(count > 0 for count in counts.values())
    today = date.today()
    start = today if counts.get(today, 0) else today - timedelta(days=1)

    current_streak = 0
    cursor = start
    while counts.get(cursor, 0) > 0:
        current_streak += 1
        cursor -= timedelta(days=1)

    peak_day, peak_count = max(counts.items(), key=lambda item: item[1])

    return {
        "total": total,
        "active_days": active_days,
        "current_streak": current_streak,
        "peak_day": (
            f"{peak_count} on "
            f"{peak_day.strftime('%b %d, %Y').replace(' 0', ' ')}"
        ),
    }


def render_heatmap(days: list[dict[str, int | str]], total: int) -> str:
    parsed = [
        (date.fromisoformat(str(day["date"])), int(day["count"]), int(day["level"]))
        for day in days
    ]
    first_day = min(day for day, _, _ in parsed)
    last_day = max(day for day, _, _ in parsed)
    calendar_start = first_day - timedelta(days=(first_day.weekday() + 1) % 7)
    columns = ((last_day - calendar_start).days // 7) + 1
    cell = 11
    gap = 4
    left = 48
    top = 29
    width = left + columns * (cell + gap) + 18
    height = top + 7 * (cell + gap) + 31

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">',
        "<title id=\"title\">Ajay Varsan's GitHub contributions</title>",
        f'<desc id="description">{total:,} contributions in the last year.</desc>',
        '<rect width="100%" height="100%" rx="12" fill="#0A192F" />',
        '<g fill="#C9D1D9" font-family="Arial, sans-serif" font-size="11">',
        '<text x="4" y="41">Mon</text><text x="4" y="71">Wed</text>'
        '<text x="4" y="101">Fri</text></g>',
    ]

    month_labels: set[tuple[int, int]] = set()
    for current, count, level in parsed:
        offset = (current - calendar_start).days
        column = offset // 7
        row = (current.weekday() + 1) % 7
        x = left + column * (cell + gap)
        y = top + row * (cell + gap)
        if current.day <= 7 and (current.year, current.month) not in month_labels:
            month_labels.add((current.year, current.month))
            label = html.escape(current.strftime("%b"))
            parts.append(
                f'<text x="{x}" y="17" fill="#C9D1D9" '
                f'font-family="Arial, sans-serif" font-size="11">{label}</text>'
            )
        delay = (column + row) * 0.012
        parts.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
            f'fill="{PALETTE[min(max(level, 0), len(PALETTE) - 1)]}" '
            f'data-date="{current.isoformat()}" data-count="{count}" opacity="1">'
            f'<title>{count} contributions on {current.isoformat()}</title>'
            f'<animate attributeName="opacity" values="0;1" begin="{delay:.3f}s" '
            'dur="0.22s" fill="freeze" /></rect>'
        )

    footer_y = height - 12
    parts.extend(
        [
            f'<text x="{left}" y="{footer_y}" fill="#C9D1D9" '
            f'font-family="Arial, sans-serif" font-size="11">{total:,} contributions in the last year</text>',
            '<g fill="#C9D1D9" font-family="Arial, sans-serif" font-size="10">'
            f'<text x="{width - 166}" y="{footer_y}">Less</text>',
        ]
    )
    legend_x = width - 135
    for index, color in enumerate(PALETTE):
        parts.append(
            f'<rect x="{legend_x + index * 14}" y="{footer_y - 9}" width="10" '
            f'height="10" rx="2" fill="{color}" />'
        )
    parts.append(f'<text x="{width - 41}" y="{footer_y}">More</text></g></svg>')
    return "".join(parts)


def render_stats(stats: dict[str, int | str]) -> str:
    rows = [
        ("TOTAL CONTRIBUTIONS (ALL TIME)", f"{stats['total']:,}"),
        (
            "CURRENT STREAK",
            f"{stats['current_streak']} "
            f"day{'s' if stats['current_streak'] != 1 else ''}",
        ),
        ("TOP CONTRIBUTION DAY", str(stats["peak_day"])),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="420" '
        'viewBox="0 0 420 420" role="img" aria-labelledby="title description">',
        "<title id=\"title\">Ajay Varsan's GitHub contribution stats</title>",
        '<desc id="description">All-time contributions, current streak, and top contribution day.</desc>',
        '<rect width="420" height="420" rx="12" fill="#0A192F" stroke="#1F3A5F" />',
        '<text x="30" y="54" fill="#69F0A0" font-family="Consolas, monospace" '
        'font-size="19" font-weight="bold">ajay@github ~ $ whoami</text>',
        '<text x="30" y="91" fill="#D1D5DB" font-family="Arial, sans-serif" '
        'font-size="16">AI / ML Engineer | Full-stack Developer</text>',
        '<text x="30" y="119" fill="#8B949E" font-family="Arial, sans-serif" '
        'font-size="13">Python · React · TypeScript · Node.js</text>',
        '<line x1="30" y1="146" x2="390" y2="146" stroke="#1F3A5F" />',
    ]
    for index, (label, value) in enumerate(rows):
        y = 190 + index * 72
        delay = index * 0.16
        parts.append(
            f'<g opacity="1"><text x="30" y="{y}" fill="#8B949E" '
            f'font-family="Arial, sans-serif" font-size="12">{html.escape(label)}</text>'
            f'<text x="30" y="{y + 27}" fill="#D1D5DB" '
            f'font-family="Consolas, monospace" font-size="20" font-weight="bold">'
            f'{html.escape(value)}</text>'
            f'<animate attributeName="opacity" values="0;1" begin="{delay:.2f}s" '
            'dur="0.25s" fill="freeze" /></g>'
        )
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    days = load_days()
    stats = contribution_stats(days)
    cutoff = date.today() - timedelta(days=364)
    heatmap_days = [
        day
        for day in days
        if date.fromisoformat(str(day["date"])) >= cutoff
    ]
    heatmap_total = sum(int(day["count"]) for day in heatmap_days)
    if not heatmap_days:
        raise ValueError("No contribution days available for the last-year heatmap")
    HEATMAP_FILE.write_text(
        render_heatmap(heatmap_days, heatmap_total), encoding="utf-8"
    )
    STATS_FILE.write_text(render_stats(stats), encoding="utf-8")
    print(f"Rendered {HEATMAP_FILE} and {STATS_FILE}")


if __name__ == "__main__":
    main()
