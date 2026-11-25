#!/usr/bin/env python3
"""
Builds dark_mode.svg and light_mode.svg: a "neural brain" GitHub profile card
with live stats, including private contributions.

Usage:
    python build.py --offline          # local preview with sample numbers, no network
    GITHUB_USER=you GITHUB_TOKEN=... python build.py

Commit numbers follow GitHub's own contribution counting (the same data as the
graph on your profile): public commits plus your private contribution count.
SETUP.md explains the token and the profile setting this needs.

Standard library only, nothing to install.
"""
import datetime
import json
import math
import os
import random
import sys
import urllib.request
from xml.sax.saxutils import escape

# ----------------------------------------------------------------------------
# CONFIG: edit this part
# ----------------------------------------------------------------------------
NAME = "Vincent Brand"
LINES = [
    "Founder from the Netherlands",
    "Building Oxid-DB, the neurosymbolic database",
]
# Shown in code style above the name. Words in QUERY_KEYWORDS get the accent colour.
QUERY = 'FIND ?x WHERE ?x IS-A Founder NEAR ?x TO "neurosymbolic"'
QUERY_KEYWORDS = {"FIND", "WHERE", "IS-A", "NEAR", "TO"}
# Labelled "symbol" nodes inside the brain (keep it to 4-6 short words).
SYMBOLS = ["Rust", "Python", "OxQL", "TypeScript", "OxidDB"]
LINKS = ["vincentbrand.com", "oxid-db.com", "linkedin.com/in/vincentbrand-nl"]  # keep it short, the row is 444px wide

THEMES = {
    "dark_mode.svg": {
        "bg": "#0a0a0b", "border": "#23262b", "text": "#f2f4f6", "muted": "#8b949e",
        "node": "#6fa8d6", "edge": "#2f6690", "edge_opacity": "0.55",
        "accent": "#e07b45", "glow": "#143f61", "glow_opacity": "0.55", "bar": "#2b5777",
    },
    "light_mode.svg": {
        "bg": "#f9fafb", "border": "#d9dee4", "text": "#0d2233", "muted": "#5c6b78",
        "node": "#143f61", "edge": "#143f61", "edge_opacity": "0.26",
        "accent": "#9e5333", "glow": "#cfe0ee", "glow_opacity": "0.9", "bar": "#a9c0d3",
    },
}

WIDTH, HEIGHT = 900, 424
NEURONS = 78          # dots in the brain
SEED = 7              # change for a different brain layout
# ----------------------------------------------------------------------------

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"


# ------------------------------- GitHub data --------------------------------

def graphql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": "Bearer " + token, "User-Agent": "profile-card-build"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.load(resp)
    if body.get("errors"):
        sys.exit("GitHub API error: " + json.dumps(body["errors"], indent=2))
    return body["data"]


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


COUNTS = "totalCommitContributions restrictedContributionsCount"


def commits_in(collection):
    """Public commits plus private contributions (see the note at the top)."""
    return collection["totalCommitContributions"] + collection["restrictedContributionsCount"]


