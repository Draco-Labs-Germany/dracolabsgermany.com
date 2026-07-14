#!/usr/bin/env python3
"""Prueft Ratgeber-Seiten auf die Hausregeln.

Checks je Seite:
  1. Fussnoten: jede Text-Referenz <a href="#qX">N</a> muss die Nummer zeigen,
     die das <ol> der Quellenangaben tatsaechlich rendert (Listenposition).
     Referenzen ohne Ziel und Quellen ohne Referenz werden gemeldet.
     --fix schreibt die angezeigten Nummern auf die Listenposition um.
  2. Stil: keine Em-Dashes im Fliesstext (Kopfbereich und Quellenangaben sind
     ausgenommen), zwei Leerzeichen nach jedem Satzpunkt (nur innerhalb einer
     Quelltextzeile pruefbar).
  3. Struktur: oeffnende/schliessende Tags balanciert (p, table, tr, td, th,
     ul, ol, li, strong, em, h2, h3).
  4. Lokale Links: verlinkte Dateien und Anker muessen existieren.
  5. Header-Kanon: der <header class="site">-Block muss auf allen Seiten
     identisch sein (Shop/Website = ein Auftritt).
  6. Rechnungen: alle als "unsere Rechnung" markierten Zahlen der Seite werden
     unabhaengig nachgerechnet (Tabelle RECHNUNGEN unten, je Seite gepflegt).

Aufruf:  python tools/check_ratgeber.py ratgeber-carbon-frame.html [--fix]
         python tools/check_ratgeber.py --alle
"""

import argparse
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Abkuerzungen, deren Binnenpunkt kein Satzende ist.
ABKUERZUNGEN = ("z. B", "u. a", "d. h", "Nr. ", "Dr. ", "ca. ", "bzw. ", "ggf. ", "evtl. ")

PAAR_TAGS = ("p", "table", "tr", "td", "th", "ul", "ol", "li",
             "strong", "em", "h1", "h2", "h3", "div", "a", "sup")


