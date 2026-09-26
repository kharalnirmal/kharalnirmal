"""Render a live, spider-web themed GitHub streak graphic as SVG."""

import datetime as dt
import html
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


def render(days, today, preview=False):
    current = today if days.get(today, 0) > 0 else today - dt.timedelta(days=1)
    streak = 0
    while days.get(current, 0) > 0:
        streak += 1
        current -= dt.timedelta(days=1)
    history = [days.get(today - dt.timedelta(days=34-i), 0) for i in range(35)]
    active = sum(value > 0 for value in history)
    total = sum(history)
    cx, cy = 284, 182
    angles = [math.radians(degrees) for degrees in (-150, -100, -50, 0, 50, 100, 150)]
    radii = (35, 65, 95, 125, 155)

    def xy(radius, angle):
        return (cx + radius * math.cos(angle), cy + radius * .77 * math.sin(angle))

    web = []
    for radius in radii:
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(radius, a) for a in angles))
        web.append(f'<polyline points="{points}" fill="none" stroke="#4B6076" stroke-width="1" opacity=".65"/>')
    for angle in angles:
        x, y = xy(165, angle)
        web.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#4B6076" stroke-width="1" opacity=".65"/>')

    # One data point per day, ordered from oldest in the inner web to newest outside.
    nodes = []
    for i, count in enumerate(history):
        ring, spoke = divmod(i, 7)
        x, y = xy(radii[ring], angles[spoke])
        color = "#24D6F2" if count >= 4 else "#FF495A" if count else "#334257"
        radius = min(6.5, 3.2 + count * .6) if count else 2.5
        if count:
            nodes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius+4:.1f}" fill="{color}" opacity=".14"/>')
        nodes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}"/>')

    # An original, simple spider mark. No third-party image is embedded in the SVG.
    spider = '''<g stroke="#FF495A" stroke-width="2.7" stroke-linecap="round" fill="none">
      <path d="M272 171l-12-9-12-2M272 179l-16-2-12 7M274 186l-11 12-10 4M296 171l12-9 12-2M296 179l16-2 12 7M294 186l11 12 10 4"/>
    </g>
    <ellipse cx="284" cy="180" rx="11" ry="14" fill="#FF495A"/>
    <circle cx="284" cy="162" r="7" fill="#FF495A"/>
    <path d="M276 176l6 3-2-5M292 176l-6 3 2-5" fill="#07131D"/>'''

    flag = "CONCEPT PREVIEW · SAMPLE DATA" if preview else "LIVE DATA · GITHUB"
    date_text = today.strftime("%d %b %Y").upper()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="940" height="360" viewBox="0 0 940 360" role="img" aria-label="Nirmal Kharal: {streak} day streak, {active} active days in the last 35 days">
  <title>Nirmal's Spider Streak</title>
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop stop-color="#081420"/><stop offset="1" stop-color="#101B2E"/>
    </linearGradient>
    <linearGradient id="thread" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop stop-color="#FF495A"/><stop offset="1" stop-color="#24D6F2"/>
    </linearGradient>
  </defs>
  <rect width="940" height="360" rx="22" fill="url(#bg)"/>
  <rect x="1" y="1" width="938" height="358" rx="21" fill="none" stroke="#32465D"/>
  <path d="M0 57H940" stroke="#32465D"/>
  <rect x="28" y="23" width="11" height="11" rx="2" fill="#FF495A"/>
  <text x="52" y="34" font-size="14" font-weight="700" fill="#EAF1F7" letter-spacing="2" font-family="DejaVu Sans,Arial,sans-serif">NIRMAL / SPIDER STREAK</text>
  <text x="910" y="34" text-anchor="end" font-size="11" fill="#8499AD" letter-spacing="1.5" font-family="DejaVu Sans,Arial,sans-serif">{html.escape(flag)}</text>
  <g>{''.join(web)}{''.join(nodes)}{spider}</g>
  <path d="M576 79V319" stroke="#32465D"/>
  <text x="610" y="112" font-size="12" font-weight="700" fill="#8499AD" letter-spacing="2.5" font-family="DejaVu Sans,Arial,sans-serif">CONNECTED DAYS</text>
  <text x="604" y="229" font-size="116" font-weight="800" fill="#F5F8FB" font-family="DejaVu Sans,Arial,sans-serif">{streak}</text>
  <path d="M608 243H902" stroke="url(#thread)" stroke-width="3"/>
  <circle cx="608" cy="243" r="5" fill="#FF495A"/>
  <circle cx="902" cy="243" r="5" fill="#24D6F2"/>
  <text x="610" y="281" font-size="16" font-weight="700" fill="#24D6F2" font-family="DejaVu Sans,Arial,sans-serif">{active} / 35</text>
  <text x="699" y="281" font-size="12" fill="#A9BAC9" letter-spacing="1" font-family="DejaVu Sans,Arial,sans-serif">ACTIVE WEB NODES</text>
  <text x="610" y="312" font-size="12" fill="#A9BAC9" font-family="DejaVu Sans,Arial,sans-serif">{total} contributions across the web</text>
  <path d="M28 329H912" stroke="#32465D"/>
  <text x="30" y="349" font-size="11" fill="#8499AD" letter-spacing="1" font-family="DejaVu Sans,Arial,sans-serif">EACH CONTRIBUTION ADDS A THREAD</text>
  <text x="910" y="349" text-anchor="end" font-size="11" fill="#8499AD" font-family="DejaVu Sans,Arial,sans-serif">{date_text}</text>
</svg>'''


if __name__ == "__main__":
    preview = "--preview" in sys.argv
    today = dt.datetime.now(dt.timezone.utc).date()
    if preview:
        sample = [0, 1, 2, 0, 1, 4, 0, 2, 1, 0, 3, 5, 2, 0, 1, 3, 0, 0,
                  2, 4, 1, 3, 0, 2, 5, 1, 0, 1, 3, 2, 4, 2, 5, 3, 0]
        data = {today - dt.timedelta(days=34-i): value for i, value in enumerate(sample)}
        output = Path("spider-streak-preview.svg")
    else:
        data = fetch_days()
        output = Path("assets/spider-streak.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(data, today, preview), encoding="utf-8")
    print(f"Wrote {output}")
