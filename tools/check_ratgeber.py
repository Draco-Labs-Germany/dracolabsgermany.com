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
  7. Vorschaubild: og:image, twitter:image und das "image" im Article-JSON-LD
     muessen vorhanden, identisch, kein Logo und lokal auch wirklich da sein.
     Gesetzt werden sie von tools/og_bild.py; der Check ist die Gegenprobe.

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


BILD_FELDER = (
    ("og:image", r'<meta property="og:image" content="([^"]*)">'),
    ("twitter:image", r'<meta name="twitter:image" content="([^"]*)">'),
    ("JSON-LD image", r'\n  "image": "([^"]*)"'),
)

BASIS = "https://dracolabsgermany.com/"


def pruefe_vorschaubild(html: str) -> list:
    """Die drei Bildfelder muessen auf dasselbe eigene Schaubild zeigen.

    Der Befund vom 14.08.2026 hing genau daran: og_bild.py setzte nur die
    beiden Meta-Tags, das JSON-LD blieb auf logo.png stehen.  Beim Teilen sah
    die Seite damit richtig aus, in Google Discover falsch — und weil nichts
    das geprueft hat, fiel es erst beim dritten Hinsehen auf.
    """
    fehler, werte = [], {}
    for name, muster in BILD_FELDER:
        m = re.search(muster, html)
        if not m:
            fehler.append(f"{name} fehlt")
            continue
        werte[name] = m.group(1)
    if len(set(werte.values())) > 1:
        fehler.append("Bildfelder weichen voneinander ab: "
                      + ", ".join(f"{k}={v.split('/')[-1]}" for k, v in werte.items()))
    for name, url in werte.items():
        if url.endswith(("logo.png", "emblem.png")):
            fehler.append(f"{name} zeigt aufs Logo statt aufs eigene Schaubild")
        elif url.startswith(BASIS) and not (ROOT / url[len(BASIS):]).exists():
            fehler.append(f"{name}: Datei {url[len(BASIS):]} fehlt im Repo")
        elif not url.startswith(BASIS):
            fehler.append(f"{name}: keine absolute URL auf {BASIS}")
    return fehler


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


def _video_rechnungen():
    import math
    v_ms = 100 / 3.6                              # m/s bei 100 km/h
    weg_20ms = v_ms * 0.02                        # m in 20 ms
    laenge = 299792458 / 5.8e9                    # m, Wellenlaenge 5,8 GHz
    horizont_120 = math.sqrt(2 * 6_371_000 * 120) / 1000   # km, geometrisch
    fresnel = 0.5 * math.sqrt(laenge * 1000)      # m, Radius Mitte bei 1 km
    return [
        ("100 km/h = 27,8 m/s", v_ms, 27.7 <= v_ms <= 27.9),
        ("'gut einen halben Meter' in 20 ms", weg_20ms, 0.5 <= weg_20ms <= 0.6),
        ("60 von 150 MHz = '40 Prozent'", 60 / 150, 60 / 150 == 0.4),
        ("14 dBm = 'rund 25 mW'", 10 ** 1.4, 24 <= 10 ** 1.4 <= 26),
        ("23 dBm = 'rund 200 mW'", 10 ** 2.3, 190 <= 10 ** 2.3 <= 210),
        ("5,1-GHz-Band 'achtfache' Leistung (200/25)", 200 / 25, 200 / 25 == 8),
        ("Horizont 'etwa 39 km' bei 120 m", horizont_120, 38.5 <= horizont_120 <= 39.6),
        ("Wellenlaenge 'rund 5,2 cm'", laenge * 100, 5.1 <= laenge * 100 <= 5.3),
        ("Fresnel-Radius 'etwa 3,6 m' auf 1 km", fresnel, 3.4 <= fresnel <= 3.8),
        ("linear/zirkular '3 dB' = Haelfte", 10 ** -0.3, 0.49 <= 10 ** -0.3 <= 0.52),
    ]


