#!/usr/bin/env python3
"""Setzt Produktbild-Karten der Partner unter die Affiliate-Links der Ratgeber.

Warum ein Tool und kein Handeinbau: dieselben Produkte stehen auf mehreren
Seiten, und die Bildrechte sind an Auflagen gebunden.  Steht ein Produkt einmal
in PRODUKTE, rendert das Skript ueberall dieselbe Karte mit derselben
Markennennung; faellt eine Freigabe weg, reicht ein Loeschen an einer Stelle.

Bildrechte (Stand 14.08.2026, Belege in draco-labs/content/affiliate-links.md):
  * DarwinFPV  — Freigabe von Lin am 13.08.2026 fuer Website und YouTube.
    Auflagen: Marke "DarwinFPV" bei jedem Produktfoto klar nennen, Bilder nicht
    irrefuehrend veraendern.  Deshalb steht die Marke sichtbar in der Karte und
    im alt-Text, und die Bilder werden nur proportional verkleinert.
  * Ampow/Ovonic — Freigabe von Evelyn am 13.08.2026 fuer Affiliate-Promotion.
  KEINE Bilder von Partnern ohne Freigabe (FPV24 offen, n-factory hinfaellig).

Ablauf:
  python tools/produktbilder.py --laden    Bilder von den Herstellerseiten holen
                                           (nach assets/produkte/, verkleinert)
  python tools/produktbilder.py            Karten in die Ratgeber-Seiten setzen
  python tools/produktbilder.py --pruefen  nur melden, was sich aendern wuerde

Idempotent: ein vorhandener Block wird ersetzt, nicht verdoppelt.

Stil: Ratgeber-Hausregeln (zwei Leerzeichen nach Satzpunkt, keine Em-Dashes);
Kennzeichnung als Anzeige und rel="sponsored" sind Pflicht bei Affiliate-Links.
"""

import re
import sys
import urllib.request
from pathlib import Path

try:                                  # Windows-Konsole ist cp1252, ✔ wirft sonst.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent
BILDER = ROOT / "assets" / "produkte"
# Alle Quellbilder sind quadratisch; die Karte zeigt rund 190 px, gespeichert
# wird das Doppelte fuer Retina.  width/height im HTML nur als Seitenverhaeltnis,
# die tatsaechliche Groesse steuert .produkt-grid in style.css.
BREITE = 480

# key -> (Marke, Produktname, Quell-Bild beim Hersteller)
PRODUKTE = {
    "darwin-toruk13-frame": (
        "DarwinFPV", "Toruk13 Frame Kit (13 Zoll)",
        "https://darwinfpv.com/cdn/shop/files/DarwinFPVToruk1313inchframe.jpg?width=1024"),
    "darwin-toruk15-frame": (
        "DarwinFPV", "Toruk15 Frame Kit (15 Zoll)",
        "https://darwinfpv.com/cdn/shop/files/FullyAssembledDarwinFPV15-inchFPVDroneFrame.jpg?width=1024"),
    "darwin-4320-motor": (
        "DarwinFPV", "4320 Brushless-Motor",
        "https://darwinfpv.com/cdn/shop/files/DarwinFPV4320-350KVBrushlessMotor-DualView.jpg?width=1024"),
    "darwin-3115-motor": (
        "DarwinFPV", "3115 Brushless-Motor",
        "https://darwinfpv.com/cdn/shop/files/1_b90f5e9f-7721-4062-ae60-f1dc4884f376.jpg?width=1024"),
    "ovonic-roam-6s-5600": (
        "Ovonic", "ROAM 6S 5.600 mAh (100C, XT90)",
        "https://www.ampow.com/cdn/shop/files/0_ceffef59-5b0b-47fb-9055-e7008cfd4438.jpg"),
    "ovonic-roam-6s-6500": (
        "Ovonic", "ROAM 6S 6.500 mAh (150C, XT90-S)",
        "https://www.ampow.com/cdn/shop/files/O-150C-6500-6S1P-XT90-S_1.png"),
    "ovonic-roam-8s-5200": (
        "Ovonic", "ROAM 8S 5.200 mAh (150C, XT90-S)",
        "https://www.ampow.com/cdn/shop/files/Ovonic_Roam_Series_8S_Lipo_Battery_5200mAh_8S1P_150C_29.6V_Long_Range_Lipo_Battery_with_XT90_Anti_Spark_Plug.jpg"),
    "ovonic-roam-8s-6200": (
        "Ovonic", "ROAM 8S 6.200 mAh (150C, XT90-S)",
        "https://www.ampow.com/cdn/shop/files/O-150C-6200-8S1P-XT90-S_4.png"),
}

# (Seite, Block-ID, Anker = bereits vorhandener Link auf der Seite, [(key, Ziel-URL)])
# Der Anker sagt nur, WO die Karten stehen; verlinkt wird der jeweils hinterlegte
# Affiliate-Link, damit keine neuen Tracking-Links erfunden werden.
COLLABS = "https://collabs.shop/"
AMPOW_ROAM = ("https://www.ampow.com/collections/"
              "ovonic-roam-series-6s-8s-lipo-battery-for-long-range-drone?dt_id=3341217")

