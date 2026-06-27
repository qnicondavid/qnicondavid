#!/usr/bin/env python3
"""
Generate a custom three-ring streak SVG (Total Contributions / Current Streak /
Longest Streak) from real GitHub contribution data.

Run by the GitHub Action in .github/workflows/streak.yml.
Env vars:
  GH_TOKEN  - token with GraphQL access (the Action's GITHUB_TOKEN works for public contributions)
  GH_USER   - the GitHub username (defaults to qnicondavid)
"""

import os
import json
import math
import datetime
import urllib.request

USER = os.environ.get("GH_USER", "qnicondavid")
TOKEN = os.environ.get("GH_TOKEN")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "streak-rings.svg")
API = "https://api.github.com/graphql"

# ---- editorial palette --------------------------------------------------
SLATE = "#6f8bad"   # total   - dotted ring (many contributions)
CLAY  = "#bf7257"   # current - gapped ring + flame (burning)
SAGE  = "#7e9c86"   # longest - near-solid ring + star (record)
NUM   = "#7d8590"   # numbers (legible on light + dark)
DATE  = "#8a8f98"   # date text


# ---- data ---------------------------------------------------------------
def gql(query, variables):
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        API, data=payload,
        headers={"Authorization": f"bearer {TOKEN}",
                 "Content-Type": "application/json", "User-Agent": USER})
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise RuntimeError(json.dumps(body["errors"]))
    return body["data"]