def _motoren_rechnungen():
    leerlauf_13 = 400 * 22.2                      # U/min, KV mal Spannung (6S nominal)
    leerlauf_5 = 1750 * 22.2
    kt_verh = (8.3 / 400) / (8.3 / 1750)          # Drehmoment je Ampere, 400KV vs 1750KV
    vol_verh = (40**2 * 12) / (22**2 * 7)         # Statorvolumen ~ d^2 * h
    gw_50 = 1010 / 106.56                         # g/W aus T-Motor-Datenblatt (15x5, 22,2 V)
    gw_100 = 2370 / 359.64
    return [
        ("KV400 an 6S: 'rund 8.900' U/min Leerlauf", leerlauf_13, 8800 <= leerlauf_13 <= 8950),
        ("KV1750 an 6S: 'knapp 39.000' U/min Leerlauf", leerlauf_5, 38500 <= leerlauf_5 <= 39000),
        ("'gut das Vierfache' Drehmoment je Ampere (1750/400)", kt_verh, 4.2 <= kt_verh <= 4.6),
        ("Statorvolumen 4012 'rund das 5,7-Fache' eines 2207", vol_verh, 5.5 <= vol_verh <= 5.9),
        ("Halbgas: 'rund 44 %' mehr Schub je Watt (9,48/6,59)", 9.48 / 6.59 - 1, 0.42 <= 9.48 / 6.59 - 1 <= 0.46),
        ("g/W-Gegenprobe Datenblatt 50 %: 1010 g / 106,56 W = 9,48", gw_50, 9.4 <= gw_50 <= 9.55),
        ("g/W-Gegenprobe Datenblatt 100 %: 2370 g / 359,64 W = 6,59", gw_100, 6.5 <= gw_100 <= 6.7),
        ("8S dreht 'ein Drittel schneller' als 6S", 29.6 / 22.2 - 1, 0.32 <= 29.6 / 22.2 - 1 <= 0.34),
        ("3-kg-Copter: '750 g' Schub je Motor", 3000 / 4, 3000 / 4 == 750),
        ("'fast 10 Prozentpunkte' Effizienzspanne (82 - 72,5)", 82 - 72.5, 9 <= 82 - 72.5 <= 10),
        ("Dreieck: 'die 1,73-fache' KV (Wurzel 3)", 3**0.5, 1.72 <= 3**0.5 <= 1.74),
        ("Stern 920 KV -> Dreieck 'rund 1.590'", 920 * 3**0.5, 1570 <= 920 * 3**0.5 <= 1600),
    ]


RECHNUNGEN = {"ratgeber-carbon-frame.html": _carbon_rechnungen,
              "ratgeber-videouebertragung.html": _video_rechnungen,
              "ratgeber-motoren.html": _motoren_rechnungen}


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
        "Vorschaubild": pruefe_vorschaubild(html),
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


def inhaltsseiten() -> list:
    """Alle redaktionellen Seiten: Ratgeber/Teilelisten und Artikel (Rubrik
    Neuigkeiten).  Beide folgen demselben Template und denselben Hausregeln."""
    return sorted(ROOT.glob("ratgeber-*.html")) + sorted(ROOT.glob("artikel-*.html"))


def main():
    # cp1252-Konsole: UTF-8 erzwingen (nur im CLI-Lauf, nicht beim Import)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("seiten", nargs="*", help="HTML-Dateien relativ zum Repo-Root")
    ap.add_argument("--alle", action="store_true",
                    help="alle Inhaltsseiten pruefen (ratgeber-*.html und artikel-*.html)")
    ap.add_argument("--fix", action="store_true", help="Fussnotennummern reparieren")
    ap.add_argument("--extern", action="store_true", help="externe Links auf Erreichbarkeit pruefen")
    args = ap.parse_args()

    pfade = ([ROOT / s for s in args.seiten] if args.seiten else []) + \
            (inhaltsseiten() if args.alle or not args.seiten else [])

    gesamt = sum(pruefe_seite(p, args.fix, args.extern) for p in pfade)
    gesamt += pruefe_header_kanon(inhaltsseiten() + [ROOT / "index.html"])

    print(f"\nGesamt: {'ALLES GRUEN' if gesamt == 0 else f'{gesamt} Befund(e)'}")
    sys.exit(0 if gesamt == 0 else 1)


if __name__ == "__main__":
    main()
