#!/usr/bin/env python3
"""
Generate a custom GitHub stats card SVG (Total Stars / Commits / PRs / Issues /
Contributed) styled to match assets/streak-rings.svg.

Run by the GitHub Action in .github/workflows/streak.yml.
Env vars:
  GH_TOKEN  - token with GraphQL access (the Action's GITHUB_TOKEN works for public data)
  GH_USER   - the GitHub username (defaults to qnicondavid)
"""

import os
import json
import datetime
import urllib.request

USER = os.environ.get("GH_USER", "qnicondavid")
TOKEN = os.environ.get("GH_TOKEN")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "stats-card.svg")
API = "https://api.github.com/graphql"

# ---- palette (shared with generate_streak.py) ---------------------------
SLATE = "#6f8bad"
CLAY  = "#bf7257"
SAGE  = "#7e9c86"
NUM   = "#7d8590"   # numbers
LINE  = "#8a8f98"   # hairline dividers

# ---- hairline outline icons (lucide), drawn in a 24x24 box --------------
IC_STAR = ('<path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 '
           '1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0 '
           '-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0 '
           '-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0 '
           '-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 '
           '1.597-1.16z"/>')
IC_COMMIT = ('<circle cx="12" cy="12" r="3"/><line x1="3" y1="12" x2="9" y2="12"/>'
             '<line x1="15" y1="12" x2="21" y2="12"/>')
IC_PR = ('<circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/>'
         '<path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/>')
IC_ISSUE = ('<circle cx="12" cy="12" r="9"/>'
            '<circle cx="12" cy="12" r="1.6" fill="ACCENT" stroke="none"/>')
IC_FOLDER = ('<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 '
             '3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>')


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


def fetch_stats():
    now = datetime.datetime.now(datetime.timezone.utc)
    frm = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    q = """
    query($l:String!,$from:DateTime!,$to:DateTime!){
      user(login:$l){
        pullRequests{ totalCount }
        issues{ totalCount }
        repositories(first:100, ownerAffiliations:OWNER, isFork:false){
          nodes{ stargazerCount }
        }
        contributionsCollection(from:$from,to:$to){
          totalCommitContributions
          totalRepositoriesWithContributedCommits
        }
      }
    }"""
    d = gql(q, {"l": USER, "from": frm.isoformat(), "to": now.isoformat()})["user"]
    cc = d["contributionsCollection"]
    return {
        "year": now.year,
        "stars": sum(n["stargazerCount"] for n in d["repositories"]["nodes"]),
        "commits": cc["totalCommitContributions"],
        "prs": d["pullRequests"]["totalCount"],
        "issues": d["issues"]["totalCount"],
        "contrib": cc["totalRepositoriesWithContributedCommits"],
    }


# ---- drawing ------------------------------------------------------------
def icon(paths, x, ytop, accent):
    body = paths.replace("ACCENT", accent)
    return (f'<g transform="translate({x},{ytop}) scale(0.75)" stroke="{accent}" '
            f'stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">'
            f'{body}</g>')


def render(s):
    rows = [
        (IC_STAR,   CLAY,  "Total Stars Earned",             s["stars"]),
        (IC_COMMIT, SLATE, f'Total Commits ({s["year"]})',   s["commits"]),
        (IC_PR,     SAGE,  "Total PRs",                      s["prs"]),
        (IC_ISSUE,  CLAY,  "Total Issues",                   s["issues"]),
        (IC_FOLDER, SLATE, f'Contributed to ({s["year"]})',  s["contrib"]),
    ]
    baselines = [28, 64, 100, 136, 172]

    parts = []
    for (ic, color, label, value), yb in zip(rows, baselines):
        parts.append(icon(ic, 6, yb - 14, color))
        parts.append(f'<text x="34" y="{yb}" class="lbl" fill="{color}">{label}</text>')
        parts.append(f'<text x="474" y="{yb}" text-anchor="end" class="val">{value:,}</text>')

    inner = "\n  ".join(parts)
    return f'''<svg viewBox="0 0 480 188" xmlns="http://www.w3.org/2000/svg" fill="none">
  <style>
    .lbl {{ font: 600 14px 'Segoe UI',Ubuntu,Helvetica,Arial,sans-serif; }}
    .val {{ font: 700 17px 'Segoe UI',Ubuntu,Helvetica,Arial,sans-serif; fill:{NUM}; }}
  </style>
  {inner}
</svg>
'''


def main():
    if not TOKEN:
        raise SystemExit("GH_TOKEN is not set")
    s = fetch_stats()
    svg = render(s)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"stars={s['stars']} commits={s['commits']} prs={s['prs']} "
          f"issues={s['issues']} contrib={s['contrib']}")


if __name__ == "__main__":
    main()
