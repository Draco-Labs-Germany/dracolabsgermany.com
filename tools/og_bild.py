#!/usr/bin/env python3
"""Gibt jeder Artikelseite ihr eigenes Vorschaubild fuer Social und Chat.

Befund vom 2026-08-14: ``og:image`` und ``twitter:image`` zeigten auf allen
Seiten auf ``assets/logo.png``.  Geteilt in WhatsApp, LinkedIn oder Discord sah
damit jeder Ratgeber gleich aus — obwohl jeder laengst sein eigenes Schaubild
hat, naemlich genau das, das auch auf der Kachel der Startseite steht.

Die Zuordnung wird deshalb nicht erneut gepflegt, sondern aus
``ratgeber_karussell.py`` uebernommen: ein Artikel, ein Bild, eine Quelle.
Seiten ohne Kachel (Startseite, Impressum, Datenschutz, Nutzungsbedingungen,
tiktok-callback) behalten das Logo — dort ist die Marke das richtige Motiv.

Die Standbilder liegen bei 1200 Pixel Breite und im 16:9-Format; das deckt die
Mindestmasse von Facebook, LinkedIn und X ab.

Nachtrag 14.08.2026: Die erste Fassung hat nur ``og:image`` und
``twitter:image`` gesetzt.  Das ``image``-Feld im Article-JSON-LD blieb
uebersehen und stand auf allen zehn Artikelseiten weiter auf ``logo.png`` —
also genau der Fehler, der behoben werden sollte, nur eine Ebene tiefer.  Google
zieht das Vorschaubild fuer Discover und die Suchergebnisse aus dem JSON-LD,
nicht aus Open Graph; die Seite sah damit im Chat richtig und in der Suche
falsch aus.  Seither setzt das Skript alle drei Felder, und
``check_ratgeber.py`` prueft sie mit, damit es nicht ein drittes Mal auffaellt.

Idempotent: was schon stimmt, wird nicht neu geschrieben.

Aufruf:  python tools/og_bild.py [--pruefen]
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ratgeber_karussell import NEUIGKEITEN, RATGEBER, TEILELISTEN  # noqa: E402

try:                                  # Windows-Konsole ist cp1252.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent
BASIS = "https://dracolabsgermany.com/"

BILD = {e["datei"]: "assets/ratgeber/" + e["bild"]
        for e in NEUIGKEITEN + RATGEBER + TEILELISTEN}

OG_RE = re.compile(r'(<meta property="og:image" content=")([^"]*)(">)')
TW_RE = re.compile(r'(<meta name="twitter:image" content=")([^"]*)(">)')
# Nur das "image" der Article-Ebene, nicht das "url" im publisher-Logo darunter.
LD_RE = re.compile(r'(\n  "image": ")([^"]*)(")')

MUSTER = (("og:image", OG_RE), ("twitter:image", TW_RE), ("JSON-LD image", LD_RE))


def setzen(html: str, url: str) -> tuple:
    """Setzt alle drei Bildfelder und meldet, welche gar nicht vorhanden sind."""
    fehlend = []
    for name, muster in MUSTER:
        html, treffer = muster.subn(
            lambda m: m.group(1) + url + m.group(3), html, count=1)
        if not treffer:
            fehlend.append(name)
    return html, fehlend


def main() -> None:
    pruefen = "--pruefen" in sys.argv
    offen = 0
    for datei, bild in sorted(BILD.items()):
        pfad = ROOT / datei
        if not (ROOT / bild).exists():
            sys.exit(f"FEHLER: {bild} fehlt (gehört zu {datei}).")
        html = pfad.read_text(encoding="utf-8")
        neu, fehlend = setzen(html, BASIS + bild)
        if fehlend:
            sys.exit(f"FEHLER: {datei} hat kein {', kein '.join(fehlend)}.")
        if neu == html:
            print(f"  =  {datei}")
            continue
        if pruefen:
            print(f"  ~  {datei} → {bild}")
            offen += 1
            continue
        pfad.write_text(neu, encoding="utf-8")
        print(f"  ✔  {datei} → {bild}")
        offen += 1
    if pruefen:
        print(f"\n{offen} Seite(n) mit generischem Bild." if offen
              else "\nAlle Artikelseiten mit eigenem Vorschaubild.")
        sys.exit(1 if offen else 0)
    print(f"\n{offen} Seite(n) aktualisiert.")


if __name__ == "__main__":
    main()