def fetch_days():
    created = gql("query($l:String!){user(login:$l){createdAt}}", {"l": USER})
    start_year = int(created["user"]["createdAt"][:4])
    this_year = datetime.datetime.utcnow().year
    q = """
    query($l:String!,$from:DateTime!,$to:DateTime!){
      user(login:$l){ contributionsCollection(from:$from,to:$to){
        contributionCalendar{ weeks{ contributionDays{ date contributionCount } } } } } }"""
    days = {}
    for year in range(start_year, this_year + 1):
        data = gql(q, {"l": USER,
                       "from": f"{year}-01-01T00:00:00Z",
                       "to": f"{year}-12-31T23:59:59Z"})
        cal = data["user"]["contributionsCollection"]["contributionCalendar"]
        for week in cal["weeks"]:
            for d in week["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
    return days


def compute(days):
    today = datetime.date.today().isoformat()
    items = [(d, c) for d, c in sorted(days.items()) if d <= today]

    total = sum(c for _, c in items)

    # longest streak + its date span
    longest = run = 0
    run_start = 0
    long_start = long_end = None
    for j, (_, c) in enumerate(items):
        if c > 0:
            if run == 0:
                run_start = j
            run += 1
            if run > longest:
                longest = run
                long_start, long_end = run_start, j
        else:
            run = 0

    # current streak + its date span
    end_idx = len(items) - 1
    if items and items[end_idx][0] == today and items[end_idx][1] == 0:
        end_idx -= 1
    current = 0
    i = end_idx
    while i >= 0 and items[i][1] > 0:
        current += 1
        i -= 1
    cur_start_idx = i + 1

    cur_range = (items[cur_start_idx][0], items[end_idx][0]) if current > 0 else (None, None)
    long_range = (items[long_start][0], items[long_end][0]) if longest > 0 else (None, None)
    cur_commits = sum(c for _, c in items[cur_start_idx:end_idx + 1]) if current > 0 else 0
    long_commits = sum(c for _, c in items[long_start:long_end + 1]) if longest > 0 else 0
    return total, current, longest, cur_range, long_range, cur_commits, long_commits


def fmt_range(start, end):
    if not start:
        return ""
    sd = datetime.date.fromisoformat(start)
    ed = datetime.date.fromisoformat(end)
    if sd == ed:
        return f"{sd.strftime('%b')} {sd.day}"
    return f"{sd.strftime('%b')} {sd.day} – {ed.strftime('%b')} {ed.day}"


# ---- drawing ------------------------------------------------------------
def arc(cx, cy, r, gap=60):
    a1 = math.radians(gap / 2)
    a2 = math.radians(360 - gap / 2)
    x1, y1 = cx + r * math.sin(a1), cy - r * math.cos(a1)
    x2, y2 = cx + r * math.sin(a2), cy - r * math.cos(a2)
    return f"M {x1:.2f} {y1:.2f} A {r} {r} 0 1 1 {x2:.2f} {y2:.2f}"


def star(cx, cy, ro, ri=None, pts=5):
    ri = ri or ro * 0.45
    p = []
    for k in range(pts * 2):
        a = math.pi / pts * k - math.pi / 2
        rr = ro if k % 2 == 0 else ri
        p.append(f"{cx + rr * math.cos(a):.2f},{cy + rr * math.sin(a):.2f}")
    return "M" + " L".join(p) + " Z"


LUCIDE_FLAME = ("M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 "
                "2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 "
                "1-3a2.5 2.5 0 0 0 2.5 2.5z")


def flame_icon(cx, cyc, h=30, fill=CLAY):
    sc = h / 24.0
    tx = cx - 12 * sc
    ty = cyc - 12 * sc
    return (f'<g transform="translate({tx:.2f},{ty:.2f}) scale({sc:.3f})">'
            f'<path d="{LUCIDE_FLAME}" fill="{fill}"/></g>')


CROWN = "M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zM5 18.5h14v2.4H5z"


def crown_icon(cx, cyc, h=27, fill=SAGE):
    sc = h / 24.0
    tx = cx - 12 * sc
    ty = cyc - 12 * sc
    return (f'<g transform="translate({tx:.2f},{ty:.2f}) scale({sc:.3f})">'
            f'<path d="{CROWN}" fill="{fill}"/></g>')


def render(total, current, longest, cur_date, long_date, cur_commits=0, long_commits=0):
    cy, r = 90, 44
    x1, x2, x3 = 112, 272, 432

    circ = 2 * math.pi * r
    seg = circ / 26  # 26 evenly spaced dots so start/end don't overlap
    total_ring = (f'<circle cx="{x1}" cy="{cy}" r="{r}" stroke="{SLATE}" stroke-width="5" '
                  f'stroke-linecap="round" stroke-dasharray="0.01 {seg - 0.01:.4f}"/>')

    flame_path = flame_icon(x2, cy - r + 1, 30)
    cur_ring = (f'<path d="{arc(x2, cy, r)}" stroke="{CLAY}" stroke-width="5" '
                f'stroke-linecap="round"/>{flame_path}')

    long_ring = (f'<path d="{arc(x3, cy, r, gap=60)}" stroke="{SAGE}" stroke-width="5" '
                 f'stroke-linecap="round"/>' + crown_icon(x3, cy - r + 1, 27))

    def num(x, v):
        return f'<text x="{x}" y="{cy + 12}" text-anchor="middle" class="num">{v}</text>'

    def lab(x, t, c):
        return f'<text x="{x}" y="166" text-anchor="middle" class="lbl" fill="{c}">{t}</text>'

    def dt(x, t):
        return f'<text x="{x}" y="200" text-anchor="middle" class="dt">{t}</text>' if t else ''

    def cm(x, n, c):
        if not n:
            return ''
        word = 'commit' if n == 1 else 'commits'
        return f'<text x="{x}" y="184" text-anchor="middle" class="cm" fill="{c}">{n:,} {word}</text>'

    return f'''<svg viewBox="0 0 544 222" xmlns="http://www.w3.org/2000/svg" fill="none">
  <style>
    .num {{ font: 700 30px 'Segoe UI',Ubuntu,Helvetica,Arial,sans-serif; fill:{NUM}; }}
    .lbl {{ font: 600 14px 'Segoe UI',Ubuntu,Helvetica,Arial,sans-serif; }}
    .dt  {{ font: 400 11px 'Segoe UI',Ubuntu,Helvetica,Arial,sans-serif; fill:{DATE}; }}
    .cm  {{ font: 600 11px 'Segoe UI',Ubuntu,Helvetica,Arial,sans-serif; }}
  </style>
  {total_ring}{num(x1, f"{total:,}")}{lab(x1, "Total Contributions", SLATE)}
  {cur_ring}{num(x2, current)}{lab(x2, "Current Streak", CLAY)}{cm(x2, cur_commits, CLAY)}{dt(x2, cur_date)}
  {long_ring}{num(x3, longest)}{lab(x3, "Longest Streak", SAGE)}{cm(x3, long_commits, SAGE)}{dt(x3, long_date)}
</svg>
'''


def main():
    if not TOKEN:
        raise SystemExit("GH_TOKEN is not set")
    total, current, longest, cur_range, long_range, cur_commits, long_commits = compute(fetch_days())
    svg = render(total, current, longest,
                 fmt_range(*cur_range), fmt_range(*long_range),
                 cur_commits, long_commits)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"total={total} current={current} longest={longest} "
          f"cur={fmt_range(*cur_range)} long={fmt_range(*long_range)}")


if __name__ == "__main__":
    main()
