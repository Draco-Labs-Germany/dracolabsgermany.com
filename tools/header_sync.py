#!/usr/bin/env python3
"""Haelt die Navigation im Kopf JEDER Seite synchron.

Warum ein Tool und kein Handeinbau: die Seite ist statisches HTML ohne Includes,
der <header class="site"> steht also auf jeder Seite erneut.  Kommt eine Rubrik
dazu (zuletzt "Neuigkeiten"), muesste man sonst ein Dutzend Dateien einzeln
anfassen, und check_ratgeber.py meldet danach zu Recht eine Kanon-Abweichung.
Die Menuepunkte stehen einmal in MENUE; das Skript schreibt daraus den <nav>
jeder Seite.

Auf der Startseite sind die Ziele reine Anker (#ratgeber), auf allen anderen
Seiten muessen sie auf index.html zeigen (index.html#ratgeber).  Genau diese
Unterscheidung nimmt das Skript ab; check_ratgeber.py rechnet sie beim
Kanon-Vergleich wieder heraus.

Idempotent: ein vorhandener <nav> wird ersetzt, nicht verdoppelt.

Aufruf:  python tools/header_sync.py [--pruefen]
"""

import re
import sys
from pathlib import Path

try:                                  # Windows-Konsole ist cp1252, ✔ wirft sonst.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent

# (Anker ohne #, Beschriftung) — Reihenfolge = Reihenfolge im Menue.
MENUE = [
    ("leistungen", "Leistungen"),
    ("neuigkeiten", "Neuigkeiten"),
    ("ratgeber", "Ratgeber"),
    ("ueber", "Über uns"),
    ("kontakt", "Kontakt"),
]

# Der auskommentierte Baustelle-Punkt bleibt erhalten: er wird bewusst
# reaktiviert, wenn die Frame-Serie live geht.
KOMMENTAR = ("      <!-- <a href=\"{p}#baustelle\">Baustelle</a> reaktivieren, "
             "wenn die Serie kurz vor Frame-Go-live released wird -->")

NAV_RE = re.compile(r"[ \t]*<nav>.*?</nav>\n", re.S)


def block(startseite: bool) -> str:
    praefix = "" if startseite else "index.html"
    zeilen = ["    <nav>", KOMMENTAR.format(p=praefix)]
    for anker, text in MENUE:
        zeilen.append(f'      <a href="{praefix}#{anker}">{text}</a>')
    zeilen.append("    </nav>")
    return "\n".join(zeilen) + "\n"


def main() -> None:
    pruefen = "--pruefen" in sys.argv
    geaendert = fehlt = 0
    for seite in sorted(ROOT.glob("*.html")):
        text = seite.read_text(encoding="utf-8")
        if '<header class="site">' not in text:
            continue
        kopf = re.search(r'<header class="site">.*?</header>', text, re.S)
        if not kopf or not NAV_RE.search(kopf.group(0)):
            print(f"  !  {seite.name}: kein <nav> im Kopf, uebersprungen")
            continue
        neuer_kopf = NAV_RE.sub(block(seite.name == "index.html"),
                                kopf.group(0), count=1)
        if neuer_kopf == kopf.group(0):
            print(f"  =  {seite.name}")
            continue
        if pruefen:
            print(f"  ~  {seite.name} (würde geändert)")
            fehlt += 1
            continue
        text = text[:kopf.start()] + neuer_kopf + text[kopf.end():]
        seite.write_text(text, encoding="utf-8")
        print(f"  ✔  {seite.name}")
        geaendert += 1

    if pruefen:
        print(f"\n{fehlt} Seite(n) nicht auf Stand." if fehlt else "\nAlle Seiten aktuell.")
        sys.exit(1 if fehlt else 0)
    print(f"\n{geaendert} Seite(n) aktualisiert." if geaendert else "\nNichts zu tun.")


if __name__ == "__main__":
    main()
