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


SPIDER_ART = '''<g id="spiderman-mask" aria-hidden="true">
  <!-- Recognizable red mask silhouette with web strands and expressive white lenses -->
  <circle cx="280" cy="166" r="57" fill="none" stroke="#ED3D57" stroke-width="1.4" opacity=".28"/>
  <path d="M242 245 C240 224 252 209 264 203 L273 195 L287 195 L297 203 C309 209 320 225 318 245 Z"
        fill="#101F35" stroke="#D43754" stroke-width="2.3" stroke-linejoin="round"/>
  <path d="M243 243 C248 223 255 216 266 210 L270 221 L259 245 Z" fill="#D52D48"/>
  <path d="M317 243 C312 223 305 216 294 210 L290 221 L301 245 Z" fill="#D52D48"/>
  <path d="M265 209 L280 223 L295 209" fill="none" stroke="#EA4B61" stroke-width="1.5"/>
  <path d="M278 219 Q280 215 282 219 L283 226 L280 230 L277 226Z" fill="#DB304A"/>
  <path d="M278 223 l-7 -5 m7 6 l-10 0 m9 3 l-8 6 m13 -10 l7 -5 m-7 6 l10 0 m-9 3 l8 6" fill="none" stroke="#F1455C" stroke-width="1.1" stroke-linecap="round"/>
  <path d="M271 190 L269 208 L280 215 L291 208 L289 190 Z" fill="#B82038" stroke="#10151D" stroke-width="2"/>
  <path d="M280 111 C258 111 248 128 246 149 C244 168 254 186 267 194 C276 200 284 200 293 194 C306 186 316 168 314 149 C312 128 302 111 280 111Z"
        fill="url(#heroMask)" stroke="#0F1520" stroke-width="4.2" stroke-linejoin="round"/>
  <path d="M256 135 Q262 117 277 117" fill="none" stroke="#FF6479" stroke-width="2.1" opacity=".7" stroke-linecap="round"/>
  <g stroke="#611424" stroke-width="1.35" opacity=".85" fill="none" stroke-linecap="round">
    <path d="M280 114L280 193 M280 141L249 128 M280 141L311 128 M280 141L247 147 M280 141L313 147 M280 141L251 170 M280 141L309 170 M280 141L266 191 M280 141L294 191"/>
    <path d="M253 131Q280 144 307 131 M248 145Q280 159 312 145 M249 164Q280 173 311 164 M259 182Q280 187 301 182"/>
  </g>
  <path d="M252 146 Q263 145 276 154 Q274 166 266 171 Q256 169 251 161Z" fill="#F7FBFF" stroke="#0A111D" stroke-width="5" stroke-linejoin="round"/>
  <path d="M308 146 Q297 145 284 154 Q286 166 294 171 Q304 169 309 161Z" fill="#F7FBFF" stroke="#0A111D" stroke-width="5" stroke-linejoin="round"/>
  <path d="M255 151 Q264 152 272 157 M305 151 Q296 152 288 157" fill="none" stroke="#BEE7F2" stroke-width="1.3" opacity=".8"/>
  <path d="M273 181 Q280 183 287 181" fill="none" stroke="#8B1B2E" stroke-width="1.5"/>
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
      <linearGradient id="heroMask" x1="0" y1="0" x2="1" y2="1">
          <stop stop-color="#FC405B"/><stop offset=".45" stop-color="#D32A46"/><stop offset="1" stop-color="#9F1F3B"/>
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