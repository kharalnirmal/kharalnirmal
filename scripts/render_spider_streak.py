"""Render a live, spider-web themed GitHub streak graphic as SVG."""

import datetime as dt
import json
import math
import os
from pathlib import Path
import sys
import urllib.request

USERNAME = "kharalnirmal"
QUERY = """query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""


def fetch_days():
    payload = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                 "Content-Type": "application/json", "User-Agent": "spider-streak-readme"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors") or not result.get("data", {}).get("user"):
        raise RuntimeError(f"Contribution query failed: {result.get('errors')}")
    weeks = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {dt.date.fromisoformat(day["date"]): day["contributionCount"]
            for week in weeks for day in week["contributionDays"]}


def render(days, today, transparent=False):
    current = today if days.get(today, 0) > 0 else today - dt.timedelta(days=1)
    streak = 0
    while days.get(current, 0) > 0:
        streak += 1
        current -= dt.timedelta(days=1)
    history = [days.get(today - dt.timedelta(days=34-i), 0) for i in range(35)]
    active = sum(value > 0 for value in history)
    cx, cy = 280, 165
    angles = [math.radians(-90 + i * 360 / 7) for i in range(7)]
    radii = (86, 102, 118, 134, 151)

    def xy(radius, angle):
        return (cx + radius * math.cos(angle), cy + radius * .67 * math.sin(angle))

    web = []
    for radius in radii:
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(radius, a) for a in angles))
        web.append(f'<polygon points="{points}" fill="none" stroke="#6B6B6B" stroke-width=".9" opacity=".63"/>')
    for angle in angles:
        x, y = xy(151, angle)
        web.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#6B6B6B" stroke-width=".9" opacity=".63"/>')

    # One data point per day, ordered from oldest in the inner web to newest outside.
    nodes = []
    for i, count in enumerate(history):
        ring, spoke = divmod(i, 7)
        x, y = xy(radii[ring], angles[spoke])
        color = "#FF5B65" if count >= 4 else "#DC3549" if count else "#555555"
        radius = min(5.3, 3 + count * .45) if count else 2.1
        if count:
            nodes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius+3:.1f}" fill="{color}" opacity=".12"/>')
        nodes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}"/>')

    # The spider's legs stay within the empty central area (r < 80).
    # Each side has four distinct, jointed legs and the body has two sections.
    legs = []
    for direction in (-1, 1):
        paths = (
            ((10, -13), (26, -28), (40, -30), (55, -44)),
            ((13, -7), (30, -16), (48, -8), (67, -13)),
            ((13, 3), (34, 9), (49, 20), (67, 22)),
            ((10, 13), (27, 29), (39, 38), (54, 50)),
        )
        for root, knee, joint, tip in paths:
            coords = [(cx + direction*x, cy + y) for x, y in (root, knee, joint, tip)]
            p = " ".join(f"{x:.0f},{y:.0f}" for x, y in coords)
            legs.append(f'<polyline points="{p}" fill="none" stroke="#D5D5D5" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>')
            legs.append(f'<circle cx="{coords[1][0]}" cy="{coords[1][1]}" r="2.4" fill="#F04A59"/>')
    spider = f'''<g>{''.join(legs)}
      <path d="M280 145V128" stroke="#858585" stroke-width="1"/>
      <ellipse cx="280" cy="176" rx="15" ry="21" fill="#AF2536" stroke="#F25C65" stroke-width="1.2"/>
      <path d="M271 169Q280 176 289 169M274 183l6 7 6-7" fill="none" stroke="#181818" stroke-width="2" opacity=".8"/>
      <ellipse cx="280" cy="149" rx="11" ry="10" fill="#D33749" stroke="#F36D74" stroke-width="1"/>
      <path d="M275 146l3 2M285 146l-3 2" stroke="#F3E6E7" stroke-width="1.5" stroke-linecap="round"/>
    </g>'''

    background = '' if transparent else '<rect width="900" height="320" rx="18" fill="#000000"/>'
    border = '' if transparent else '<rect x=".8" y=".8" width="898.4" height="318.4" rx="17.2" fill="none" stroke="#353535" stroke-width="1.6"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="320" viewBox="0 0 900 320" role="img" aria-label="Nirmal Kharal: {streak} day contribution streak, {active} active days out of 35">
  <title>Nirmal's Spider Streak</title>
  {background}{border}
  <rect x="28" y="24" width="4" height="15" rx="2" fill="#E34454"/>
  <text x="43" y="37" font-size="14" font-weight="700" fill="#F1F1F1" letter-spacing="1.7" font-family="DejaVu Sans,Arial,sans-serif">SPIDER STREAK</text>
  <g>{''.join(web)}{''.join(nodes)}{spider}</g>
  <path d="M527 71V274" stroke="#3E3E3E" stroke-width="1"/>
  <text x="566" y="102" font-size="13" font-weight="700" fill="#BEBEBE" letter-spacing="2" font-family="DejaVu Sans,Arial,sans-serif">CURRENT STREAK</text>
  <text x="557" y="212" font-size="116" font-weight="800" fill="#F7F7F7" font-family="DejaVu Sans,Arial,sans-serif">{streak}</text>
  <path d="M566 231H852" stroke="#D83A4C" stroke-width="2"/>
  <text x="566" y="267" font-size="15" fill="#DDDDDD" font-family="DejaVu Sans,Arial,sans-serif">{active} / 35 active days</text>
</svg>'''


if __name__ == "__main__":
    preview = "--preview" in sys.argv
    today = dt.datetime.now(dt.timezone.utc).date()
    if preview:
        sample = [0, 1, 2, 0, 1, 4, 0, 2, 1, 0, 3, 5, 2, 0, 1, 3, 0, 0,
                  2, 4, 1, 3, 0, 2, 5, 1, 0, 1, 3, 2, 4, 2, 5, 3, 0]
        data = {today - dt.timedelta(days=34-i): value for i, value in enumerate(sample)}
        output = Path("spider-streak-preview.svg")
        transparent_output = Path("spider-streak-transparent-preview.svg")
    else:
        data = fetch_days()
        output = Path("assets/spider-streak.svg")
        transparent_output = Path("assets/spider-streak-transparent.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(data, today), encoding="utf-8")
    transparent_output.write_text(render(data, today, transparent=True), encoding="utf-8")
    print(f"Wrote {output} and {transparent_output}")