def fetch_stats(user, token):
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    base = graphql("""
      query($login: String!) {
        user(login: $login) {
          followers { totalCount }
          contributionsCollection { contributionYears }
        }
      }""", {"login": user}, token)["user"]
    if base is None:
        sys.exit("User not found: " + user)

    # Repos you own, and the stars on them.
    repos, stars, cursor = 0, 0, None
    while True:
        page = graphql("""
          query($login: String!, $cursor: String) {
            user(login: $login) {
              repositories(ownerAffiliations: OWNER, first: 100, after: $cursor) {
                totalCount
                nodes { stargazerCount }
                pageInfo { hasNextPage endCursor }
              }
            }
          }""", {"login": user, "cursor": cursor}, token)["user"]["repositories"]
        repos = page["totalCount"]
        stars += sum(node["stargazerCount"] for node in page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    # One contributions window per calendar year (the API allows one year at most),
    # plus the last 7 days, the last 30 days and the last 52 weeks.
    parts = []
    for year in base["contributionsCollection"]["contributionYears"]:
        parts.append('y{0}: contributionsCollection(from: "{0}-01-01T00:00:00Z", '
                     'to: "{0}-12-31T23:59:59Z") {{ {1} }}'.format(year, COUNTS))
    parts.append('week: contributionsCollection(from: "{}", to: "{}") {{ {} }}'.format(
        iso(now - datetime.timedelta(days=7)), iso(now), COUNTS))
    parts.append('month: contributionsCollection(from: "{}", to: "{}") {{ {} }}'.format(
        iso(now - datetime.timedelta(days=30)), iso(now), COUNTS))
    parts.append('year: contributionsCollection(from: "{}", to: "{}") {{ {} '
                 'contributionCalendar {{ weeks {{ contributionDays {{ contributionCount }} }} }} }}'
                 .format(iso(now - datetime.timedelta(weeks=52)), iso(now), COUNTS))
    data = graphql("query($login: String!) { user(login: $login) { %s } }" % " ".join(parts),
                   {"login": user}, token)["user"]

    years = [value for key, value in data.items() if key.startswith("y") and key != "year"]
    public = sum(c["totalCommitContributions"] for c in years)
    private = sum(c["restrictedContributionsCount"] for c in years)
    print("all time: {:,} public commits + {:,} private contributions".format(public, private))
    if private == 0:
        print("NOTE: no private contributions returned. Check that 'Private contributions' "
              "is enabled on your profile and that PROFILE_TOKEN has the read:user scope.")

    weeks = [sum(day["contributionCount"] for day in week["contributionDays"])
             for week in data["year"]["contributionCalendar"]["weeks"]][-52:]
    return {
        "commits": public + private,
        "last_week": commits_in(data["week"]),
        "last_month": commits_in(data["month"]),
        "weekly_avg": commits_in(data["year"]) / 52,
        "repos": repos,
        "stars": stars,
        "followers": base["followers"]["totalCount"],
        "weeks": weeks,
        "synced": now.date().isoformat(),
    }


def sample_stats():
    rng = random.Random(3)
    weeks = [max(0, int(rng.gauss(24, 14))) for _ in range(52)]
    return {"commits": 4812, "last_week": 37, "last_month": 112, "weekly_avg": 24.6,
            "repos": 42, "stars": 128, "followers": 64, "weeks": weeks,
            "synced": datetime.date.today().isoformat()}


# ------------------------------- the brain ----------------------------------

# Side view of a brain in a 300 x 250 box, front on the left.
OUTLINE = [(38, 150), (28, 112), (48, 66), (95, 36), (150, 22), (205, 30), (250, 55),
           (276, 95), (279, 136), (264, 166), (252, 192), (222, 207), (192, 197),
           (174, 181), (150, 191), (110, 193), (74, 181)]
STEM = [(196, 212), (190, 230), (183, 247)]
BRAIN_X, BRAIN_Y, BRAIN_SCALE = 20, 46, 1.3


def smooth_path(points):
    """Closed Catmull-Rom spline through the points, as an SVG path."""
    n = len(points)
    d = "M{:.1f},{:.1f}".format(*points[0])
    for i in range(n):
        p0, p1, p2, p3 = points[i - 1], points[i], points[(i + 1) % n], points[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += " C{:.1f},{:.1f} {:.1f},{:.1f} {:.1f},{:.1f}".format(*c1, *c2, *p2)
    return d + " Z"


def inside(point, polygon):
    x, y = point
    hit = False
    for i in range(len(polygon)):
        (x1, y1), (x2, y2) = polygon[i], polygon[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def build_brain(firing):
    """Returns nodes, edges, symbol node indexes and firing node indexes."""
    rng = random.Random(SEED)
    place = lambda p: (BRAIN_X + p[0] * BRAIN_SCALE, BRAIN_Y + p[1] * BRAIN_SCALE)
    nodes = []
    while len(nodes) < NEURONS:
        # Best-candidate sampling keeps the dots evenly spread.
        best, best_d = None, -1
        for _ in range(24):
            cand = (rng.uniform(25, 282), rng.uniform(20, 210))
            if not inside(cand, OUTLINE):
                continue
            d = min((math.dist(cand, n) for n in nodes), default=999)
            if d > best_d:
                best, best_d = cand, d
        if best:
            nodes.append(best)
    edges = set()
    for i, node in enumerate(nodes):
        near = sorted(range(len(nodes)), key=lambda j: math.dist(node, nodes[j]))[1:4]
        for j in near:
            if math.dist(node, nodes[j]) < 46:
                edges.add((min(i, j), max(i, j)))
    # Brain stem: a short chain hanging off the nearest node.
    anchor = min(range(len(nodes)), key=lambda j: math.dist(STEM[0], nodes[j]))
    for point in STEM:
        nodes.append(point)
        edges.add((anchor, len(nodes) - 1))
        anchor = len(nodes) - 1

    # Symbol nodes: spread far apart, away from the right edge so labels fit.
    pool = [i for i in range(NEURONS) if 60 < nodes[i][0] < 215 and 50 < nodes[i][1] < 180]
    symbols = [min(pool, key=lambda i: math.dist(nodes[i], (150, 110)))]
    while len(symbols) < len(SYMBOLS):
        symbols.append(max(pool, key=lambda i: min(math.dist(nodes[i], nodes[s]) for s in symbols)))
    symbols.sort(key=lambda i: nodes[i][0])

    rest = [i for i in range(NEURONS) if i not in symbols]
    rng.shuffle(rest)
    fire = rest[:firing]
    return [place(n) for n in nodes], sorted(edges), symbols, fire


def hexagon(cx, cy, r):
    pts = [(cx + r * math.sin(math.radians(a)), cy - r * math.cos(math.radians(a)))
           for a in range(0, 360, 60)]
    return " ".join("{:.1f},{:.1f}".format(*p) for p in pts)


def draw_brain(stats):
    # More commits last week means more neurons firing.
    firing = max(4, min(26, round(stats["last_week"] / 2)))
    nodes, edges, symbols, fire = build_brain(firing)
    out = ['<path d="{}" transform="translate({},{}) scale({})" class="outline"/>'.format(
        smooth_path(OUTLINE), BRAIN_X, BRAIN_Y, BRAIN_SCALE)]
    hot = set(fire) | set(symbols)
    signals = 0
    for a, b in edges:
        (x1, y1), (x2, y2) = nodes[a], nodes[b]
        line = 'x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}"'.format(x1, y1, x2, y2)
        out.append('<line {} class="edge"/>'.format(line))
        if (a in hot or b in hot) and signals < 22 and (a + b) % 2 == 0:
            out.append('<line {} class="sig" style="animation-delay:-{:.1f}s"/>'.format(
                line, (a * 7 + b * 3) % 40 / 10))
            signals += 1
    for i, (x, y) in enumerate(nodes):
        if i in symbols:
            continue
        r = 2.1 + (i * 37 % 10) / 7
        if i in fire:
            delay = (i * 13 % 30) / 10
            out.append('<g class="fire" style="animation-delay:-{:.1f}s">'
                       '<circle cx="{:.1f}" cy="{:.1f}" r="{:.1f}" class="halo"/>'
                       '<circle cx="{:.1f}" cy="{:.1f}" r="{:.1f}" class="hot"/></g>'
                       .format(delay, x, y, r * 2.8, x, y, r))
        else:
            out.append('<circle cx="{:.1f}" cy="{:.1f}" r="{:.1f}" class="node"/>'.format(x, y, r))
    for label, i in zip(SYMBOLS, symbols):
        x, y = nodes[i]
        out.append('<polygon points="{}" class="symbol"/>'.format(hexagon(x, y, 7.5)))
        out.append('<text x="{:.1f}" y="{:.1f}" class="label">{}</text>'.format(
            x + 12, y + 4, escape(label)))
    return out


# ------------------------------- the card -----------------------------------

LOGO_RING = ("M131.21,0L0,75.75v151.5l131.21,75.75,131.21-75.75V75.75L131.21,0Z"
             "M221.38,203.56l-90.17,52.06-90.17-52.06v-104.12l90.17-52.06,90.17,52.06v104.12Z")
LOGO_FACE = "0 227.26 131.21 151.5 131.21 303.01 0 227.26"


def query_spans():
    out = []
    for word in QUERY.split(" "):
        cls = ' class="kw"' if word in QUERY_KEYWORDS else ""
        out.append("<tspan{}>{}</tspan>".format(cls, escape(word)))
    return " ".join(out)


def draw_panel(stats):
    x0 = 424
    out = ['<text x="{}" y="66" class="query">{}</text>'.format(x0, query_spans()),
           '<text x="{}" y="106" class="name">{}</text>'.format(x0, escape(NAME))]
    for i, line in enumerate(LINES):
        out.append('<text x="{}" y="{}" class="line">{}</text>'.format(x0, 132 + i * 20, escape(line)))

    fmt = "{:,}".format
    tiles = [
        (fmt(stats["last_month"]), "commits, 30 days"),   # the caption row is 152px wide
        (fmt(stats["last_week"]), "last 7 days"),
        ("{:,.1f}".format(stats["weekly_avg"]), "weekly average"),
        (fmt(stats["repos"]), "repositories"),
        (fmt(stats["stars"]), "stars"),
        (fmt(stats["followers"]), "followers"),
    ]
    for i, (value, label) in enumerate(tiles):
        x, y = x0 + (i % 3) * 152, 212 + (i // 3) * 58
        cls = "num hotnum" if i == 1 else "num"
        out.append('<text x="{}" y="{}" class="{}">{}</text>'.format(x, y, cls, value))
        out.append('<text x="{}" y="{}" class="cap">{}</text>'.format(x, y + 18, label.upper()))

    # 52 weekly bars; the most recent week is highlighted.
    weeks = stats["weeks"] or [0]
    top, base, step = 318, 354, 444 / 52
    peak = max(max(weeks), 1)
    for i, count in enumerate(weeks):
        h = max(2, (base - top) * count / peak)
        cls = "bar now" if i == len(weeks) - 1 else "bar"
        out.append('<rect x="{:.1f}" y="{:.1f}" width="5.4" height="{:.1f}" rx="1.5" class="{}"/>'
                   .format(x0 + i * step, base - h, h, cls))
    out.append('<text x="{}" y="374" class="cap">52 WEEKS OF CONTRIBUTIONS</text>'.format(x0))
    out.append('<text x="{}" y="374" class="cap" text-anchor="end">SYNCED {}</text>'.format(
        x0 + 444, stats["synced"]))
    out.append('<text x="{}" y="400" class="links">{}</text>'.format(
        x0, '<tspan class="sep" dx="9">/</tspan>'.join(
            "<tspan{}>{}</tspan>".format(' dx="9"' if i else "", escape(link))
            for i, link in enumerate(LINKS))))
    # Hexagon mark, top right.
    out.append('<g transform="translate(842,34) scale(0.105)"><path d="{}" class="ring" '
               'fill-rule="evenodd"/><polygon points="{}" class="face"/></g>'.format(LOGO_RING, LOGO_FACE))
    return out


def render(theme, stats):
    css = """
text {{ font-family: {sans}; fill: {text}; }}
.query, .label, .num {{ font-family: {mono}; }}
.query {{ font-size: 12px; fill: {muted}; }}
.kw, .hotnum {{ fill: {accent}; }}
.name {{ font-size: 30px; font-weight: 700; letter-spacing: -0.5px; }}
.line {{ font-size: 14px; fill: {muted}; }}
.num {{ font-size: 26px; font-weight: 600; }}
.cap {{ font-size: 10.5px; letter-spacing: 1.1px; fill: {muted}; }}
.links {{ font-size: 12.5px; }}
.sep {{ fill: {muted}; }}
.label {{ font-size: 11px; font-weight: 600; paint-order: stroke; stroke: {bg}; stroke-width: 4px; stroke-linejoin: round; }}
.outline {{ fill: none; stroke: {edge}; stroke-opacity: 0.35; stroke-width: 1.2; stroke-dasharray: 2 5; }}
.edge {{ stroke: {edge}; stroke-opacity: {edge_opacity}; stroke-width: 1; }}
.node {{ fill: {node}; }}
.hot, .symbol, .face, .now {{ fill: {accent}; }}
.halo {{ fill: {accent}; opacity: 0.18; }}
.symbol {{ stroke: {bg}; stroke-width: 2; }}
.ring {{ fill: {text}; }}
.bar {{ fill: {bar}; }}
.sig {{ stroke: {accent}; stroke-width: 1.6; stroke-linecap: round; stroke-dasharray: 5 70; animation: flow 4s linear infinite; }}
.fire {{ animation: pulse 3s ease-in-out infinite; }}
@keyframes flow {{ to {{ stroke-dashoffset: -75; }} }}
@keyframes pulse {{ 0%, 100% {{ opacity: 0.45; }} 50% {{ opacity: 1; }} }}
@media (prefers-reduced-motion: reduce) {{ .sig, .fire {{ animation: none; }} }}
""".format(sans=SANS, mono=MONO, **theme)
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        'role="img" aria-label="{label}">'.format(
            w=WIDTH, h=HEIGHT, label=escape(
                "{}: {:,} commits in the last 30 days, {:,} in the last 7 days".format(
                    NAME, stats["last_month"], stats["last_week"]))),
        "<style>" + css + "</style>",
        '<defs><radialGradient id="glow" cx="50%" cy="50%" r="50%">'
        '<stop offset="0" stop-color="{glow}" stop-opacity="{glow_opacity}"/>'
        '<stop offset="1" stop-color="{glow}" stop-opacity="0"/></radialGradient></defs>'.format(**theme),
        '<rect x="0.5" y="0.5" width="{}" height="{}" rx="16" fill="{}" stroke="{}"/>'.format(
            WIDTH - 1, HEIGHT - 1, theme["bg"], theme["border"]),
        '<ellipse cx="215" cy="205" rx="250" ry="195" fill="url(#glow)"/>',
    ]
    out += draw_brain(stats) + draw_panel(stats)
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    if "--offline" in sys.argv:
        stats = sample_stats()
    else:
        user, token = os.environ.get("GITHUB_USER"), os.environ.get("GITHUB_TOKEN")
        if not user or not token:
            sys.exit("Set GITHUB_USER and GITHUB_TOKEN, or run with --offline for a preview.")
        stats = fetch_stats(user, token)
    for filename, theme in THEMES.items():
        with open(os.path.join(here, filename), "w", encoding="utf-8") as f:
            f.write(render(theme, stats))
        print("wrote", filename)


if __name__ == "__main__":
    main()
