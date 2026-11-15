#!/usr/bin/env python3
"""
Builds dark_mode.svg and light_mode.svg for a GitHub profile README.

Everything you would want to change lives in the CONFIG block below.
The ASCII art on the left is read from ascii.txt.

Usage:
    python build.py --offline          # local preview with sample numbers, no network
    GITHUB_USER=you python build.py    # live numbers from the GitHub API
    (in GitHub Actions the workflow sets GITHUB_USER and GITHUB_TOKEN for you)

Standard library only, nothing to install.
"""
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

# ----------------------------------------------------------------------------
# CONFIG: edit this part
# ----------------------------------------------------------------------------
TITLE = "vince@moonlightarray"

# Each section is (heading or None, [(key, value), ...]).
# A key may contain dots, e.g. "Languages.Real".
# An entry of None gives an empty line.
# The special value "{uptime}" is replaced by your time on GitHub.
SECTIONS = [
    (None, [
        ("OS", "macOS, Linux"),
        ("Uptime", "{uptime}"),
        ("Host", "Moonlight Array, Arnhem NL"),
        ("Kernel", "Solo founder, building OxidDB"),
        ("IDE", "VS Code, Claude Code"),
        None,
        ("Languages.Programming", "Rust, Python, TypeScript"),
        ("Languages.Real", "Dutch, English, Mandarin"),
        None,
        ("Projects.OxidDB", "Neurosymbolic database engine"),
        ("Projects.Book", "Future Ready"),
        ("Studies", "MSc Applied Data Science, HAN"),
    ]),
    ("Contact", [
        ("Website", "vincentbrand.com"),
        ("Company", "moonlightarray.com"),
        ("LinkedIn", "your-linkedin-handle"),
    ]),
]

SHOW_GITHUB_STATS = True
AVG_WEEKS = 52  # "Weekly avg" is commits over this many past weeks, divided by it

THEMES = {
    "dark_mode.svg": {
        "bg": "#161b22", "text": "#c9d1d9", "key": "#ffa657",
        "value": "#a5d6ff", "dots": "#616e7f",
        "art": "#c9d1d9", "accent": "#d9743f",
    },
    "light_mode.svg": {
        "bg": "#f6f8fa", "text": "#24292f", "key": "#953800",
        "value": "#0a3069", "dots": "#c2cfde",
        "art": "#143f61", "accent": "#9e5333",
    },
}

# Layout. COLS is the width of the right-hand column in characters.
COLS = 60
ART_FILE = "ascii.txt"
ACCENT_CHARS = "%=~"  # characters in ascii.txt drawn in the accent colour ("" to switch off)
ART_X, TEXT_X = 15, 390
WIDTH, LINE_H, FONT_SIZE = 985, 20, 16
RULE_CHAR = "-"
# ----------------------------------------------------------------------------


def api(path, token):
    req = urllib.request.Request("https://api.github.com" + path)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-readme-build")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def uptime_since(created, today=None):
    today = today or datetime.date.today()
    months = (today.year - created.year) * 12 + today.month - created.month
    if today.day < created.day:
        months -= 1
    years, months = divmod(max(months, 0), 12)
    plural = lambda n, word: "{} {}{}".format(n, word, "" if n == 1 else "s")
    return "{}, {} on GitHub".format(plural(years, "year"), plural(months, "month"))


def fetch_stats(user, token):
    """Public numbers only: owned repos, stars on them, followers, commits."""
    quoted = urllib.parse.quote(user)
    profile = api("/users/" + quoted, token)
    stars, page = 0, 1
    while True:
        repos = api("/users/{}/repos?type=owner&per_page=100&page={}".format(quoted, page), token)
        stars += sum(r["stargazers_count"] for r in repos)
        if len(repos) < 100:
            break
        page += 1
    def commit_count(since=None):
        q = "author:" + user + (" author-date:>=" + since.isoformat() if since else "")
        return api("/search/commits?per_page=1&q=" + urllib.parse.quote(q), token)["total_count"]

    today = datetime.datetime.now(datetime.timezone.utc).date()
    commits = commit_count()
    last_week = commit_count(today - datetime.timedelta(days=7))
    weekly_avg = commit_count(today - datetime.timedelta(weeks=AVG_WEEKS)) / AVG_WEEKS
    created = datetime.date.fromisoformat(profile["created_at"][:10])
    return {
        "uptime": uptime_since(created),
        "repos": profile["public_repos"],
        "stars": stars,
        "followers": profile["followers"],
        "commits": commits,
        "last_week": last_week,
        "weekly_avg": weekly_avg,
    }


