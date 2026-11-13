"""Draws the "mod downloads" card for the profile README from the live Thunderstore counts.

Usage:
    python tools/make_mods_downloads_card.py --out-dir out
    python tools/make_mods_downloads_card.py --out-dir out --counts counts.json --date 2026-11-12   (no network)

Writes downloads-dark.svg and downloads-light.svg. Standard library only, so a scheduled job can
run it with no install step. If any count cannot be read the script exits with an error and
writes nothing, so the last good cards stay in place.
"""
import argparse
import json
import os
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


def main():
    ap = argparse.ArgumentParser(description="Draws the mod downloads card for the profile README.")
    ap.add_argument("--out-dir", required=True, help="folder to write downloads-dark.svg and downloads-light.svg into")
    ap.add_argument("--counts", help='JSON file of {"<package>": downloads} to use instead of asking Thunderstore')
    ap.add_argument("--date", help="date to print on the card, as YYYY-MM-DD (default: today, UTC)")
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
    except Exception as err:  # network error, bad JSON, missing key: keep the old cards
        print(f"Could not read the counts: {err}", file=sys.stderr)
        return 1

    day = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now(timezone.utc)
    as_of = f"{MONTHS[day.month - 1]} {day.day}, {day.year}"
    cards = {theme: card(counts, as_of, theme) for theme in THEMES}  # draw both before writing either
    os.makedirs(args.out_dir, exist_ok=True)
    for theme, svg in cards.items():
        with open(os.path.join(args.out_dir, f"downloads-{theme}.svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
    print(f"wrote 2 cards to {args.out_dir}: {sum(counts[pkg] for _, _, pkg, _ in MODS):,} downloads, as of {as_of}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
