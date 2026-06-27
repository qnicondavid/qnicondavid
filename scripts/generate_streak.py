#!/usr/bin/env python3
"""
Generate a custom three-ring streak SVG (Total Contributions / Current Streak /
Longest Streak) from real GitHub contribution data.

Run by the GitHub Action in .github/workflows/streak.yml.
Requires env vars:
  GH_TOKEN  - token with GraphQL access (the Action's GITHUB_TOKEN works for public contributions)
  GH_USER   - the GitHub username (defaults to qnicondavid)
"""

import os
import json
import datetime
import urllib.request

USER = os.environ.get("GH_USER", "qnicondavid")
TOKEN = os.environ.get("GH_TOKEN")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "streak-rings.svg")

API = "https://api.github.com/graphql"


def gql(query, variables):
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        API,
        data=payload,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": USER,
        },
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise RuntimeError(json.dumps(body["errors"]))
    return body["data"]


def fetch_days():
    """Return {date_str: count} for every day since account creation."""
    created = gql("query($l:String!){user(login:$l){createdAt}}", {"l": USER})
    start_year = int(created["user"]["createdAt"][:4])
    this_year = datetime.datetime.utcnow().year

    q = """
    query($l:String!,$from:DateTime!,$to:DateTime!){
      user(login:$l){
        contributionsCollection(from:$from,to:$to){
          contributionCalendar{
            weeks{ contributionDays{ date contributionCount } }
          }
        }
      }
    }"""

    days = {}
    for year in range(start_year, this_year + 1):
        data = gql(q, {
            "l": USER,
            "from": f"{year}-01-01T00:00:00Z",
            "to": f"{year}-12-31T23:59:59Z",
        })
        cal = data["user"]["contributionsCollection"]["contributionCalendar"]
        for week in cal["weeks"]:
            for d in week["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
    return days


def compute(days):
    today = datetime.date.today().isoformat()
    items = [(d, c) for d, c in sorted(days.items()) if d <= today]

    total = sum(c for _, c in items)

    longest = run = 0
    for _, c in items:
        if c > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    idx = len(items) - 1
    if items and items[idx][0] == today and items[idx][1] == 0:
        idx -= 1
    current = 0
    while idx >= 0 and items[idx][1] > 0:
        current += 1
        idx -= 1

    return total, current, longest


SVG = """<svg viewBox="0 0 495 195" xmlns="http://www.w3.org/2000/svg" fill="none">
  <style>
    .num {{ font: 700 30px 'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif; fill: #808080; }}
    .lbl {{ font: 600 14px 'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif; fill: #708090; }}
  </style>

  <line x1="185" y1="48" x2="185" y2="150" stroke="#808080" stroke-width="1" opacity="0.35"/>
  <line x1="310" y1="48" x2="310" y2="150" stroke="#808080" stroke-width="1" opacity="0.35"/>

  <!-- Total Contributions -->
  <circle cx="92" cy="86" r="40" stroke="#708090" stroke-width="5"/>
  <text x="92" y="96" text-anchor="middle" class="num">{total}</text>
  <text x="92" y="156" text-anchor="middle" class="lbl">Total Contributions</text>

  <!-- Current Streak -->
  <circle cx="247" cy="86" r="40" stroke="#708090" stroke-width="5"/>
  <path d="M247,34 c-8,8 -11,13 -11,19 a11,11 0 0 0 22,0 c0,-6 -3,-11 -11,-19 z" fill="#708090"/>
  <text x="247" y="96" text-anchor="middle" class="num">{current}</text>
  <text x="247" y="156" text-anchor="middle" class="lbl">Current Streak</text>

  <!-- Longest Streak -->
  <circle cx="402" cy="86" r="40" stroke="#708090" stroke-width="5"/>
  <text x="402" y="96" text-anchor="middle" class="num">{longest}</text>
  <text x="402" y="156" text-anchor="middle" class="lbl">Longest Streak</text>
</svg>
"""


def main():
    if not TOKEN:
        raise SystemExit("GH_TOKEN is not set")
    total, current, longest = compute(fetch_days())
    svg = SVG.format(total=f"{total:,}", current=current, longest=longest)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"total={total} current={current} longest={longest}")


if __name__ == "__main__":
    main()
