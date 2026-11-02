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


SPIDER_ART = '''<g id="spider-mascot" aria-hidden="true">
  <g fill="none" stroke-linecap="round" stroke-linejoin="round">
    <g id="legs-left">
      <path d="M274 164 L260 149 L240 142 L220 112 L206 109" stroke="#131822" stroke-width="7"/>
      <path d="M274 164 L260 149 L240 142 L220 112 L206 109" stroke="#D7374C" stroke-width="2.2"/>
      <path d="M270 171 L248 163 L230 170 L207 157 L194 161" stroke="#131822" stroke-width="7"/>
      <path d="M270 171 L248 163 L230 170 L207 157 L194 161" stroke="#D7374C" stroke-width="2.2"/>
      <path d="M270 183 L250 193 L232 190 L210 208 L195 206" stroke="#131822" stroke-width="7"/>
      <path d="M270 183 L250 193 L232 190 L210 208 L195 206" stroke="#D7374C" stroke-width="2.2"/>
      <path d="M276 194 L261 213 L243 216 L229 241 L215 244" stroke="#131822" stroke-width="7"/>
      <path d="M276 194 L261 213 L243 216 L229 241 L215 244" stroke="#D7374C" stroke-width="2.2"/>
      <g fill="#F04459" stroke="#171A22" stroke-width="1.7">
        <circle cx="240" cy="142" r="3.4"/><circle cx="230" cy="170" r="3.4"/>
        <circle cx="232" cy="190" r="3.4"/><circle cx="243" cy="216" r="3.4"/>
      </g>
    </g>
    <use href="#legs-left" transform="translate(560 0) scale(-1 1)" />
  </g>
  <path d="M280 163 C265 163 263 172 264 184 C264 200 273 217 280 219 C287 217 296 200 296 184 C297 172 295 163 280 163Z"
        fill="url(#spiderBody)" stroke="#F24A62" stroke-width="2"/>
  <path d="M280 168 L280 209 M269 176 Q280 184 291 176 M270 190 Q280 198 290 190"
        fill="none" stroke="#F4556C" stroke-width="1.5" opacity=".65"/>
  <path d="M280 174 L275 186 L280 193 L285 186Z" fill="#EF3751"/>
  <path d="M280 155 C269 156 268 169 272 176 L280 179 L288 176 C292 169 291 156 280 155Z"
        fill="#CB2942" stroke="#FC6275" stroke-width="1.3"/>
  <path d="M280 134 C267 134 263 144 266 153 C270 163 276 166 280 167 C284 166 290 163 294 153 C297 144 293 134 280 134Z"
        fill="url(#spiderMask)" stroke="#FB5870" stroke-width="1.6"/>
  <path d="M280 137V161 M270 143L280 154L290 143 M267 150L279 158L291 150"
        fill="none" stroke="#BE2D46" stroke-width="1" opacity=".9"/>
  <path d="M270 150 Q272 145 278 150 Q276 155 271 155Z" fill="#F2FCFF"/>
  <path d="M290 150 Q288 145 282 150 Q284 155 289 155Z" fill="#F2FCFF"/>
  <path d="M270 150L277 153 M290 150L283 153" stroke="#C3E8F6" stroke-width=".7"/>
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