SAMPLE_STATS = {"uptime": "9 years, 4 months on GitHub", "repos": 42,
                "stars": 128, "followers": 64, "commits": 3210,
                "last_week": 37, "weekly_avg": 24.6}


def span(text, cls=None):
    if not text:
        return ""
    if cls:
        return '<tspan class="{}">{}</tspan>'.format(cls, escape(text))
    return escape(text)


def art_row(row):
    """Colours runs of ACCENT_CHARS with the accent class."""
    out, run, accent = [], "", False
    for ch in row + "\0":
        is_accent = ch in ACCENT_CHARS
        if ch == "\0" or (is_accent != accent and ch != " "):
            out.append(span(run, "accent" if accent else None))
            run, accent = "", is_accent
        run += ch if ch != "\0" else ""
    return "".join(out)


def key_spans(key):
    return ".".join(span(part, "key") for part in key.split("."))


def kv_line(key, value, width=COLS):
    """'. Key: ........ value' padded with dots to exactly `width` characters."""
    value = str(value)
    dots = width - len(". ") - len(key) - len(":") - len(value) - 2
    if dots < 1:
        sys.exit("Line too long for the column ({} > {} chars): {}: {}".format(
            width - dots + 1, width, key, value))
    return (span(". ", "dots") + key_spans(key) + ":"
            + span(" " + "." * dots + " ", "dots") + span(value, "value"))


def rule_line(label):
    return span(label + " ") + span(RULE_CHAR * (COLS - len(label) - 1), "dots")


def build_lines(stats):
    lines = []
    for index, (heading, entries) in enumerate(SECTIONS):
        if index == 0:
            lines.append(rule_line(TITLE))
        else:
            lines += ["", rule_line("- " + heading)]
        for entry in entries:
            if entry is None:
                lines.append(span(". ", "dots"))
            else:
                lines.append(kv_line(entry[0], entry[1].replace("{uptime}", stats["uptime"])))
    if SHOW_GITHUB_STATS:
        left, right = (COLS - 3) // 2, COLS - 3 - (COLS - 3) // 2
        fmt = "{:,}".format
        lines += ["", rule_line("- GitHub Stats")]
        lines.append(kv_line("Repos", fmt(stats["repos"]), left) + " | "
                     + kv_line("Stars", fmt(stats["stars"]), right))
        lines.append(kv_line("Commits", fmt(stats["commits"]), left) + " | "
                     + kv_line("Followers", fmt(stats["followers"]), right))
        lines.append(kv_line("Last week", fmt(stats["last_week"]), left) + " | "
                     + kv_line("Weekly avg", "{:,.1f}".format(stats["weekly_avg"]), right))
    return lines


def render(theme, art, lines):
    rows = max(len(art), len(lines))
    height = rows * LINE_H + 30
    out = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        '<svg xmlns="http://www.w3.org/2000/svg" width="{w}px" height="{h}px" '
        'viewBox="0 0 {w} {h}" font-size="{f}px" '
        'font-family="Consolas,Menlo,\'DejaVu Sans Mono\',\'Liberation Mono\',monospace">'
        .format(w=WIDTH, h=height, f=FONT_SIZE),
        "<style>",
        ".key {{fill: {key};}} .value {{fill: {value};}} .dots {{fill: {dots};}} "
        ".accent {{fill: {accent};}}".format(**theme),
        "text, tspan {white-space: pre;}",
        "</style>",
        '<rect width="{}px" height="{}px" fill="{}" rx="15"/>'.format(WIDTH, height, theme["bg"]),
    ]
    for x, fill, block in ((ART_X, theme["art"], [art_row(row) for row in art]),
                           (TEXT_X, theme["text"], lines)):
        out.append('<text xml:space="preserve" fill="{}">'.format(fill))
        for i, content in enumerate(block):
            if content:
                out.append('<tspan x="{}" y="{}">{}</tspan>'.format(x, 30 + i * LINE_H, content))
        out.append("</text>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    if "--offline" in sys.argv:
        stats = SAMPLE_STATS
    else:
        user = os.environ.get("GITHUB_USER")
        if not user:
            sys.exit("Set GITHUB_USER, or run with --offline for a preview.")
        stats = fetch_stats(user, os.environ.get("GITHUB_TOKEN"))
    with open(os.path.join(here, ART_FILE), encoding="utf-8") as f:
        art = f.read().rstrip("\n").split("\n")
    lines = build_lines(stats)
    for filename, theme in THEMES.items():
        with open(os.path.join(here, filename), "w", encoding="utf-8") as f:
            f.write(render(theme, art, lines))
        print("wrote", filename)


if __name__ == "__main__":
    main()
