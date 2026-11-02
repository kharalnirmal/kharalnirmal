"""Generate a dynamically updated spider-themed GitHub streak card.

The SVG bundles an optimized spider image with editable SVG streak and contribution
markers. The artwork is included locally so scheduled actions need no third-party
image host. Both theme variants intentionally use the approved black/red style.
"""

import base64
import datetime as dt
import json
import math
import os
from pathlib import Path
import urllib.request
from zoneinfo import ZoneInfo

USERNAME = "kharalnirmal"
CX, CY = 275, 165

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
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": "spider-streak-readme",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors") or not result.get("data", {}).get("user"):
        raise RuntimeError(f"Contribution query failed: {result.get('errors')}")
    return result["data"]["user"]


def fetch_days():
    """Fetch the full calendar year by year instead of just the latest year."""
    years = sorted(set(graphql_user(YEARS_QUERY, {"login": USERNAME})[
        "contributionsCollection"]["contributionYears"]))
    now = dt.datetime.now(dt.timezone.utc)
    days = {}
    for year in years:
        start = dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc)
        end = min(dt.datetime(year + 1, 1, 1, tzinfo=dt.timezone.utc)
                  - dt.timedelta(seconds=1), now)
        if start > end:
            continue
        years_data = graphql_user(YEAR_QUERY, {
            "login": USERNAME,
            "from": start.isoformat().replace("+00:00", "Z"),
            "to": end.isoformat().replace("+00:00", "Z"),
        })
        for week in years_data["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                date = dt.date.fromisoformat(day["date"])
                if date.year == year:
                    days[date] = day["contributionCount"]
    return days


def streak_stats(days, today):
    """Return current streak, all-time high, and current-streak dates."""
    cursor = today if days.get(today, 0) > 0 else today - dt.timedelta(days=1)
    current = 0
    streak_dates = set()
    while days.get(cursor, 0) > 0:
        current += 1
        streak_dates.add(cursor)
        cursor -= dt.timedelta(days=1)

    longest = 0
    run = 0
    previous = None
    for date, count in sorted(days.items()):
        if date > today or count <= 0:
            continue
        run = run + 1 if previous is not None and date - previous == dt.timedelta(days=1) else 1
        longest = max(longest, run)
        previous = date
    return current, longest, streak_dates


PORTRAIT_BASE64 = Path("assets/spider-portrait.webp.b64").read_text(encoding="ascii").strip()

legs = [
('M262 179 C247 163 224 137 195 127 L166 113','M262 179 C249 164 223 139 195 127 L166 113'),
('M259 188 C240 175 212 165 183 167 L148 150','M259 188 C240 175 212 165 183 167 L148 150'),
('M259 201 C236 206 208 215 191 231 L167 245','M259 201 C236 206 208 215 191 231 L167 245'),
('M263 214 C249 229 231 251 215 260 L204 277','M263 214 C249 229 231 251 215 260 L204 277'),
]
paths=[]
for path,_ in legs:
    for mirror in (False,True):
        transform=f'transform="translate({2*CX},0) scale(-1,1)"' if mirror else ''
        paths.append(f'<g {transform}><path d="{path}" fill="none" stroke="#03050A" stroke-width="11" stroke-linejoin="round" stroke-linecap="round"/><path d="{path}" fill="none" stroke="url(#legRed)" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/><path d="{path}" fill="none" stroke="#FF8995" stroke-opacity=".36" stroke-width=".9" stroke-linejoin="round"/></g>')
art='''<g opacity=".85" filter="url(#spiderShadow)"><ellipse cx="275" cy="169" rx="62" ry="67" fill="#E52243" /></g>'''+''.join(paths)+'''<g id="real-spider">
<!-- upper abdomen with subtle surface texture and veins -->
<ellipse cx="275" cy="149" rx="37" ry="43" fill="url(#abdomen)" stroke="#671B2B" stroke-width="2.8"/>
<path d="M275 109 C269 124 264 134 263 155 C261 168 267 177 275 186" fill="none" stroke="#FF4257" stroke-width="2.6" opacity=".83"/>
<path d="M276 127 C283 141 288 156 282 177 M275 143 L257 132 M276 152 L291 139 M273 160 L252 151 M278 169 L297 157" fill="none" stroke="#C51E39" stroke-width="1.3" opacity=".70"/>
<ellipse cx="264" cy="135" rx="6" ry="17" fill="#FF6A75" opacity=".14" transform="rotate(22 264 135)" />
<ellipse cx="275" cy="202" rx="29" ry="25" fill="url(#thorax)" stroke="#651825" stroke-width="2.5"/>
<path d="M254 191 Q275 183 295 191 M256 212 Q275 221 293 211" stroke="#C72A44" opacity=".6" stroke-width="1.4" fill="none"/>
<g fill="#E5D8DE"><circle cx="264" cy="197" r="2.4"/><circle cx="272" cy="193" r="2.2"/><circle cx="280" cy="193" r="2.2"/><circle cx="288" cy="198" r="2.4"/></g>
<g fill="none" stroke="#E42A47" stroke-width="3" stroke-linecap="round"><path d="M268 221 Q266 233 271 237"/><path d="M282 221 Q284 233 279 237"/></g>
<path d="M273 222 L275 230 L277 222" fill="#E41D3B"/>
</g>'''

def render(days, today, theme="dark"):
  if theme not in ("dark", "light"):
      raise ValueError("theme must be dark or light")
  streak, high, _ = streak_stats(days, today)
  counts = [days.get(today - dt.timedelta(days=34 - i), 0) for i in range(35)]
  days = counts
  defs='''<defs>
    <radialGradient id="bg"><stop stop-color="#1A070A"/><stop offset="1" stop-color="#06070A"/></radialGradient>
    <radialGradient id="abdomen" cx="42%" cy="22%" r="75%"><stop stop-color="#A82035"/><stop offset=".27" stop-color="#3D1820"/><stop offset=".63" stop-color="#0F1119"/><stop offset="1" stop-color="#03060C"/></radialGradient>
    <radialGradient id="thorax" cx="40%" cy="30%" r="75%"><stop stop-color="#51505A"/><stop offset=".5" stop-color="#161820"/><stop offset="1" stop-color="#07090E"/></radialGradient>
    <linearGradient id="legRed"><stop stop-color="#D4203D"/><stop offset=".45" stop-color="#7B1428"/><stop offset="1" stop-color="#E02842"/></linearGradient>
    <linearGradient id="statRed" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#FF5265"/><stop offset="1" stop-color="#D70828"/></linearGradient>
    <filter id="spiderShadow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="17"/></filter>
    <filter id="dotGlow" x="-120%" y="-120%" width="340%" height="340%"><feGaussianBlur stdDeviation="4"/></filter>
    </defs>'''
  web=[]
  for r in [55,76,96,116,139]:
      points=[]
      for i in range(12):
          a=-math.pi/2+i*math.tau/12
          points.append((CX+r*math.cos(a),CY+r*math.sin(a)))
      d=' '.join((('M' if j==0 else 'L')+f'{x:.1f},{y:.1f}') for j,(x,y) in enumerate(points))+' Z'
      web.append(f'<path d="{d}" fill="none" stroke="#8F1A2E" stroke-width=".75" opacity=".40"/>')
  for i in range(12):
      a=-math.pi/2+i*math.tau/12
      x=CX+140*math.cos(a);y=CY+140*math.sin(a)
      web.append(f'<path d="M{CX},{CY} L{x:.1f},{y:.1f}" fill="none" stroke="#9C2239" stroke-width=".65" opacity=".36"/>')
  for i,n in enumerate(days):
      a=-math.pi/2+i*math.tau/35
      x=CX+143*math.cos(a);y=CY+143*math.sin(a)
      if n:
          web.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.8" fill="#E82540" opacity=".42" filter="url(#dotGlow)"/><circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#F52B47"/>')
      else:
          web.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="#372328"/>')
  return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="320" viewBox="0 0 900 320" role="img" aria-label="Current streak {streak} days; all-time high {high} days">
{defs}
<rect width="900" height="320" fill="#050507"/>
<rect x="1.5" y="1.5" width="897" height="317" rx="20" fill="none" stroke="#8B1529" stroke-width="1.1"/>
<text x="38" y="36" fill="#EBE9EC" font-size="17" font-weight="700" letter-spacing="2.3" font-family="Arial,sans-serif">SPIDER</text>
<text x="114" y="36" fill="#E92A48" font-size="17" font-weight="700" letter-spacing="2.3" font-family="Arial,sans-serif">STREAK</text>
<rect x="24" y="20" width="4" height="19" rx="2" fill="#EC2342"/>
<g>{''.join(web)}</g>{art}
<!-- The authored raster is bundled within the SVG, not fetched remotely. -->
<image x="146" y="68" width="260" height="240" href="data:image/webp;base64,{PORTRAIT_BASE64}"/>
<path d="M502 57V270" stroke="#A52338" stroke-width=".9" opacity=".65"/>
<text x="699" y="94" text-anchor="middle" fill="#BEB9BD" font-size="21" font-weight="600" letter-spacing="3" font-family="Arial,sans-serif">CURRENT STREAK</text>
<text x="699" y="215" text-anchor="middle" fill="url(#statRed)" font-size="118" font-weight="800" font-family="Arial,sans-serif">{streak}</text>
<path d="M574 231H820" stroke="#B71D32" stroke-width="1.5"/>
<text x="558" y="271" fill="#BEB9BD" font-size="16" letter-spacing="1.6" font-family="Arial,sans-serif">ALL-TIME HIGH</text>
<text x="823" y="271" text-anchor="end" fill="#E52742" font-size="19" font-weight="700" font-family="Arial,sans-serif">{high} DAYS</text>
</svg>'''


if __name__ == "__main__":
    today = dt.datetime.now(ZoneInfo("Asia/Kathmandu")).date()
    days = fetch_days()
    Path("assets").mkdir(exist_ok=True)
    for theme in ("dark", "light"):
        path = Path(f"assets/spider-streak-{theme}.svg")
        path.write_text(render(days, today, theme), encoding="utf-8")
        print("Updated", path)