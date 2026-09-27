"""Draw the contribution snake: the last year of real contributions (53 weeks,
like GitHub's own graph) and an orange snake that crawls in, eats every active
day and leaves again; the eaten days grow back before the next round.

Pure SVG + SMIL, so it animates inside a README <img>.
Usage: python scripts/snake.py dist        (DEMO=1 uses random data)
"""
import os
import random
import re
import sys
import urllib.request
from datetime import date

USER = os.environ.get("PROFILE_USER", "YasinKiani")
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"

WEEKS = 53          # one year
CELL, GAP = 16, 5   # cell size and gap
PITCH = CELL + GAP
PAD = 14
STEP = 0.11         # seconds per cell the snake moves
SEGMENTS = 9
PAUSE_STEPS = 30    # time off screen before the next round; eaten days grow back

THEMES = {
    "dark": {"empty": "#1B1F24", "border": "#262B31", "levels": ["#5A3410", "#8F5316", "#C8721F", "#F59541"],
             "head": "#FFB26B", "body": "#F59541", "tail": "#8F5316", "eye": "#0D0D0D"},
    "light": {"empty": "#EEF0F2", "border": "#E1E4E8", "levels": ["#FDDDBA", "#F9B774", "#F08A34", "#D46A12"],
              "head": "#E07B24", "body": "#F59541", "tail": "#FBC08A", "eye": "#FFFFFF"},
}


def contributions():
    """{(week, weekday): level} for the last 53 weeks, read from the public calendar."""
    if os.environ.get("DEMO"):
        rnd = random.Random(7)
        return {(w, d): rnd.choice([0, 0, 0, 1, 1, 2, 3, 4]) for w in range(53) for d in range(7)}
    req = urllib.request.Request(f"https://github.com/users/{USER}/contributions", headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode()
    cells = {}
    for td in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
        m = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', td)
        lvl = re.search(r'data-level="(\d)"', td)
        if m and lvl:
            cells[(int(m.group(2)), int(m.group(1)))] = int(lvl.group(1))
    return cells


def layout(cells):
    """Map (week, weekday) to a grid (col, row), newest week in the last column."""
    first = max(w for w, _ in cells) + 1 - WEEKS
    return {(w - first, d): lvl for (w, d), lvl in cells.items() if w >= first}


def center(col, row):
    return PAD + col * PITCH + CELL / 2, PAD + row * PITCH + CELL / 2


def route(grid):
    """Cell-by-cell path: enter left, visit every active cell (nearest first), exit right."""
    targets = {c for c, lvl in grid.items() if lvl}
    pos = (0, 3)
    path = [(-SEGMENTS - 2 + i, 3) for i in range(SEGMENTS + 2)] + [pos]
    targets.discard(pos)

    def walk(to):
        nonlocal pos
        (c, r), (tc, tr) = pos, to
        while r != tr:
            r += 1 if tr > r else -1
            path.append((c, r))
        while c != tc:
            c += 1 if tc > c else -1
            path.append((c, r))
        pos = (c, r)

    while targets:
        nxt = min(targets, key=lambda t: (abs(t[0] - pos[0]) + abs(t[1] - pos[1]), t))
        walk(nxt)
        targets -= set(path)
    walk((WEEKS - 1, pos[1]))
    c, r = pos
    path += [(c + i, r) for i in range(1, SEGMENTS + 3 + PAUSE_STEPS)]
    return path


def svg(grid, theme):
    t = THEMES[theme]
    path = route(grid)
    n = len(path) - 1
    dur = n * STEP
    width = PAD * 2 + WEEKS * PITCH - GAP
    height = PAD * 2 + 7 * PITCH - GAP

    regrow = (n - PAUSE_STEPS) / n  # the snake has left the grid by now
    first_visit = {}
    for i, cell in enumerate(path):
        first_visit.setdefault(cell, i)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'role="img" aria-label="Contribution snake"><title>Contribution snake</title>',
           '<defs><filter id="glow" x="-100%" y="-100%" width="300%" height="300%">'
           f'<feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
           '</filter></defs>']
    for col in range(WEEKS):
        for row in range(7):
            x, y = center(col, row)
            lvl = grid.get((col, row), 0)  # days outside the year are drawn as empty cells
            attrs = f'x="{x - CELL / 2:.1f}" y="{y - CELL / 2:.1f}" width="{CELL}" height="{CELL}" rx="4" stroke="{t["border"]}"'
            if not lvl:
                out.append(f'<rect {attrs} fill="{t["empty"]}"/>')
                continue
            color = t["levels"][lvl - 1]
            # flash when eaten, stay empty while the snake is on the grid, then grow back
            k = first_visit[(col, row)] / n
            times = [0, k, k, k + 1.5 / n, regrow, regrow + 6 / n, 1]
            values = [color, color, t["head"], t["empty"], t["empty"], color, color]
            out.append(f'<rect {attrs} fill="{color}"><animate attributeName="fill" dur="{dur:.2f}s" repeatCount="indefinite" '
                       f'keyTimes="{";".join("%.4f" % v for v in times)}" values="{";".join(values)}"/></rect>')

    d = "M" + " L".join("%.1f %.1f" % center(c, r) for c, r in path)
    lag = 0.8 * STEP  # time between two body segments
    # tail first so the head is drawn on top
    for i in reversed(range(SEGMENTS)):
        s = CELL - 1 - i * 0.7
        f = i / (SEGMENTS - 1)
        color = t["body"] if i < SEGMENTS * 0.5 else t["tail"]
        begin = -(dur - i * lag) if i else 0
        if i == 0:
            shape = (f'<g filter="url(#glow)"><rect x="{-s / 2}" y="{-s / 2}" width="{s}" height="{s}" rx="6" fill="{t["head"]}"/></g>'
                     f'<circle cx="3" cy="-3.5" r="1.9" fill="{t["eye"]}"/><circle cx="3" cy="3.5" r="1.9" fill="{t["eye"]}"/>')
        else:
            shape = (f'<rect x="{-s / 2:.1f}" y="{-s / 2:.1f}" width="{s:.1f}" height="{s:.1f}" rx="{s / 2.4:.1f}" '
                     f'fill="{color}" opacity="{1 - f * 0.55:.2f}"/>')
        out.append(f'<g>{shape}<animateMotion dur="{dur:.2f}s" begin="{begin:.2f}s" '
                   f'repeatCount="indefinite" rotate="auto" calcMode="linear" path="{d}"/></g>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    grid = layout(contributions())
    for theme, name in (("light", "github-snake.svg"), ("dark", "github-snake-dark.svg")):
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(svg(grid, theme))
    print("active days:", sum(1 for v in grid.values() if v))
