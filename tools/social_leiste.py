#!/usr/bin/env python3
"""Setzt die Social-Leiste in den Footer JEDER Seite — und hält sie dort synchron.

Warum ein Tool und kein Handeinbau: die Seite ist statisches HTML ohne Includes, der
Footer steht also fünfmal da. Ohne dieses Skript driften die Links auseinander, sobald
sich ein Handle ändert (passiert: Instagram heißt draco.labs.germany, nicht
dracolabsgermany). Einmal hier ändern, überall gültig.

Idempotent: ein vorhandener Block wird ersetzt, nicht verdoppelt.

Die Icons sind Inline-SVG. Grafiken von Meta/ByteDance nachzuladen wäre ein
Drittanbieter-Request beim Seitenaufruf — datenschutzrechtlich unnötiger Ärger.

Das Design ist identisch zum Shop-Theme (draco-labs/shop/design/theme/assets/base.css):
monochrom, Markenfarbe erst beim Hover. Ändert sich eins, bitte das andere nachziehen.

Aufruf:  python tools/social_leiste.py [--pruefen]
"""

import re
import sys
from pathlib import Path

try:                                  # Windows-Konsole ist cp1252, ✔ wirft sonst.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent

KANAELE = [
    ("yt", "YouTube", "https://www.youtube.com/@DracoLabsGermany",
     "M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2C0 8.1 "
     "0 12 0 12s0 3.9.5 5.8a3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 "
     "2.1-2.1c.5-1.9.5-5.8.5-5.8s0-3.9-.5-5.8ZM9.6 15.6V8.4l6.3 3.6-6.3 3.6Z"),
    ("ig", "Instagram", "https://www.instagram.com/draco.labs.germany",
     "M12 2.2c3.2 0 3.6 0 4.9.07 1.2.05 1.8.25 2.2.42.6.22 1 .48 1.4.9.4.4.7.8.9 1.4.2.4.4 1 "
     ".4 2.2.1 1.3.1 1.7.1 4.9s0 3.6-.1 4.9c0 1.2-.2 1.8-.4 2.2-.2.6-.5 1-.9 1.4-.4.4-.8.7-1.4"
     ".9-.4.2-1 .4-2.2.4-1.3.1-1.7.1-4.9.1s-3.6 0-4.9-.1c-1.2 0-1.8-.2-2.2-.4-.6-.2-1-.5-1.4-.9"
     "-.4-.4-.7-.8-.9-1.4-.2-.4-.4-1-.4-2.2C2.2 15.6 2.2 15.2 2.2 12s0-3.6.1-4.9c0-1.2.2-1.8.4"
     "-2.2.2-.6.5-1 .9-1.4.4-.4.8-.7 1.4-.9.4-.2 1-.4 2.2-.4C8.4 2.2 8.8 2.2 12 2.2Zm0 3.1A6.7 "
     "6.7 0 1 0 18.7 12 6.7 6.7 0 0 0 12 5.3Zm0 11a4.3 4.3 0 1 1 4.3-4.3 4.3 4.3 0 0 1-4.3 4.3Z"
     "M19 5a1.6 1.6 0 1 1-1.6-1.6A1.6 1.6 0 0 1 19 5Z"),
    ("tt", "TikTok", "https://www.tiktok.com/@dracolabsgermany",
     "M16.6 2h-3.1v13.1a2.7 2.7 0 1 1-2.7-2.7c.2 0 .4 0 .6.1V9.3a6 6 0 0 0-.6 0 5.8 5.8 0 1 0 "
     "5.8 5.8V8.6a7 7 0 0 0 4.1 1.3V6.8a3.9 3.9 0 0 1-4.1-3.9V2Z"),
]

ANFANG = '    <nav class="social" aria-label="Draco Labs in sozialen Netzwerken">'
ENDE = "    </nav>\n"
# Ein bereits eingesetzter Block (zum Ersetzen statt Verdoppeln).
BLOCK_RE = re.compile(r'[ \t]*<nav class="social".*?</nav>\n', re.S)


def block() -> str:
    zeilen = [ANFANG]
    for css, name, url, pfad in KANAELE:
        zeilen.append(
            f'      <a href="{url}" rel="noopener" class="{css}" '
            f'aria-label="Draco Labs auf {name}">\n'
            f'        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            f'<path d="{pfad}"/></svg>\n'
            f'      </a>')
    zeilen.append(ENDE.rstrip("\n"))
    return "\n".join(zeilen) + "\n"


def main() -> None:
    pruefen = "--pruefen" in sys.argv
    neu = block()
    geaendert = fehlt = 0
    for seite in sorted(ROOT.glob("*.html")):
        text = seite.read_text(encoding="utf-8")
        if '<footer class="site">' not in text:
            continue
        vorher = text
        if BLOCK_RE.search(text):
            text = BLOCK_RE.sub(neu, text, count=1)
        else:
            # Direkt hinter das <div class="wrap"> des Footers, vor die Link-Zeile.
            text = re.sub(r'(<footer class="site">\n\s*<div class="wrap">\n)',
                          r"\1" + neu, text, count=1)
        if text == vorher:
            print(f"  =  {seite.name}")
            continue
        if pruefen:
            print(f"  ~  {seite.name} (würde geändert)")
            fehlt += 1
            continue
        seite.write_text(text, encoding="utf-8")
        print(f"  ✔  {seite.name}")
        geaendert += 1
    if pruefen:
        print(f"\n{fehlt} Seite(n) nicht auf Stand." if fehlt else "\nAlle Seiten aktuell.")
        sys.exit(1 if fehlt else 0)
    print(f"\n{geaendert} Seite(n) aktualisiert.")


if __name__ == "__main__":
    main()