BLOECKE = [
    ("ratgeber-teileliste-long-range.html", "frames", COLLABS + "eronj6", [
        ("darwin-toruk13-frame", COLLABS + "eronj6"),
        ("darwin-toruk15-frame", COLLABS + "vsorw4")]),
    ("ratgeber-teileliste-long-range.html", "motor", COLLABS + "eoovhg", [
        ("darwin-4320-motor", COLLABS + "eoovhg")]),
    ("ratgeber-teileliste-long-range.html", "akku", AMPOW_ROAM, [
        ("ovonic-roam-8s-6200", AMPOW_ROAM)]),
    ("ratgeber-teileliste-10-zoll.html", "motor", COLLABS + "huexzp", [
        ("darwin-3115-motor", COLLABS + "huexzp")]),
    ("ratgeber-teileliste-10-zoll.html", "akku", COLLABS + "qkk8sa", [
        ("ovonic-roam-6s-5600", COLLABS + "qkk8sa"),
        ("ovonic-roam-6s-6500", COLLABS + "vwf4bn")]),
    ("ratgeber-akku-13-zoll.html", "akku", AMPOW_ROAM, [
        ("ovonic-roam-8s-5200", AMPOW_ROAM),
        ("ovonic-roam-8s-6200", AMPOW_ROAM)]),
    ("ratgeber-akku-13-zoll.html", "frames", COLLABS + "eronj6", [
        ("darwin-toruk13-frame", COLLABS + "eronj6"),
        ("darwin-toruk15-frame", COLLABS + "vsorw4")]),
]


def laden() -> None:
    """Holt die freigegebenen Produktfotos und legt sie verkleinert ab."""
    from PIL import Image                       # nur beim Laden noetig

    BILDER.mkdir(parents=True, exist_ok=True)
    for key, (marke, name, quelle) in PRODUKTE.items():
        ziel = BILDER / f"{key}.jpg"
        anfrage = urllib.request.Request(quelle, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(anfrage, timeout=40) as antwort:
            roh = BILDER / f"{key}.tmp"
            roh.write_bytes(antwort.read())
        bild = Image.open(roh).convert("RGB")
        hoehe = round(bild.height * (BREITE * 2) / bild.width)
        bild.resize((BREITE * 2, hoehe), Image.LANCZOS).save(ziel, "JPEG", quality=82)
        roh.unlink()
        print(f"  ✔  {ziel.name}  {marke} {name}  ({bild.width}x{bild.height} → {BREITE*2}px)")


def karte(key: str, ziel: str) -> str:
    marke, name, _ = PRODUKTE[key]
    return (
        f'      <a class="produkt-karte" href="{ziel}"\n'
        f'         target="_blank" rel="sponsored noopener">\n'
        f'        <img src="assets/produkte/{key}.jpg" alt="{marke} {name}"\n'
        f'             width="{BREITE}" height="{BREITE}" loading="lazy">\n'
        f'        <div class="produkt-marke">{marke}</div>\n'
        f'        <div class="produkt-name">{name}</div>\n'
        f'        <div class="produkt-hinweis">Anzeige</div>\n'
        f'      </a>')


def block(block_id: str, eintraege: list) -> str:
    karten = "\n".join(karte(key, ziel) for key, ziel in eintraege)
    return (
        f"    <!-- produktbilder:{block_id} -->\n"
        f'    <div class="produkt-grid">\n'
        f"{karten}\n"
        f"    </div>\n"
        f"    <!-- produktbilder:ende -->\n")


def setze(text: str, block_id: str, anker: str, neu: str) -> str:
    """Ersetzt einen vorhandenen Block oder haengt ihn hinter den Anker-Absatz."""
    vorhanden = re.compile(
        rf"[ \t]*<!-- produktbilder:{block_id} -->.*?<!-- produktbilder:ende -->\n", re.S)
    if vorhanden.search(text):
        return vorhanden.sub(neu, text, count=1)
    # Absatz suchen, der den Anker-Link enthaelt, und dahinter einsetzen.
    absatz = re.compile(r"<p[^>]*>(?:(?!</p>).)*?"
                        + re.escape(anker) + r"(?:(?!</p>).)*?</p>\n", re.S)
    treffer = absatz.search(text)
    if not treffer:
        return text
    return text[:treffer.end()] + neu + text[treffer.end():]


def main() -> None:
    if "--laden" in sys.argv:
        laden()
        return
    pruefen = "--pruefen" in sys.argv
    fehlend = [k for k in PRODUKTE if not (BILDER / f"{k}.jpg").exists()]
    if fehlend:
        print("Fehlende Bilder (erst 'python tools/produktbilder.py --laden'):")
        for k in fehlend:
            print(f"  ✗  {k}")
        sys.exit(1)

    geaendert = offen = 0
    for name in sorted({b[0] for b in BLOECKE}):
        seite = ROOT / name
        vorher = text = seite.read_text(encoding="utf-8")
        for seitenname, block_id, anker, eintraege in BLOECKE:
            if seitenname != name:
                continue
            neu = block(block_id, eintraege)
            danach = setze(text, block_id, anker, neu)
            if danach == text and f"produktbilder:{block_id}" not in text:
                print(f"  ✗  {name}: Anker für Block '{block_id}' nicht gefunden")
            text = danach
        if text == vorher:
            print(f"  =  {name}")
            continue
        if pruefen:
            print(f"  ~  {name} (würde geändert)")
            offen += 1
            continue
        seite.write_text(text, encoding="utf-8")
        print(f"  ✔  {name}")
        geaendert += 1
    if pruefen:
        print(f"\n{offen} Seite(n) nicht auf Stand." if offen else "\nAlle Seiten aktuell.")
        sys.exit(1 if offen else 0)
    print(f"\n{geaendert} Seite(n) aktualisiert.")


if __name__ == "__main__":
    main()
