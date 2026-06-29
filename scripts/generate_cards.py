#!/usr/bin/env python3
"""
Combine the stats card and languages card into one side-by-side SVG so they
always render on a single row in the profile README. A single <img> can't wrap,
and at width="100%" it scales to whatever column width GitHub gives it.

Run by the GitHub Action AFTER generate_stats.py and generate_langs.py.
"""

import os

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
STATS = os.path.join(ASSETS, "stats-card.svg")
LANGS = os.path.join(ASSETS, "langs-card.svg")
OUT = os.path.join(ASSETS, "cards.svg")

H = 188            # both cards share this height
LANG_X = 520       # left edge of the languages card (stats is 480 wide -> ~40px gap)
LANGS_W = 400
TOTAL_W = LANG_X + LANGS_W


def inner(path):
    """Return everything inside a card's outer <svg> ... </svg> wrapper."""
    s = open(path, encoding="utf-8").read()
    start = s.index(">", s.index("<svg")) + 1
    end = s.rindex("</svg>")
    return s[start:end].strip()


def main():
    combined = f'''<svg viewBox="0 0 {TOTAL_W} {H}" xmlns="http://www.w3.org/2000/svg" fill="none">
  <g>{inner(STATS)}</g>
  <g transform="translate({LANG_X},0)">{inner(LANGS)}</g>
</svg>
'''
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(combined)
    print(f"cards.svg written ({TOTAL_W}x{H})")


if __name__ == "__main__":
    main()
