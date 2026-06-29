#!/usr/bin/env python3
"""
Generate a custom Top Languages card SVG (stacked bar + legend, muted colors)
styled to match assets/stats-card.svg and assets/streak-rings.svg.

Run by the GitHub Action in .github/workflows/streak.yml.
Env vars:
  GH_TOKEN  - token with GraphQL access (the Action's GITHUB_TOKEN works for public data)
  GH_USER   - the GitHub username (defaults to qnicondavid)
"""

import os
import json
import html
import urllib.request

USER = os.environ.get("GH_USER", "qnicondavid")
TOKEN = os.environ.get("GH_TOKEN")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "langs-card.svg")
API = "https://api.github.com/graphql"

NEUTRAL = "#8a8f98"   # mute target + fallback for languages with no color
NAME    = "#8a8f98"   # legend text
OTHER   = "#6e7681"   # 'Other' segment / legend dot
TOP_N   = 5           # named languages before the rest are grouped as 'Other'


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


def fetch_langs():
    q = """
    query($l:String!){
      user(login:$l){
        repositories(first:100, ownerAffiliations:OWNER, isFork:false){
          nodes{
            languages(first:20, orderBy:{field:SIZE, direction:DESC}){
              edges{ size node{ name color } }
            }
          }
        }
      }
    }"""
    nodes = gql(q, {"l": USER})["user"]["repositories"]["nodes"]
    totals, colors = {}, {}
    for repo in nodes:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            totals[n] = totals.get(n, 0) + e["size"]
            colors[n] = e["node"]["color"]
    return totals, colors


# ---- colour -------------------------------------------------------------
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mute(color, f=0.45):
    """Blend a language's real colour toward the card's neutral so it stays
    recognisable but doesn't fight the muted palette."""
    if not color:
        color = NEUTRAL
    target = _rgb(NEUTRAL)
    m = tuple(round(c * (1 - f) + t * f) for c, t in zip(_rgb(color), target))
    return "#%02x%02x%02x" % m


def build_rows(totals, colors):
    grand = sum(totals.values()) or 1
    ordered = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    rows = [(n, s / grand * 100, mute(colors.get(n))) for n, s in ordered[:TOP_N]]
    rem = sum(s for _, s in ordered[TOP_N:])
    if rem > 0:
        rows.append(("Other", rem / grand * 100, OTHER))
    return rows


# ---- drawing ------------------------------------------------------------
def render(rows):
    segs, x = [], 8.0
    for _, pct, color in rows:
        w = 384 * pct / 100
        segs.append(f'<rect x="{x:.2f}" y="22" width="{w + 0.6:.2f}" height="11" fill="{color}"/>')
        x += w
    bar = ('<clipPath id="bc"><rect x="8" y="22" width="384" height="11" rx="5.5"/></clipPath>'
           f'<g clip-path="url(#bc)">{"".join(segs)}</g>')

    leg = []
    for i, (name, pct, color) in enumerate(rows):
        dx = 210 if i % 2 else 12
        ty = 70 + (i // 2) * 38
        leg.append(f'<circle cx="{dx}" cy="{ty - 4}" r="5" fill="{color}"/>')
        leg.append(f'<text x="{dx + 14}" y="{ty}" class="ln">{html.escape(name)} {round(pct)}%</text>')

    return f'''<svg viewBox="0 0 400 188" xmlns="http://www.w3.org/2000/svg" fill="none">
  <style>
    .ln {{ font: 600 13px 'Segoe UI',Ubuntu,Helvetica,Arial,sans-serif; fill:{NAME}; }}
  </style>
  {bar}
  {"".join(leg)}
</svg>
'''


def main():
    if not TOKEN:
        raise SystemExit("GH_TOKEN is not set")
    rows = build_rows(*fetch_langs())
    svg = render(rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("langs: " + ", ".join(f"{n} {round(p)}%" for n, p, _ in rows))


if __name__ == "__main__":
    main()
