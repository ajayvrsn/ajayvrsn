import html
import json
import random
from datetime import date, timedelta
from pathlib import Path


DATA_FILE = Path("data/contributions.json")
HEATMAP_FILE = Path("contrib-heatmap.svg")
PACMAN_FILE = Path("pacman-contribution-graph.svg")
STATS_FILE = Path("stats.svg")
PALETTE = ("#161B22", "#0E4429", "#006D32", "#26A641", "#39D353", "#69F0A0")


def load_days() -> list[dict[str, int | str]]:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    days = data.get("days")
    if not isinstance(days, list) or not days:
        raise ValueError(f"No contribution days found in {DATA_FILE}")
    return days


def render_heatmap(
    days: list[dict[str, int | str]], total: int, pacman: bool = False
) -> str:
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
        (
            "<title id=\"title\">Ajay Varsan's Pac-Man contribution graph</title>"
            if pacman
            else "<title id=\"title\">Ajay Varsan's GitHub contributions</title>"
        ),
        (
            f'<desc id="description">{total:,} contributions in the last year, '
            'with Pac-Man chased through a maze by four ghosts.</desc>'
            if pacman
            else f'<desc id="description">{total:,} contributions in the last year.</desc>'
        ),
        '<rect width="100%" height="100%" rx="12" fill="#0A192F" />',
        '<g fill="#C9D1D9" font-family="Arial, sans-serif" font-size="11">',
        '<text x="4" y="41">Mon</text><text x="4" y="71">Wed</text>'
        '<text x="4" y="101">Fri</text></g>',
    ]

    month_labels: set[tuple[int, int]] = set()
    contribution_pellets = []
    for current, count, level in parsed:
        offset = (current - calendar_start).days
        column = offset // 7
        row = (current.weekday() + 1) % 7
        x = left + column * (cell + gap)
        y = top + row * (cell + gap)
        if pacman and count > 0:
            contribution_pellets.append((column, row, current, count))
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
    if pacman:
        rows = 7
        nodes = [(column, row) for row in range(rows) for column in range(columns)]
        adjacency = {node: [] for node in nodes}
        open_edges: set[frozenset[tuple[int, int]]] = set()
        visited = {(0, 0)}
        stack = [(0, 0)]
        maze_random = random.Random(42)
        while stack:
            column, row = stack[-1]
            choices = [
                neighbor
                for neighbor in (
                    (column - 1, row),
                    (column + 1, row),
                    (column, row - 1),
                    (column, row + 1),
                )
                if neighbor in adjacency and neighbor not in visited
            ]
            if not choices:
                stack.pop()
                continue
            neighbor = maze_random.choice(choices)
            edge = frozenset(((column, row), neighbor))
            open_edges.add(edge)
            adjacency[(column, row)].append(neighbor)
            adjacency[neighbor].append((column, row))
            visited.add(neighbor)
            stack.append(neighbor)

        route_nodes: list[tuple[int, int]] = []

        def walk_maze(node: tuple[int, int], parent: tuple[int, int] | None) -> None:
            route_nodes.append(node)
            for neighbor in adjacency[node]:
                if neighbor == parent:
                    continue
                walk_maze(neighbor, node)
                route_nodes.append(node)

        walk_maze((0, 0), None)
        route_nodes.pop()
        route_indices: dict[tuple[int, int], int] = {}
        for index, node in enumerate(route_nodes):
            route_indices.setdefault(node, index)

        def route_from(offset: int) -> str:
            route = route_nodes[offset:] + route_nodes[:offset]
            route.append(route[0])
            points = [
                (
                    left + column * (cell + gap) + cell / 2,
                    top + row * (cell + gap) + cell / 2,
                )
                for column, row in route
            ]
            return "M" + " L".join(f"{x:g} {y:g}" for x, y in points)

        outer_width = (columns - 1) * (cell + gap) + cell
        wall_segments = []
        for column, row in nodes:
            if column + 1 < columns and frozenset(
                ((column, row), (column + 1, row))
            ) not in open_edges:
                x = left + column * (cell + gap) + cell + gap / 2
                y = top + row * (cell + gap)
                wall_segments.append(f"M{x:g} {y} v{cell}")
            if row + 1 < rows and frozenset(
                ((column, row), (column, row + 1))
            ) not in open_edges:
                x = left + column * (cell + gap)
                y = top + row * (cell + gap) + cell + gap / 2
                wall_segments.append(f"M{x} {y:g} h{cell}")

        parts.append(
            f'<rect x="{left - 2}" y="{top - 2}" '
            f'width="{outer_width + 4}" height="{rows * (cell + gap) - gap + 4}" '
            'fill="none" stroke="#65A7FF" stroke-width="2" />'
        )
        parts.append(
            f'<path d="{" ".join(wall_segments)}" fill="none" '
            'stroke="#65A7FF" stroke-width="2" stroke-linecap="round" />'
        )
        lap_duration = 90
        for column, row, current, count in contribution_pellets:
            node = (column, row)
            visit = route_indices[node] / len(route_nodes)
            visit = min(max(visit, 0.001), 0.996)
            fade_end = visit + 0.001
            x = left + column * (cell + gap) + cell / 2
            y = top + row * (cell + gap) + cell / 2
            parts.append(
                f'<circle cx="{x:g}" cy="{y:g}" r="2.2" fill="#B8FF75" '
                f'data-pellet-date="{current.isoformat()}" data-count="{count}">'
                f'<title>{count} contributions on {current.isoformat()}</title>'
                '<animate attributeName="opacity" values="1;1;0;0;1" '
                f'keyTimes="0;{visit:.6f};{fade_end:.6f};0.999;1" '
                f'dur="{lap_duration}s" repeatCount="indefinite" />'
                '</circle>'
            )
        parts.append(
            '<g fill="#FFD84D"><path d="M0 0 L4 -3.2 A5.5 5.5 0 1 1 4 3.2 Z" />'
            f'<animateMotion dur="{lap_duration}s" rotate="auto" repeatCount="indefinite" '
            f'path="{route_from(0)}" /></g>'
        )
        ghost_colors = ("#FF5B63", "#FF9DE2", "#4DE1E8", "#FFAA45")
        ghost_starts = tuple(len(route_nodes) * percent // 100 for percent in (92, 94, 96, 98))
        ghost_durations = ("88s", "86s", "84s", "82s")
        ghost_shape = (
            '<path d="M-11 10 V0 A11 11 0 0 1 11 0 V10 L6 6 L1 10 '
            'L-4 6 Z" />'
            '<g fill="#FFFFFF"><circle cx="-4" cy="-1" r="3.5" />'
            '<circle cx="4" cy="-1" r="3.5" /></g>'
            '<g fill="#172554"><circle cx="-3" cy="0" r="1.5" />'
            '<circle cx="5" cy="0" r="1.5" /></g>'
        )
        for color, start_index, duration in zip(
            ghost_colors, ghost_starts, ghost_durations
        ):
            parts.append(
                f'<g><g transform="scale(0.48)" fill="{color}">{ghost_shape}</g>'
                f'<animateMotion dur="{duration}" rotate="auto" '
                f'repeatCount="indefinite" path="{route_from(start_index)}" />'
                '</g>'
            )
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


def render_profile_card() -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="420" '
        'viewBox="0 0 420 420" role="img" aria-labelledby="title description">',
        "<title id=\"title\">About Ajay Varsan</title>",
        '<desc id="description">AI and full-stack developer building practical software and exploring AI-powered tools.</desc>',
        '<rect width="420" height="420" rx="12" fill="#0A192F" stroke="#1F3A5F" />',
        '<text x="30" y="54" fill="#69F0A0" font-family="Consolas, monospace" '
        'font-size="19" font-weight="bold">ajay@github ~ $ whoami</text>',
        '<text x="30" y="91" fill="#D1D5DB" font-family="Arial, sans-serif" '
        'font-size="16">AI / ML Engineer | Full-stack Developer</text>',
        '<line x1="30" y1="121" x2="390" y2="121" stroke="#1F3A5F" />',
        '<text x="30" y="157" fill="#69F0A0" font-family="Arial, sans-serif" '
        'font-size="12" font-weight="bold">WHAT I BUILD</text>',
        '<text x="30" y="183" fill="#D1D5DB" font-family="Arial, sans-serif" '
        'font-size="14">Practical software, from AI-powered apps to</text>',
        '<text x="30" y="205" fill="#D1D5DB" font-family="Arial, sans-serif" '
        'font-size="14">full-stack products and developer tools.</text>',
        '<text x="30" y="251" fill="#69F0A0" font-family="Arial, sans-serif" '
        'font-size="12" font-weight="bold">CURRENT CURIOSITIES</text>',
        '<text x="30" y="277" fill="#D1D5DB" font-family="Arial, sans-serif" '
        'font-size="14">Generative AI · RAG · thoughtful product design</text>',
        '<text x="30" y="323" fill="#69F0A0" font-family="Arial, sans-serif" '
        'font-size="12" font-weight="bold">HOW I LEARN</text>',
        '<text x="30" y="349" fill="#D1D5DB" font-family="Arial, sans-serif" '
        'font-size="14">By experimenting, solving real problems, and</text>',
        '<text x="30" y="371" fill="#D1D5DB" font-family="Arial, sans-serif" '
        'font-size="14">sharing what I discover along the way.</text>',
    ]
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    days = load_days()
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
    PACMAN_FILE.write_text(
        render_heatmap(heatmap_days, heatmap_total, pacman=True), encoding="utf-8"
    )
    STATS_FILE.write_text(render_profile_card(), encoding="utf-8")
    print(f"Rendered {HEATMAP_FILE}, {PACMAN_FILE}, and {STATS_FILE}")


if __name__ == "__main__":
    main()
