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
    {"datei": "ratgeber-motoren.html",
     "titel": "Wo der Schub herkommt",
     "teaser": "Brushless-Motoren für FPV- und Long-Range-Copter: was Statorgröße, "
               "KV und Drehmoment wirklich bedeuten und warum Gramm pro Watt die "
               "ehrlichste Zahl ist.",
     "bild": "motoren-hero.jpg",
     "alt": "Schemabild: Außenläufer-Motor im Querschnitt mit Stator, Glocke, "
            "Propeller, Drehmoment-Bogen und Schub-Pfeil"},
    {"datei": "ratgeber-videouebertragung.html",
     "titel": "Was dein Copter dir zeigt",
     "teaser": "Die Videoübertragung von analog bis DJI O4, Walksnail und HDZero: "
               "was Latenz wirklich bedeutet, was in Deutschland erlaubt ist und "
               "wie du Reichweite legal verlängerst.",
     "bild": "vtx-zweistrecken.jpg",
     "alt": "Schemabild: schmaler Steuer-Pfad und breiter Video-Kachelstrom "
            "zwischen Fernsteuerung, Copter und Brille"},
    {"datei": "ratgeber-funk-kommunikation.html",
     "titel": "Wie du mit deinem Copter sprichst",
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

# Rubrik "Neuigkeiten": Berichte und Einordnungen zu Ereignissen der Szene,
# im Gegensatz zu den zeitlosen Ratgebern.  Dateien heissen artikel-*.html.
NEUIGKEITEN = [
    {"datei": "artikel-exportbeschraenkungen.html",
     "titel": "Exportbeschränkungen",
     "teaser": "China verschärft die Exportkontrollen, und es gibt keinen "
               "einzigen 13-Zoll-Frame aus deutscher Fertigung.  Was davon bei "
               "dir im Warenkorb und bei uns in der Werkstatt ankommt.",
     "bild": "exportbeschraenkungen-hero.jpg",
     "alt": "Schaubild: die Lieferkette als Kette aus Rohstoff, Bauteil, "
            "Ausfuhrkontrolle und Werkstatt"},
    {"datei": "artikel-darpa-lift-challenge.html",
     "titel": "DARPA Lift Challenge",
     "teaser": "Eine Woche Dayton: 76 Teams, nur 9 gewertete Läufe und ein "
               "klassischer Elektro-Helikopter, der alle Multikopter schlägt.  "
               "Mit Bildergalerie und Videos der Teams.",
     "bild": "darpa-lift-hero.jpg",
     "alt": "Unbemannter Single-Rotor-Helikopter im Flug, unter dem Rumpf hängt "
            "eine Gusseisen-Hantelscheibe"},
]

TEILELISTEN = [
    {"datei": "ratgeber-teileliste-10-zoll.html",
     "titel": "10-Zoll-Build",
     "teaser": "Der kompakte Long-Range-Build: Frame und Motoren von Axisflying, "
               "MacroQuad-Props und ein 30,5er-Stack, dazu Akku, Funk, Video und "
               "GPS mit Bezugsquellen.",
     "bild": "teileliste-10-zoll.jpg",
     "alt": "Schemabild: die sieben Komponentengruppen des 10-Zoll-Builds, von "
            "Frame bis GPS"},
    {"datei": "ratgeber-teileliste-long-range.html",
     "titel": "13-Zoll-Build 1",
     "teaser": "Der große Long-Range-Build mit 13 und 15 Zoll: Frame, Motoren, "
               "Akku, Ladegerät, Funk, Video und GPS, mit direkten "
               "Bezugsquellen.",
     "bild": "teileliste-uebersicht.jpg",
     "alt": "Schemabild: die sieben Komponentengruppen des 13-Zoll-Builds 1, "
            "von Frame bis GPS"},
]

# (Markername, Rubrik in der Meta-Zeile, Datenliste)
BEREICHE = [("neuigkeiten", "Neuigkeiten", NEUIGKEITEN),
            ("ratgeber", "Ratgeber", RATGEBER),
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
    # break_on_hyphens=False ist Pflicht: sonst bricht textwrap deutsche
    # Komposita am Bindestrich um ("Elektro-\nHelikopter"), und der Browser
    # macht aus dem Zeilenumbruch ein Leerzeichen ("Elektro- Helikopter").
    alt = textwrap.fill(eintrag["alt"], width=86, initial_indent="",
                        subsequent_indent=" " * 13, break_on_hyphens=False).strip()
    teaser = textwrap.fill(eintrag["teaser"], width=88,
                           subsequent_indent=" " * 10, break_on_hyphens=False)
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
