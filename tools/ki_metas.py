#!/usr/bin/env python3
"""Setzt den KI-Nutzungsvorbehalt als Meta-Tag auf jede Seite.

Befund vom 2026-08-14: die robots.txt sperrt zwar zwei Dutzend KI-Crawler, auf
Seitenebene stand aber nichts.  Damit war die robots.txt die einzige
Verteidigungslinie — und die liest ein Bot, der die Seite ueber einen Cache,
einen Datensatz oder einen Reader-Dienst bekommt, gar nicht erst.

Gesetzt werden zwei Dinge:

  * ``noai, noimageai`` im vorhandenen robots-Meta.  Die Kuerzel sind kein
    W3C-Standard, werden aber von mehreren Crawlern ausgewertet und sind die
    verbreitetste Form des Vorbehalts.
  * ``<meta name="tdm-reservation" content="1">`` nach dem TDM Reservation
    Protocol.  Das ist der maschinenlesbare Nutzungsvorbehalt, den
    § 44b Abs. 3 UrhG fuer Text- und Data-Mining verlangt — ohne ihn ist das
    Auslesen fuer Trainingszwecke schlicht erlaubt.

Die Seite bleibt normal indexierbar: das vorhandene ``index, follow`` bzw.
``noindex`` bleibt unangetastet, es kommt nur etwas dazu.

Das Shop-Pendant steht im Theme (``layout/theme.liquid``), dort genuegt eine
Stelle fuer alle Seiten.

Idempotent: bereits ausgezeichnete Seiten werden uebersprungen.

Aufruf:  python tools/ki_metas.py [--pruefen]
"""

import re
import sys
from pathlib import Path

try:                                  # Windows-Konsole ist cp1252.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent

ROBOTS_RE = re.compile(r'<meta name="robots" content="([^"]*)">')
TDM = '<meta name="tdm-reservation" content="1">'
ZUSATZ = ["noai", "noimageai"]


def umbauen(html: str) -> str:
    m = ROBOTS_RE.search(html)
    if not m:
        return html
    werte = [w.strip() for w in m.group(1).split(",") if w.strip()]
    for z in ZUSATZ:
        if z not in werte:
            werte.append(z)
    zeile = f'<meta name="robots" content="{", ".join(werte)}">'
    if TDM not in html:
        zeile += "\n" + TDM
    return html[:m.start()] + zeile + html[m.end():]


def main() -> None:
    pruefen = "--pruefen" in sys.argv
    offen = fehlt = 0
    for datei in sorted(ROOT.glob("*.html")):
        html = datei.read_text(encoding="utf-8")
        neu = umbauen(html)
        if neu == html:
            if not ROBOTS_RE.search(html):
                print(f"  !  {datei.name} (kein robots-Meta)")
                fehlt += 1
            else:
                print(f"  =  {datei.name}")
            continue
        if pruefen:
            print(f"  ~  {datei.name} (würde ausgezeichnet)")
            offen += 1
            continue
        datei.write_text(neu, encoding="utf-8")
        print(f"  ✔  {datei.name}")
        offen += 1
    if fehlt:
        print(f"\n{fehlt} Seite(n) ohne robots-Meta — dort erst header/SEO nachziehen.")
    if pruefen:
        print(f"\n{offen} Seite(n) ohne Vorbehalt." if offen else "\nAlle Seiten ausgezeichnet.")
        sys.exit(1 if offen or fehlt else 0)
    print(f"\n{offen} Seite(n) aktualisiert.")


if __name__ == "__main__":
    main()
