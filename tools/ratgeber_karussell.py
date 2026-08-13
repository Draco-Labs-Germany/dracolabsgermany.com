#!/usr/bin/env python3
"""Haelt die Kachel-Karussells "Ratgeber & Wissen" und "Teilelisten" der
Startseite synchron.

Warum ein Tool und kein Handeinbau: die Kacheln (Video-Still + Titel + Teaser +
Lesezeit) stehen einmal in RATGEBER bzw. TEILELISTEN; das Skript rendert daraus
die Karussell-Bloecke der Startseite (zwischen <!-- ratgeber:start/ende --> und
<!-- teilelisten:start/ende -->).  Neuer Artikel = ein Listeneintrag, fertig.
Die Lesezeit wird nicht gepflegt, sondern live aus der Zeile "Lesezeit ca. X Min"
der jeweiligen Artikelseite gelesen und bleibt so automatisch aktuell.

Bilder: Standbilder aus den Wissensvideos (assets/ratgeber/, gepflegt von
draco-labs/tools/ratgeber_stills.py); Teilelisten ohne Video bekommen ihr
Schaubild aus draco-labs/tools/teileliste_hero.py.

Idempotent: ein vorhandener Block wird ersetzt, nicht verdoppelt.

Stil: Ratgeber-Hausregeln (zwei Leerzeichen nach Satzpunkt, keine Em-Dashes).

Aufruf:  python tools/ratgeber_karussell.py [--pruefen]
"""

import re
import sys
import textwrap
from pathlib import Path

try:                                  # Windows-Konsole ist cp1252, ✔ wirft sonst.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent

# Anzeigereihenfolge = Listenreihenfolge (neuester Artikel zuerst).
RATGEBER = [
    {"datei": "ratgeber-videouebertragung.html",
     "titel": "Was dein Copter dir zeigt",
     "teaser": "Die Videoübertragung von analog bis DJI O4, Walksnail und HDZero: "
               "was Latenz wirklich bedeutet, was in Deutschland erlaubt ist und "
               "wie du Reichweite legal verlängerst.",
     "bild": "vtx-zweistrecken.jpg",
     "alt": "Schemabild: schmaler Steuer-Pfad und breiter Video-Kachelstrom "
            "zwischen Fernsteuerung, Copter und Brille"},
    {"datei": "ratgeber-funk-kommunikation.html",
     "titel": "Wie dein Copter mit dir spricht",
     "teaser": "Der RC-Link von ExpressLRS bis Crossfire: was RSSI und LQ bedeuten, "
               "wie GPS funktioniert und warum die Antenne der wichtigste "
               "Zentimeter deines Copters ist.",
     "bild": "funk-systeme.jpg",
     "alt": "Schemabild: drei Funksysteme am Copter, Steuerung mit Telemetrie, "
            "Video und GPS"},
    {"datei": "ratgeber-carbon-frame.html",
     "titel": "Vom Erdöl zum FPV-Frame",
     "teaser": "Wie Carbon entsteht, was eine gute Platte von einer schlechten "
               "unterscheidet und warum bei 13 Zoll Rohre an die Arme gehören.",
     "bild": "carbon-prozesskette.jpg",
     "alt": "Schemabild: Prozesskette vom Erdöl über Propylen, Acrylnitril und "
            "PAN zu den Öfen"},
    {"datei": "ratgeber-akku-13-zoll.html",
     "titel": "Du und dein Akku",
     "teaser": "Akkus für 13-Zoll-Copter: Zellenzahl, Kapazität, C-Rate, Stecker "
               "und Sicherheit.",
     "bild": "akku-zellenzahl.jpg",
     "alt": "Schemabild: acht LiPo-Zellen in Reihe ergeben 8S mit 29,6 Volt nominal"},
    {"datei": "ratgeber-ladegeraet-8s.html",
     "titel": "Der Akku und sein Ladegerät",
     "teaser": "Ladegeräte für 6S und 8S: Leistung, Balancer, AC/DC, "
               "Marktübersicht und wie ein LiPo-Lader funktioniert.",
     "bild": "ladegeraet-leistung.jpg",
     "alt": "Schemabild: Leistungsvergleich 200, 300 und 600 Watt beim Laden "
            "eines 8S-Akkus"},
]

