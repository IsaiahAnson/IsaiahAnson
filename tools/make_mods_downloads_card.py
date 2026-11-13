"""Draws the "mod downloads" card and the stat strip for the profile README from the live Thunderstore counts.

Usage:
    python tools/make_mods_downloads_card.py --out-dir out --readme README.md
    python tools/make_mods_downloads_card.py --out-dir out --readme README.md --counts counts.json --date 2026-11-12   (no network)

Writes downloads-dark.svg and downloads-light.svg, and with --readme also strip-dark.svg and
strip-light.svg (the four numbers under the banner; projects and field guides are counted from the
README, so they stay right as rows are added). Standard library only, so a scheduled job can run it
with no install step. If anything cannot be read the script exits with an error and writes
nothing, so the last good images stay in place.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

# (name shown on the card, Thunderstore namespace, package, game)
MODS = [
    ("REPOPerformanceKit", "Mentalize", "REPOPerformanceKit", "R.E.P.O."),
    ("REPOPathfinder", "MentalizePez", "REPOPathfinder", "R.E.P.O."),
    ("REPOBlacklist", "Mentalize", "REPOBlacklist", "R.E.P.O."),
    ("RotRadarMinimap", "Mentalize", "RotRadarMinimap", "Grain Rot"),
    ("CoinBeams", "Mentalize", "CoinBeams", "Grain Rot"),
    ("RotVitals", "Mentalize", "RotVitals", "Grain Rot"),
    ("RotDurability", "Mentalize", "RotDurability", "Grain Rot"),
    ("GripandFlip", "Mentalize", "GripAndFlip", "Grain Rot"),
    ("RotScaling", "Mentalize", "RotScaling", "Grain Rot"),
    ("CompatShield", "Mentalize", "CompatShield", "Risk of Rain 2"),
]
METRICS_URL = "https://thunderstore.io/api/v1/package-metrics/{ns}/{pkg}/"

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# Colours follow the README's other artwork: GitHub's own greys, and the orange of the Game mods section.
THEMES = {
    "dark": dict(ink="#e6edf3", muted="#8b949e", dim="#6e7681", line="#ffffff", tones=("#f0883e", "#e3b341", "#ff7b72"), wash=0.07),
    "light": dict(ink="#1f2328", muted="#59636e", dim="#818b98", line="#1f2328", tones=("#bc4c00", "#9a6700", "#cf222e"), wash=0.05),
}
W, H = 960, 282
BAR_X, BAR_W = 512, 340
STYLE = ("<style>@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
         ".bar{transform-box:fill-box;transform-origin:0 50%;animation:grow .8s cubic-bezier(.3,.7,.2,1) both}"
         "@media (prefers-reduced-motion:reduce){.bar{animation:none}}</style>")


def fetch_counts():
    counts = {}
    for _, ns, pkg, _ in MODS:
        req = urllib.request.Request(METRICS_URL.format(ns=ns, pkg=pkg),
                                     headers={"User-Agent": "downloads-card/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            counts[pkg] = int(json.load(resp)["downloads"])
    return counts


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def card(counts, as_of, theme):
    t = THEMES[theme]
    ink, muted, dim, line = t["ink"], t["muted"], t["dim"], t["line"]
    mods = sorted(((name, counts[pkg], game) for name, _, pkg, game in MODS), key=lambda m: -m[1])
    total = sum(m[1] for m in mods)
    games = {}
    for _, count, game in mods:
        n, s = games.get(game, (0, 0))
        games[game] = (n + 1, s + count)
    order = sorted(games, key=lambda g: -games[g][1])
    tone = {game: t["tones"][i % len(t["tones"])] for i, game in enumerate(order)}
    a = t["tones"][0]

    split = ", ".join(f"{g} {games[g][1]:,}" for g in order)
    summary = f"{total:,} Thunderstore downloads across {len(mods)} mods as of {as_of}: {split}."
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(summary)}">',
           f"<title>{esc(summary)}</title>", STYLE,
           f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="16" fill="{a}" fill-opacity="{t["wash"]}" stroke="{a}" stroke-opacity="0.38" stroke-width="1.5"/>',
           f'<g font-family="{FONT}">',
           # left: the total
           f'<rect x="32" y="30" width="44" height="44" rx="11" fill="{a}" fill-opacity="0.14" stroke="{a}" stroke-opacity="0.45"/>',
           f'<path d="M54 42 V58 M47.5 51.5 L54 58 L60.5 51.5 M45 63 H63" fill="none" stroke="{a}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
           f'<text x="90" y="48" font-size="12.5" font-weight="700" letter-spacing="2" fill="{a}">MOD DOWNLOADS</text>',
           f'<text x="90" y="68" font-size="13.5" fill="{muted}">{len(mods)} mods on Thunderstore</text>',
           f'<text x="30" y="136" font-size="56" font-weight="700" letter-spacing="-1" fill="{ink}">{total:,}</text>']
    for i, game in enumerate(order):
        y = 170 + 26 * i
        n, s = games[game]
        out.append(f'<circle cx="37" cy="{y - 5}" r="5" fill="{tone[game]}"/>'
                   f'<text x="50" y="{y}" font-size="14" font-weight="600" fill="{ink}">{esc(game)}</text>'
                   f'<text x="158" y="{y}" font-size="12.5" fill="{muted}">{n} mod{"" if n == 1 else "s"}</text>'
                   f'<text x="308" y="{y}" font-size="14" font-weight="700" fill="{ink}" text-anchor="end">{s:,}</text>')
    out.append(f'<text x="32" y="{170 + 26 * len(order) + 6}" font-size="12" fill="{dim}">As of {as_of} · refreshed daily</text>')
    out.append(f'<path d="M340.5 30 V{H - 30}" stroke="{line}" stroke-opacity="0.12"/>')
    # right: one bar per mod, most downloaded first
    top = max(m[1] for m in mods) or 1
    step = (H - 60) / len(mods)
    for i, (name, count, game) in enumerate(mods):
        cy = 30 + step * (i + 0.5)
        w = max(8, round(BAR_W * count / top, 1))
        out.append(f'<text x="368" y="{cy + 4.5:.1f}" font-size="13" fill="{ink}">{esc(name)}</text>'
                   f'<rect x="{BAR_X}" y="{cy - 4:.1f}" width="{BAR_W}" height="8" rx="4" fill="{line}" fill-opacity="0.07"/>'
                   f'<rect class="bar" style="animation-delay:{0.15 + 0.07 * i:.2f}s" x="{BAR_X}" y="{cy - 4:.1f}" width="{w}" height="8" rx="4" fill="{tone[game]}"/>'
                   f'<text x="928" y="{cy + 4.5:.1f}" font-size="13" font-weight="600" fill="{ink}" text-anchor="end">{count:,}</text>')
    out.append("</g>\n</svg>\n")
    return "\n".join(out)


# --- stat strip: four numbers under the banner, in the README's section colours (blue, teal, violet, orange) ---
FEDERAL_SINCE = 2022  # first federal service desk job
SW, SH = 960, 124
STRIP_TONES = {"dark": ("#58a6ff", "#3fb8af", "#a78bfa", "#f0883e"), "light": ("#0969da", "#0f766e", "#8250df", "#bc4c00")}
# 24 px line icons: a columned building, an open book, a 2x2 grid of projects, a download arrow
STRIP_ICONS = [
    '<path d="M3 9 L12 4 L21 9 Z M5.5 12 V18 M10 12 V18 M14 12 V18 M18.5 12 V18 M3 21 H21"/>',
    '<path d="M12 7 C9.5 5.2 6.5 4.8 3.5 5.3 V18.6 C6.5 18.1 9.5 18.5 12 20.2 C14.5 18.5 17.5 18.1 20.5 18.6 V5.3 C17.5 4.8 14.5 5.2 12 7 Z M12 7 V20.2"/>',
    '<rect x="4" y="4" width="6.5" height="6.5" rx="1.6"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.6"/>'
    '<rect x="4" y="13.5" width="6.5" height="6.5" rx="1.6"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.6"/>',
    '<path d="M12 4 V15 M7 10.5 L12 15 L17 10.5 M5 20 H19"/>',
]
STRIP_STYLE = ("<style>@keyframes rise{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}"
               ".c{animation:rise .7s cubic-bezier(.3,.7,.2,1) both}"
               "@media (prefers-reduced-motion:reduce){.c{animation:none}}</style>")


def readme_counts(path):
    """Project rows (one icon each) and distinct field-guide links in the README."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    projects = sum(1 for ln in text.splitlines() if ln.startswith('| <img src="assets/proj-'))
    guides = len(set(re.findall(r"https://isaiahanson\.pages\.dev/guides/[a-z0-9-]+", text)))
    if not projects or not guides:
        raise ValueError(f"README counts look wrong: {projects} projects, {guides} guides")
    return projects, guides


