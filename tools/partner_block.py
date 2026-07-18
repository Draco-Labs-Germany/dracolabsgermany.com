#!/usr/bin/env python3
"""Setzt den Block "Partner & Empfehlungen" auf jede Ratgeber-Seite — und haelt
ihn dort und auf der Startseite synchron.

Warum ein Tool und kein Handeinbau: die Seite ist statisches HTML ohne Includes.
Kommt ein Partner dazu oder aendert sich ein Affiliate-Link/Gutscheincode, muesste
man sonst jede Seite einzeln anfassen und die Bloecke driften auseinander.  Die
Partner stehen einmal in PARTNER; das Skript rendert daraus die Karten fuer die
Ratgeber-Seiten (zwischen <!-- partner:start --> und <!-- partner:ende -->, hinter
den Quellenangaben ans Ende des Artikels) und ersetzt die partner-grid der
Startseite.

Idempotent: ein vorhandener Block wird ersetzt, nicht verdoppelt.

Stil: Ratgeber-Hausregeln (zwei Leerzeichen nach Satzpunkt, keine Em-Dashes);
Kennzeichnung als Anzeige und rel="sponsored" sind Pflicht bei Affiliate-Links.

Aufruf:  python tools/partner_block.py [--pruefen]
"""

import re
import sys
from pathlib import Path

try:                                  # Windows-Konsole ist cp1252, ✔ wirft sonst.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent

# (Name, URL, Logo, Breite, Hoehe, Beschreibung, Gutscheincode oder None)
PARTNER = [
    ("SUNLU", "https://www.sunlu.com/?sca_ref=11859027.qxuEVmIDy7",
     "assets/partner/sunlu-logo.png", 72, 72,
     "3D-Druck-Filament (PLA, PETG, TPU), Filament-Trockner und Zubehör; damit\n"
     "          drucken wir Prototypen und Halterungen.",
     "dracolabs"),
    ("FPV24", "https://www.fpv24.com/de/?aid=U-THvRXn",
     "assets/partner/fpv24-logo.svg", 134, 44,
     "Deutscher FPV-Fachhandel mit schnellem Versand und Support; Akkus,\n"
     "          Ladegeräte (u.&nbsp;a. ISDT) und FPV-Komponenten, die wir im Aufbau verwenden.",
     None),
]

BLOCK_RE = re.compile(r"[ \t]*<!-- partner:start -->.*?<!-- partner:ende -->\n", re.S)
# Ende des Artikelinhalts: schliessendes wrap-div + </main> (einmalig je Seite).
MAIN_ENDE_RE = re.compile(r"\n(  </div>\n</main>)")
GRID_RE = re.compile(r'(<div class="partner-grid">\n).*?(\n    </div>\n  </section>)', re.S)


def karten() -> str:
    zeilen = []
    for name, url, logo, breite, hoehe, text, gutschein in PARTNER:
        zeilen.append(
            f'      <a class="partner-card" href="{url}"\n'
            f'         target="_blank" rel="sponsored noopener">\n'
            f'        <img src="{logo}" alt="{name}" width="{breite}" height="{hoehe}" loading="lazy">\n'
            f'        <div>\n'
            f'          <div class="partner-name">{name}</div>\n'
            f'          <div class="partner-desc">{text}</div>')
        if gutschein:
            zeilen.append(
                f'          <div class="partner-coupon">Gutscheincode beim Checkout: '
                f'<code>{gutschein}</code></div>')
        zeilen.append('        </div>\n      </a>')
    return "\n".join(zeilen)


def block() -> str:
    return (
        "<!-- partner:start -->\n"
        "    <h2>Partner &amp; Empfehlungen</h2>\n"
        '    <p class="muted"><strong>Anzeige:</strong> Ausrüstung, die wir selbst nutzen und\n'
        "    empfehlen können.  Die folgenden Links sind Affiliate-Links; kaufst du darüber,\n"
        "    erhalten wir eine Provision, für dich ändert sich am Preis nichts.  Empfohlen\n"
        "    wird nur, was uns fachlich überzeugt.</p>\n"
        '    <div class="partner-grid">\n'
        f"{karten()}\n"
        "    </div>\n"
        "<!-- partner:ende -->\n"
    )


def setze_ratgeber(text: str, neu: str) -> str:
    if BLOCK_RE.search(text):
        return BLOCK_RE.sub(neu, text, count=1)
    return MAIN_ENDE_RE.sub(lambda m: "\n\n" + neu + "\n" + m.group(1), text, count=1)


def setze_index(text: str) -> str:
    return GRID_RE.sub(lambda m: m.group(1) + karten() + m.group(2), text, count=1)


def main() -> None:
    pruefen = "--pruefen" in sys.argv
    neu = block()
    geaendert = fehlt = 0
    seiten = sorted(ROOT.glob("ratgeber-*.html")) + [ROOT / "index.html"]
    for seite in seiten:
        vorher = seite.read_text(encoding="utf-8")
        text = setze_index(vorher) if seite.name == "index.html" else setze_ratgeber(vorher, neu)
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
