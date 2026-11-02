"""Render a transparent, spider-web GitHub streak graphic."""

import datetime as dt
import json
import math
import os
from pathlib import Path
import urllib.request
from zoneinfo import ZoneInfo

USERNAME = "kharalnirmal"

# GitHub's default contribution calendar covers only about one year.
# Query each contribution year so the record includes the entire account history.
YEARS_QUERY = """query($login: String!) {
  user(login: $login) {
    contributionsCollection { contributionYears }
  }
}"""

YEAR_QUERY = """query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""


def graphql_user(query, variables):
    payload = json.dumps({
        "query": query,
        "variables": variables,
    }).encode()

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": "spider-streak-readme",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)

    if result.get("errors") or not result.get("data", {}).get("user"):
        raise RuntimeError(
            f"Contribution query failed: {result.get('errors')}"
        )
    return result["data"]["user"]


def fetch_days():
    user = graphql_user(YEARS_QUERY, {"login": USERNAME})
    years = sorted(set(user["contributionsCollection"]["contributionYears"]))
    now = dt.datetime.now(dt.timezone.utc)
    days = {}

    for year in years:
        start = dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc)
        # Never request future dates or a range longer than a calendar year.
        end = min(
            dt.datetime(year + 1, 1, 1, tzinfo=dt.timezone.utc)
            - dt.timedelta(seconds=1),
            now,
        )
        if start > end:
            continue

        user = graphql_user(YEAR_QUERY, {
            "login": USERNAME,
            "from": start.isoformat().replace("+00:00", "Z"),
            "to": end.isoformat().replace("+00:00", "Z"),
        })
        weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]

        for week in weeks:
            for day in week["contributionDays"]:
                date = dt.date.fromisoformat(day["date"])
                if date.year == year:
                    days[date] = day["contributionCount"]

    return days


def streak_stats(days, today):
    # A streak remains current until the end of today if yesterday was active.
    cursor = today if days.get(today, 0) > 0 else today - dt.timedelta(days=1)
    current = 0
    streak_dates = set()
    while days.get(cursor, 0) > 0:
        current += 1
        streak_dates.add(cursor)
        cursor -= dt.timedelta(days=1)

    # The historical best persists even if the current streak ends.
    longest = 0
    run = 0
    previous = None
    for date, count in sorted(days.items()):
        if date > today or count <= 0:
            continue
        if previous is not None and date - previous == dt.timedelta(days=1):
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        previous = date

    return current, longest, streak_dates


def render(days, today, theme="dark"):
    streak, longest, streak_dates = streak_stats(days, today)

    history = [
        days.get(today - dt.timedelta(days=34 - i), 0)
        for i in range(35)
    ]
    if theme not in ("dark", "light"):
        raise ValueError("theme must be dark or light")

    ink = "#F1F1F1" if theme == "dark" else "#202124"
    muted = "#D1D1D1" if theme == "dark" else "#50545A"
    thread = "#888888" if theme == "dark" else "#6E7379"
    inactive = "#626262" if theme == "dark" else "#858B91"
    divider = "#646464" if theme == "dark" else "#B7BCC1"
    leg = "#D5D5D5" if theme == "dark" else "#383D43"

    cx, cy = 280, 165
    angles = [
        math.radians(-90 + i * 360 / 7)
        for i in range(7)
    ]
    radii = (86, 102, 118, 134, 151)

    def xy(radius, angle):
        return (
            cx + radius * math.cos(angle),
            cy + radius * 0.67 * math.sin(angle),
        )

    web = []

    for radius in radii:
        points = " ".join(
            f"{x:.1f},{y:.1f}"
            for x, y in (xy(radius, angle) for angle in angles)
        )
        web.append(
            f'<polygon points="{points}" fill="none" '
            f'stroke="{thread}" stroke-width=".9" opacity=".7"/>'
        )

    for angle in angles:
        x, y = xy(151, angle)
        web.append(
            f'<line x1="{cx}" y1="{cy}" '
            f'x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{thread}" stroke-width=".9" opacity=".7"/>'
        )

    # Each ring contains seven days. Inner rings are older.
    nodes = []

    for i, count in enumerate(history):
        ring, spoke = divmod(i, 7)
        x, y = xy(radii[ring], angles[spoke])
        date = today - dt.timedelta(days=34 - i)

        color = (
            "#FF5B65" if count >= 4
            else "#DC3549" if count
            else inactive
        )
        radius = min(5.3, 3 + count * 0.45) if count else 2.1

        if count:
            nodes.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" '
                f'r="{radius + 3:.1f}" fill="{color}" opacity=".12"/>'
            )

        nodes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" '
            f'r="{radius:.1f}" fill="{color}"/>'
        )

        # Outline only the dots that belong to the current streak.
        if date in streak_dates:
            nodes.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" '
                f'r="{radius + 2.4:.1f}" fill="none" '
                f'stroke="{ink}" stroke-width="1.25"/>'
            )

    # Four segmented legs on each side, clear of the data dots.
    legs = []

    for direction in (-1, 1):
        paths = (
            ((9, -13), (25, -26), (39, -34), (54, -49)),
            ((12, -6), (30, -14), (47, -12), (65, -19)),
            ((12, 3), (31, 8), (47, 17), (65, 23)),
            ((9, 12), (25, 26), (39, 35), (54, 48)),
        )

        for root, knee, joint, tip in paths:
            coords = [
                (cx + direction * x, cy + y)
                for x, y in (root, knee, joint, tip)
            ]
            proximal = " ".join(
                f"{x:.0f},{y:.0f}" for x, y in coords[:3]
            )
            distal = " ".join(
                f"{x:.0f},{y:.0f}" for x, y in coords[2:]
            )

            legs.append(
                f'<polyline points="{proximal}" fill="none" '
                f'stroke="{leg}" stroke-width="3.5" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
            )
            legs.append(
                f'<polyline points="{distal}" fill="none" '
                f'stroke="{leg}" stroke-width="1.7" '
                f'stroke-linecap="round"/>'
            )
            legs.append(
                f'<circle cx="{coords[1][0]}" cy="{coords[1][1]}" '
                f'r="1.8" fill="#B53849"/>'
            )

    spider = f'''<g>{''.join(legs)}
      <path d="M280 157v4" stroke="#8F6266" stroke-width="4"/>
      <ellipse cx="280" cy="180" rx="15" ry="20"
        fill="#362126" stroke="#A45B65" stroke-width="1.2"/>
      <path d="M280 164c-5 5-7 12-4 17l4-4 4 4c3-5 1-12-4-17z"
        fill="#B63848"/>
      <path d="M272 189q8 5 16 0"
        fill="none" stroke="#8F515B" stroke-width="1"/>
      <ellipse cx="280" cy="148" rx="11" ry="9"
        fill="#48262C" stroke="#A96670" stroke-width="1.1"/>
      <circle cx="276" cy="146" r="1.15" fill="#D7BEC1"/>
      <circle cx="279" cy="144" r="1.15" fill="#D7BEC1"/>
      <circle cx="282" cy="144" r="1.15" fill="#D7BEC1"/>
      <circle cx="285" cy="146" r="1.15" fill="#D7BEC1"/>
    </g>'''

    # No background rectangle: GitHub's page color shows through.
    return f'''<svg xmlns="http://www.w3.org/2000/svg"
      width="900" height="320" viewBox="0 0 900 320"
      role="img"
      aria-label="Nirmal Kharal: {streak} day contribution streak,
      all-time high {longest} days">
      <title>Nirmal's Spider Streak</title>

      <rect x="28" y="24" width="4" height="15"
        rx="2" fill="#E34454"/>
      <text x="43" y="37" font-size="14" font-weight="700"
        fill="{ink}" font-family="DejaVu Sans,Arial,sans-serif">
        SPIDER STREAK
      </text>

      <g>{''.join(web)}{''.join(nodes)}{spider}</g>

      <text x="280" y="296" text-anchor="middle"
        font-size="11" fill="{muted}"
        font-family="DejaVu Sans,Arial,sans-serif">
        35 DAYS · INNER → OUTER · OUTLINED = STREAK
      </text>

      <path d="M527 71V274" stroke="{divider}" stroke-width="1"/>

      <text x="566" y="102" font-size="13" font-weight="700"
        fill="{muted}" font-family="DejaVu Sans,Arial,sans-serif">
        STREAK · DAYS IN A ROW
      </text>

      <text x="557" y="212" font-size="116" font-weight="800"
        fill="{ink}" font-family="DejaVu Sans,Arial,sans-serif">
        {streak}
      </text>

      <path d="M566 231H852" stroke="#D83A4C" stroke-width="2"/>

      <text x="566" y="267" font-size="15" fill="{ink}"
        font-family="DejaVu Sans,Arial,sans-serif">
        ALL-TIME HIGH · {longest} DAYS
      </text>
    </svg>'''


if __name__ == "__main__":
    today = dt.datetime.now(ZoneInfo("Asia/Kathmandu")).date()
    days = fetch_days()

    dark_output = Path("assets/spider-streak-dark.svg")
    light_output = Path("assets/spider-streak-light.svg")

    dark_output.parent.mkdir(parents=True, exist_ok=True)

    dark_output.write_text(
        render(days, today, theme="dark"),
        encoding="utf-8",
    )
    light_output.write_text(
        render(days, today, theme="light"),
        encoding="utf-8",
    )

    print(f"Wrote {dark_output} and {light_output}")