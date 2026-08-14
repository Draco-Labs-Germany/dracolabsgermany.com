#!/usr/bin/env python3
"""Haelt die Rechts-Links und die Copyright-Zeile im Footer JEDER Seite synchron.

Gleicher Grund wie bei header_sync.py und social_leiste.py: die Seite ist
statisches HTML ohne Includes, der Footer steht also auf jeder Seite erneut.
Ohne Tool driftet er auseinander — genau das war der Befund vom 2026-08-14:
nutzungsbedingungen.html war von keiner Seite verlinkt (verwaist), und auf
impressum/datenschutz/nutzungsbedingungen fehlte der § 19-Zusatz, den index
und alle Ratgeber tragen.

"Startseite" steht nur auf Unterseiten; auf index.html waere der Link auf
sich selbst.

Idempotent: ein vorhandener Block wird ersetzt, nicht verdoppelt.

Aufruf:  python tools/footer_links.py [--pruefen]
"""

import re
import sys
from pathlib import Path

try:                                  # Windows-Konsole ist cp1252, § wirft sonst.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent

# (Ziel, Beschriftung) — Reihenfolge = Reihenfolge im Footer.
LINKS = [
    ("index.html", "Startseite"),
    ("impressum.html", "Impressum"),
    ("datenschutz.html", "Datenschutz"),
    ("nutzungsbedingungen.html", "Nutzungsbedingungen"),
]

COPYRIGHT = "© 2026 Draco Labs Germany · Kleinunternehmer gem. § 19 UStG"

BLOCK_RE = re.compile(r'    <div class="links">.*?</div>\n', re.S)
COPY_RE = re.compile(r"    <div>©[^<]*</div>\n")


def block(ist_start: bool) -> str:
    zeilen = ['    <div class="links">']
    for ziel, name in LINKS:
        if ist_start and ziel == "index.html":
            continue
        zeilen.append(f'      <a href="{ziel}">{name}</a>')
    zeilen.append("    </div>")
    return "\n".join(zeilen) + "\n"


def main() -> None:
    pruefen = "--pruefen" in sys.argv
    geaendert = fehlt = 0
    for seite in sorted(ROOT.glob("*.html")):
        text = seite.read_text(encoding="utf-8")
        if '<footer class="site">' not in text:
            continue
        vorher = text
        neu = block(seite.name == "index.html")
        if BLOCK_RE.search(text):
            text = BLOCK_RE.sub(neu, text, count=1)
        else:                        # Footer ohne Link-Block: vor die Copyright-Zeile.
            text = COPY_RE.sub(neu + r"\g<0>", text, count=1)
        text = COPY_RE.sub(f"    <div>{COPYRIGHT}</div>\n", text, count=1)
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
