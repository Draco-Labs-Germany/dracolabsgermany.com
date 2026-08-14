#!/usr/bin/env python3
"""Baut sitemap.xml aus dem tatsaechlichen Seitenbestand.

Von Hand gepflegt driftet die Sitemap von der Realitaet weg — Befund vom
2026-08-14: impressum und datenschutz standen drin, obwohl beide auf noindex
stehen, kein einziger Eintrag hatte ein <lastmod>, obwohl die Ratgeber ihr
dateModified im JSON-LD mitfuehren.

Regeln:
  * aufgenommen wird nur, was NICHT auf noindex steht,
  * <lastmod> kommt aus dem JSON-LD (dateModified, sonst datePublished),
  * die Startseite bekommt Prioritaet 1.0, alles andere 0.8.

Idempotent: erzeugt dieselbe Datei, solange sich die Seiten nicht aendern.

Aufruf:  python tools/sitemap_build.py [--pruefen]
"""

import re
import sys
from pathlib import Path

try:                                  # Windows-Konsole ist cp1252, ✔ wirft sonst.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent
BASIS = "https://dracolabsgermany.com"
ZIEL = ROOT / "sitemap.xml"

NOINDEX_RE = re.compile(r'<meta\s+name="robots"\s+content="[^"]*noindex', re.I)
MOD_RE = re.compile(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})')
PUB_RE = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')


def eintraege() -> list[tuple[str, str | None, str]]:
    zeilen = []
    for seite in sorted(ROOT.glob("*.html")):
        text = seite.read_text(encoding="utf-8")
        if NOINDEX_RE.search(text):
            continue
        treffer = MOD_RE.search(text) or PUB_RE.search(text)
        stand = treffer.group(1) if treffer else None
        if seite.name == "index.html":
            zeilen.insert(0, (f"{BASIS}/", stand, "1.0"))
        else:
            zeilen.append((f"{BASIS}/{seite.name}", stand, "0.8"))
    return zeilen


def xml(zeilen) -> str:
    teile = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, stand, prio in zeilen:
        teile.append("  <url>")
        teile.append(f"    <loc>{url}</loc>")
        if stand:
            teile.append(f"    <lastmod>{stand}</lastmod>")
        teile.append("    <changefreq>monthly</changefreq>")
        teile.append(f"    <priority>{prio}</priority>")
        teile.append("  </url>")
    teile.append("</urlset>")
    return "\n".join(teile) + "\n"


def main() -> None:
    neu = xml(eintraege())
    alt = ZIEL.read_text(encoding="utf-8") if ZIEL.exists() else ""
    if neu == alt:
        print("sitemap.xml ist aktuell.")
        return
    if "--pruefen" in sys.argv:
        print("sitemap.xml wäre zu ändern.")
        sys.exit(1)
    ZIEL.write_text(neu, encoding="utf-8")
    print(f"sitemap.xml geschrieben: {neu.count('<url>')} Seiten, "
          f"{neu.count('<lastmod>')} mit lastmod.")


if __name__ == "__main__":
    main()
