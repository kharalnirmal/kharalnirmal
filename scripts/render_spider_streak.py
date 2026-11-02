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


SPIDER_ART = '''<g id="spider-emblem" aria-hidden="true">
  <!-- Angular red spider emblem: mirrored pointed legs and compact body -->
  <g fill="url(#emblemRed)" stroke="#39080F" stroke-width="1.9" stroke-linejoin="round">
    <path d="M278 170 C259 164 247 153 225 154 L214 159 C213 135 230 99 249 76 C226 94 205 126 199 165 L218 174 C240 164 255 172 273 182Z"/>
    <path d="M282 170 C301 164 313 153 335 154 L346 159 C347 135 330 99 311 76 C334 94 355 126 361 165 L342 174 C320 164 305 172 287 182Z"/>
    <path d="M275 170 C263 155 259 140 259 122 C246 141 246 163 265 182Z"/>
    <path d="M285 170 C297 155 301 140 301 122 C314 141 314 163 295 182Z"/>
    <path d="M275 189 C249 194 236 205 217 226 L202 253 C202 229 207 215 211 204 L192 192 C191 219 190 252 211 270 C219 250 234 228 251 216 L277 198Z"/>
    <path d="M285 189 C311 194 324 205 343 226 L358 253 C358 229 353 215 349 204 L368 192 C369 219 370 252 349 270 C341 250 326 228 309 216 L283 198Z"/>
    <path d="M273 197 C254 210 243 237 246 265 C252 246 264 222 278 207Z"/>
    <path d="M287 197 C306 210 317 237 314 265 C308 246 296 222 282 207Z"/>
    <path d="M280 158 C265 158 259 167 259 182 C258 197 266 211 280 220 C294 211 302 197 301 182 C301 167 295 158 280 158Z"/>
    <path d="M277 161 L272 149 L276 141 L280 155 L284 141 L288 149 L283 161Z"/>
  </g>
  <path d="M280 180 C273 193 273 201 280 212 C287 201 287 193 280 180Z" fill="#400711" opacity=".7"/>
  <path d="M256 89 C240 113 225 143 220 159 M304 89 C320 113 335 143 340 159"
        fill="none" stroke="#FF7584" stroke-width="1.5" opacity=".7" stroke-linecap="round"/>
</g>'''


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
    thread = "#668096" if theme == "dark" else "#8399AD"
    inactive = "#435064" if theme == "dark" else "#A4ADB9"
    divider = "#668096" if theme == "dark" else "#8399AD"

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
            f'stroke="{thread}" stroke-width="1" opacity=".36" stroke-linejoin="round"/>'
        )

    for angle in angles:
        x, y = xy(151, angle)
        web.append(
            f'<line x1="{cx}" y1="{cy}" '
            f'x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{thread}" stroke-width=".9" opacity=".26"/>'
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

    spider = SPIDER_ART

    # No background rectangle: GitHub's page color shows through.
    return f'''<svg xmlns="http://www.w3.org/2000/svg"
      width="900" height="320" viewBox="0 0 900 320"
      role="img"
      aria-label="Nirmal Kharal: {streak} day contribution streak,
      all-time high {longest} days">
      <title>Nirmal's Spider Streak</title>
      <defs>
        <linearGradient id="spiderBody" x1="0" y1="0" x2="1" y2="1">
          <stop stop-color="#4A1A29"/><stop offset=".55" stop-color="#17202A"/><stop offset="1" stop-color="#090E17"/>
        </linearGradient>
        <linearGradient id="spiderMask" x1="0" y1="0" x2="1" y2="1">
          <stop stop-color="#D83B55"/><stop offset=".4" stop-color="#8F1D36"/><stop offset="1" stop-color="#131924"/>
        </linearGradient>
      <linearGradient id="emblemRed" x1="0" y1="0" x2="1" y2="1">
          <stop stop-color="#F63046"/><stop offset=".6" stop-color="#BF1025"/><stop offset="1" stop-color="#8E081B"/>
        </linearGradient>
      </defs>

      <rect x="29" y="22" width="4" height="17"
        rx="2" fill="#F04459"/>
      <text x="44" y="37" font-size="15" font-weight="700"
        letter-spacing="1" fill="{ink}" font-family="DejaVu Sans,Arial,sans-serif">
        SPIDER STREAK
      </text>
      <text x="28" y="57" font-size="10" letter-spacing=".9"
        fill="{muted}" font-family="DejaVu Sans,Arial,sans-serif">
        THE WEB NEVER SLEEPS
      </text>

      <g>{''.join(web)}{''.join(nodes)}{spider}</g>

      <text x="280" y="296" text-anchor="middle"
        font-size="11" fill="{muted}"
        font-family="DejaVu Sans,Arial,sans-serif">
        35-DAY WEB · RINGS = WEEKS
      </text>

      <path d="M527 78V276" stroke="{divider}" opacity=".46" stroke-width="1"/>

      <text x="565" y="107" font-size="13" font-weight="700"
        letter-spacing="1.1" fill="{muted}" font-family="DejaVu Sans,Arial,sans-serif">
        CURRENT STREAK
      </text>

      <text x="556" y="224" font-size="118" font-weight="800"
        fill="{ink}" font-family="DejaVu Sans,Arial,sans-serif">
        {streak}
      </text>

      <path d="M565 237H843" stroke="#F04459" stroke-width="2.5"/>

      <text x="565" y="272" font-size="13" font-weight="600"
        letter-spacing=".45" fill="{muted}" font-family="DejaVu Sans,Arial,sans-serif">
        ALL-TIME HIGH
      </text>
      <text x="839" y="272" text-anchor="end" font-size="17" font-weight="800"
        fill="{ink}" font-family="DejaVu Sans,Arial,sans-serif">
        {longest} DAYS
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