TEILELISTEN = [
    {"datei": "ratgeber-teileliste-long-range.html",
     "titel": "Build 1: Toruk (13/15 Zoll)",
     "teaser": "Der große Long-Range-Build auf Basis der Toruk-Frames: Frame, "
               "Motoren, Akku, Ladegerät, Funk, Video und GPS, mit direkten "
               "Bezugsquellen.",
     "bild": "teileliste-uebersicht.jpg",
     "alt": "Schemabild: die sieben Komponentengruppen der Teileliste Build 1, "
            "von Frame bis GPS"},
    {"datei": "ratgeber-teileliste-manta.html",
     "titel": "Build 2: Manta (10 Zoll)",
     "teaser": "Der kompakte 10-Zoll-Build auf Manta-Basis: Frame und Motoren "
               "von Axisflying, Stack-Kombo von iFlight, dazu Akku, Funk, Video "
               "und GPS mit Bezugsquellen.",
     "bild": "teileliste-manta.jpg",
     "alt": "Schemabild: die sieben Komponentengruppen der Teileliste Build 2, "
            "von Frame bis GPS"},
]

# (Markername, Rubrik in der Meta-Zeile, Datenliste)
BEREICHE = [("ratgeber", "Ratgeber", RATGEBER),
            ("teilelisten", "Teileliste", TEILELISTEN)]

LESEZEIT_RE = re.compile(r"Lesezeit ca\.\s*(\d+)\s*Min")


def lesezeit(datei: str) -> str | None:
    m = LESEZEIT_RE.search((ROOT / datei).read_text(encoding="utf-8"))
    return m.group(1) if m else None


def kachel(eintrag: dict, rubrik: str) -> str:
    for schluessel in ("datei", "bild"):
        pfad = ROOT / ("assets/ratgeber/" + eintrag[schluessel]
                       if schluessel == "bild" else eintrag[schluessel])
        if not pfad.exists():
            sys.exit(f"FEHLER: {pfad.relative_to(ROOT)} fehlt "
                     f"(Eintrag {eintrag['titel']!r}).")
    minuten = lesezeit(eintrag["datei"])
    meta = rubrik + (f" · Lesezeit ca. {minuten} Min" if minuten else "")
    alt = textwrap.fill(eintrag["alt"], width=86, initial_indent="",
                        subsequent_indent=" " * 13).strip()
    teaser = textwrap.fill(eintrag["teaser"], width=88,
                           subsequent_indent=" " * 10)
    return (
        f'      <a class="rg-kachel" href="{eintrag["datei"]}">\n'
        f'        <img src="assets/ratgeber/{eintrag["bild"]}" alt="{alt}"\n'
        f'             width="1200" height="675" loading="lazy">\n'
        f'        <div class="rg-text">\n'
        f'          <div class="rg-titel">{eintrag["titel"]}</div>\n'
        f'          <div class="rg-teaser">{teaser}</div>\n'
        f'          <div class="rg-meta">{meta}</div>\n'
        f'        </div>\n'
        f'      </a>'
    )


def block(name: str, rubrik: str, eintraege: list) -> str:
    kacheln = "\n".join(kachel(e, rubrik) for e in eintraege)
    return (
        f"    <!-- {name}:start -->\n"
        f'    <div class="rg-karussell">\n'
        f"{kacheln}\n"
        f"    </div>\n"
        f"    <!-- {name}:ende -->\n"
    )


def main() -> None:
    pruefen = "--pruefen" in sys.argv
    seite = ROOT / "index.html"
    text = vorher = seite.read_text(encoding="utf-8")
    for name, rubrik, eintraege in BEREICHE:
        muster = re.compile(rf"[ \t]*<!-- {name}:start -->.*?<!-- {name}:ende -->\n",
                            re.S)
        if not muster.search(text):
            sys.exit(f"FEHLER: Marker <!-- {name}:start/ende --> fehlt in index.html.")
        text = muster.sub(block(name, rubrik, eintraege).replace("\\", r"\\"),
                          text, count=1)
    if text == vorher:
        print("  =  index.html")
        sys.exit(0)
    if pruefen:
        print("  ~  index.html (würde geändert)\n\n1 Seite nicht auf Stand.")
        sys.exit(1)
    seite.write_text(text, encoding="utf-8")
    print("  ✔  index.html\n\n1 Seite aktualisiert.")


if __name__ == "__main__":
    main()