def strip(total, n_mods, projects, guides, theme):
    t = THEMES[theme]
    cells = [("FEDERAL IT SINCE", str(FEDERAL_SINCE), "Energy, then Treasury"),
             ("FIELD GUIDES", str(guides), "iPhone and Mac setup"),
             ("PROJECTS", str(projects), "IT tools, AI tools, mods"),
             ("MOD DOWNLOADS", f"{total:,}", f"{n_mods} mods · updated daily")]
    summary = (f"In federal IT since {FEDERAL_SINCE}. {guides} field guides. {projects} projects. "
               f"{total:,} mod downloads on Thunderstore.")
    cw = SW / len(cells)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}" role="img" aria-label="{esc(summary)}">',
           f"<title>{esc(summary)}</title>", STRIP_STYLE,
           f'<rect x="0.75" y="0.75" width="{SW - 1.5}" height="{SH - 1.5}" rx="14" fill="{t["line"]}" fill-opacity="0.025" stroke="{t["line"]}" stroke-opacity="0.13" stroke-width="1.5"/>',
           f'<g font-family="{FONT}">']
    for i, (eyebrow, value, note) in enumerate(cells):
        x, tone = cw * i, STRIP_TONES[theme][i]
        if i:
            out.append(f'<path d="M{x:.1f} 28 V{SH - 28}" stroke="{t["line"]}" stroke-opacity="0.12"/>')
        out.append(f'<g class="c" style="animation-delay:{0.1 + 0.09 * i:.2f}s">'
                   f'<rect x="{x + 24:.1f}" y="38" width="46" height="46" rx="12" fill="{tone}" fill-opacity="0.13" stroke="{tone}" stroke-opacity="0.42"/>'
                   f'<g transform="translate({x + 35:.1f} 49)" fill="none" stroke="{tone}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">{STRIP_ICONS[i]}</g>'
                   f'<text x="{x + 84:.1f}" y="42" font-size="11" font-weight="700" letter-spacing="1.3" fill="{tone}">{eyebrow}</text>'
                   f'<text x="{x + 83:.1f}" y="76" font-size="31" font-weight="700" letter-spacing="-0.6" fill="{t["ink"]}">{esc(value)}</text>'
                   f'<text x="{x + 84:.1f}" y="97" font-size="12.5" fill="{t["muted"]}">{esc(note)}</text></g>')
    out.append("</g>\n</svg>\n")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Draws the mod downloads card for the profile README.")
    ap.add_argument("--out-dir", required=True, help="folder to write downloads-dark.svg and downloads-light.svg into")
    ap.add_argument("--counts", help='JSON file of {"<package>": downloads} to use instead of asking Thunderstore')
    ap.add_argument("--date", help="date to print on the card, as YYYY-MM-DD (default: today, UTC)")
    ap.add_argument("--readme", help="the profile README; when given, also draws strip-dark.svg and strip-light.svg")
    args = ap.parse_args()

    try:
        if args.counts:
            with open(args.counts, encoding="utf-8") as f:
                counts = {pkg: int(v) for pkg, v in json.load(f).items()}
        else:
            counts = fetch_counts()
        missing = [pkg for _, _, pkg, _ in MODS if pkg not in counts]
        if missing:
            raise KeyError("no count for " + ", ".join(missing))
        projects, guides = readme_counts(args.readme) if args.readme else (0, 0)
    except Exception as err:  # network error, bad JSON, missing key, odd README: keep the old images
        print(f"Could not read the counts: {err}", file=sys.stderr)
        return 1

    day = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now(timezone.utc)
    as_of = f"{MONTHS[day.month - 1]} {day.day}, {day.year}"
    total = sum(counts[pkg] for _, _, pkg, _ in MODS)
    files = {f"downloads-{theme}.svg": card(counts, as_of, theme) for theme in THEMES}  # draw all before writing any
    if args.readme:
        files.update({f"strip-{theme}.svg": strip(total, len(MODS), projects, guides, theme) for theme in THEMES})
    os.makedirs(args.out_dir, exist_ok=True)
    for name, svg in files.items():
        with open(os.path.join(args.out_dir, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
    extra = f", {projects} projects, {guides} guides" if args.readme else ""
    print(f"wrote {len(files)} images to {args.out_dir}: {total:,} downloads{extra}, as of {as_of}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