def lese(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8")


def quellen_positionen(html: str):
    """Liefert (map id->Listenposition, Start-Offset der Quellen-Ueberschrift)."""
    m = re.search(r"<h2>Quellenangaben</h2>", html)
    if not m:
        return {}, len(html)
    ol = re.search(r"<ol[^>]*>(.*?)</ol>", html[m.end():], re.S)
    ids = re.findall(r'<li id="(q[0-9]+[a-z]?)"', ol.group(1)) if ol else []
    return {qid: i + 1 for i, qid in enumerate(ids)}, m.start()


def pruefe_fussnoten(html: str, fix: bool):
    """Vergleicht angezeigte Fussnotennummern mit den gerenderten ol-Positionen."""
    pos, quellen_start = quellen_positionen(html)
    fehler, benutzt = [], set()

    def ersatz(m):
        qid, klammer_auf, nummer, klammer_zu = m.groups()
        benutzt.add(qid)
        if qid not in pos:
            fehler.append(f"Referenz auf fehlende Quelle #{qid}")
            return m.group(0)
        soll = pos[qid]
        if int(nummer) != soll:
            fehler.append(f"#{qid}: Text zeigt [{nummer}], Liste rendert [{soll}]")
        return f'<a href="#{qid}">{klammer_auf}{soll}{klammer_zu}</a>'

    neu = re.sub(r'<a href="#(q[0-9]+[a-z]?)">(\[?)(\d+)(\]?)</a>', ersatz, html)

    unbenutzt = [q for q in pos if q not in benutzt]
    if unbenutzt:
        fehler.append("Quellen ohne Referenz im Text: " + ", ".join(unbenutzt))
    if len(pos) != len(set(pos)):
        fehler.append("doppelte Quellen-IDs")
    return fehler, (neu if fix else html), quellen_start


def fliesstext(html: str, quellen_start: int) -> str:
    """Textbereich zwischen <main> und den Quellenangaben, Tags entfernt."""
    m = re.search(r"<main[^>]*>", html)
    bereich = html[m.end() if m else 0:quellen_start]
    bereich = re.sub(r"<sup>.*?</sup>", "", bereich, flags=re.S)
    bereich = re.sub(r"<script.*?</script>", "", bereich, flags=re.S)
    return bereich


def pruefe_stil(html: str, quellen_start: int):
    fehler = []
    bereich = fliesstext(html, quellen_start)
    for i, zeile in enumerate(bereich.splitlines(), 1):
        # &nbsp;-Entity und literales U+00A0 beide zu normalem Leerzeichen normalisieren
        text = re.sub(r"<[^>]+>", "", zeile).replace("&nbsp;", " ").replace("\u00a0", " ")
        if "—" in text:
            fehler.append(f"Em-Dash im Fliesstext: ...{text.strip()[:70]}")
        for m in re.finditer(r"[a-zäöüßA-ZÄÖÜ%°³²\"“”)\]]\. (?! )(?=[A-ZÄÖÜ„])", text):
            kontext = text[max(0, m.start() - 4):m.end() + 12]
            if any(a in text[max(0, m.start() - 3):m.end() + 2] for a in ABKUERZUNGEN):
                continue
            fehler.append(f"1 Leerzeichen nach Satzpunkt: ...{kontext}...")
    return fehler


def pruefe_tags(html: str):
    fehler = []
    for tag in PAAR_TAGS:
        auf = len(re.findall(rf"<{tag}[\s>]", html))
        zu = len(re.findall(rf"</{tag}>", html))
        if auf != zu:
            fehler.append(f"<{tag}>: {auf} oeffnend / {zu} schliessend")
    return fehler


def pruefe_links(html: str, pfad: Path):
    fehler = []
    for href in re.findall(r'(?:href|src)="([^"]+)"', html):
        if href.startswith(("http://", "https://", "mailto:", "tel:")):
            continue
        datei, _, anker = href.partition("#")
        ziel = pfad if not datei else ROOT / datei
        if not ziel.exists():
            fehler.append(f"Link-Ziel fehlt: {href}")
            continue
        if anker and not re.search(rf'id="{re.escape(anker)}"', lese(ziel)):
            fehler.append(f"Anker fehlt: {href}")
    return fehler


def pruefe_externe_links(html: str):
    """Erreichbarkeit aller externen Links (nur mit --extern; braucht Netz)."""
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor

    urls = sorted({u for u in re.findall(r'href="(https?://[^"]+)"', html)})

    def hole(url):
        req = urllib.request.Request(url, method="GET", headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Linkcheck dracolabsgermany.com"})
        try:
            with urllib.request.urlopen(req, timeout=15) as antwort:
                antwort.read(2048)
                return url, antwort.status
        except Exception as e:
            return url, str(e)

    fehler = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for url, status in pool.map(hole, urls):
            if status != 200:
                fehler.append(f"{status}: {url}")
    return fehler, len(urls)


def header_block(html: str) -> str:
    m = re.search(r'<header class="site">.*?</header>', html, re.S)
    if not m:
        return ""
    # Normalisieren: Kommentare, Leerzeilen und das (auf Unterseiten noetige)
    # index.html-Praefix der Anker-Links sind keine Kanon-Abweichung.
    block = re.sub(r"<!--.*?-->", "", m.group(0), flags=re.S)
    block = block.replace('href="index.html#', 'href="#')
    return "\n".join(z.strip() for z in block.splitlines() if z.strip())


# --- Rechnungen: je Seite die als "unsere Rechnung" markierten Zahlen -------

def _carbon_rechnungen():
    i_flach = 20 * 6**3 / 12                      # mm^4, schwache Richtung
    i_rohr = (20**4 - 18**4) / 12                 # mm^4, Vierkant 1 mm Wand
    a_flach, a_rohr = 20 * 6, 20**2 - 18**2       # mm^2
    r_kontakt = 0.002 / (16 * 25e-6)              # Ohm: 2 mm Dicke, 5x5 mm, ~16 S/m
    return [
        ("Flacharm 6x20 mm: 360 mm^4", i_flach, i_flach == 360),
        ("Vierkantrohr 20x20x1: 4.585 mm^4", i_rohr, round(i_rohr) == 4585),
        ("Rohr 'rund zwoelfmal' steifer", i_rohr / i_flach, 11.5 <= i_rohr / i_flach <= 13.5),
        ("Querschnitte 120 / 76 mm^2", (a_flach, a_rohr), (a_flach, a_rohr) == (120, 76)),
        ("'rund ein Drittel weniger' Material", 1 - a_rohr / a_flach, 0.30 <= 1 - a_rohr / a_flach <= 0.40),
        ("Dichte-Gegenprobe 250 g / 180 cm^3 = 1,39", 250 / 180, round(250 / 180, 2) == 1.39),
        ("Glasfaser 'rund 43 %' schwerer", 2.54 / 1.78 - 1, 0.41 <= 2.54 / 1.78 - 1 <= 0.45),
        ("Biegetest '43 % mehr Last'", 200 / 140 - 1, 0.41 <= 200 / 140 - 1 <= 0.45),
        ("Alu: '1,7-mal so dick' bei gleichem Gewicht", 2.7 / 1.6, 1.65 <= 2.7 / 1.6 <= 1.75),
        ("Alu: 'fuenfmal so steif'", (2.7 / 1.6) ** 3, 4.5 <= (2.7 / 1.6) ** 3 <= 5.2),
        ("Platte 3->4 mm: '2,37-mal so steif'", (4 / 3) ** 3, round((4 / 3) ** 3, 2) == 2.37),
        ("Platte 3->4 mm: '33 % mehr Gewicht'", 4 / 3 - 1, 0.32 <= 4 / 3 - 1 <= 0.34),
        ("Klasse H '200-mal weniger' Durchlass als L", 1 / 0.005, 1 / 0.005 == 200),
        ("15 dB = 'rund 97 %' weg", 1 - 10**-1.5, 0.96 <= 1 - 10**-1.5 <= 0.98),
        ("20 dB = '99 %' weg", 1 - 10**-2.0, round(1 - 10**-2.0, 2) == 0.99),
        ("Kontaktfleck 'rund 5 Ohm'", r_kontakt, 4.5 <= r_kontakt <= 5.5),
        ("6S: 'etwa 4,4 A'", 22.2 / 5, 4.2 <= 22.2 / 5 <= 4.6),
        ("6S: 'rund 100 W'", 22.2**2 / 5, 90 <= 22.2**2 / 5 <= 110),
        ("quasi-isotrop 'rund 40 %' Verlust (35/60)", 1 - 35 / 60, 0.38 <= 1 - 35 / 60 <= 0.44),
        ("0/90 schraeg 'ein Viertel so steif' (15/60)", 15 / 60, 15 / 60 == 0.25),
        ("0/90 schraeg 'rund ein Fuenftel' Last (120/550)", 120 / 550, 0.19 <= 120 / 550 <= 0.24),
        ("Carbon 'rund 60 %' des Alu-Gewichts", 1.6 / 2.7, 0.57 <= 1.6 / 2.7 <= 0.62),
        ("Faser 'mehr als doppelt so dick' als WHO-Grenze", 7 / 3, 7 / 3 > 2),
        ("Leitwert quer: 'mehr als hundert Billionen Mal' (15/1e-13)", 15 / 1e-13, 15 / 1e-13 > 1e14),
    ]


RECHNUNGEN = {"ratgeber-carbon-frame.html": _carbon_rechnungen}


def pruefe_rechnungen(name: str):
    zeilen, fehler = [], []
    for label, wert, ok in RECHNUNGEN.get(name, lambda: [])():
        zeilen.append(f"  {'OK ' if ok else 'FEHLER'} {label}  (nachgerechnet: {wert})")
        if not ok:
            fehler.append(label)
    return zeilen, fehler


def pruefe_seite(pfad: Path, fix: bool, extern: bool = False) -> int:
    html = lese(pfad)
    print(f"\n=== {pfad.name} ===")

    fussnoten, neu, quellen_start = pruefe_fussnoten(html, fix)
    if fix and neu != html:
        pfad.write_text(neu, encoding="utf-8")
        html = neu
        print(f"  --fix: Fussnotennummern auf Listenposition umgeschrieben")
        fussnoten, _, quellen_start = pruefe_fussnoten(html, fix=False)

    befunde = {
        "Fussnoten": fussnoten,
        "Stil": pruefe_stil(html, quellen_start),
        "Tag-Balance": pruefe_tags(html),
        "Lokale Links": pruefe_links(html, pfad),
    }
    rechnung_zeilen, rechnung_fehler = pruefe_rechnungen(pfad.name)
    befunde["Rechnungen"] = rechnung_fehler
    if extern:
        extern_fehler, extern_anzahl = pruefe_externe_links(html)
        befunde[f"Externe Links ({extern_anzahl} URLs)"] = extern_fehler

    for titel, liste in befunde.items():
        print(f"  {titel}: {'OK' if not liste else f'{len(liste)} Befund(e)'}")
        for eintrag in liste:
            print(f"    - {eintrag}")
    if rechnung_zeilen:
        print("  Nachgerechnet im Detail:")
        for z in rechnung_zeilen:
            print(f"  {z}")
    return sum(len(v) for v in befunde.values())


def pruefe_header_kanon(pfade):
    bloecke = {p.name: header_block(lese(p)) for p in pfade}
    referenz = bloecke.get("index.html") or next(iter(bloecke.values()))
    abweichler = [n for n, b in bloecke.items() if b != referenz]
    print(f"\nHeader-Kanon ({len(pfade)} Seiten): "
          f"{'OK, identisch' if not abweichler else 'ABWEICHUNG: ' + ', '.join(abweichler)}")
    return len(abweichler)


def main():
    # cp1252-Konsole: UTF-8 erzwingen (nur im CLI-Lauf, nicht beim Import)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("seiten", nargs="*", help="HTML-Dateien relativ zum Repo-Root")
    ap.add_argument("--alle", action="store_true", help="alle ratgeber-*.html pruefen")
    ap.add_argument("--fix", action="store_true", help="Fussnotennummern reparieren")
    ap.add_argument("--extern", action="store_true", help="externe Links auf Erreichbarkeit pruefen")
    args = ap.parse_args()

    pfade = ([ROOT / s for s in args.seiten] if args.seiten else []) + \
            (sorted(ROOT.glob("ratgeber-*.html")) if args.alle or not args.seiten else [])

    gesamt = sum(pruefe_seite(p, args.fix, args.extern) for p in pfade)
    gesamt += pruefe_header_kanon(sorted(ROOT.glob("ratgeber-*.html")) + [ROOT / "index.html"])

    print(f"\nGesamt: {'ALLES GRUEN' if gesamt == 0 else f'{gesamt} Befund(e)'}")
    sys.exit(0 if gesamt == 0 else 1)


if __name__ == "__main__":
    main()
