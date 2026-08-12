#!/usr/bin/env python3
"""Snippet-Schutz fuer die Ratgeber: data-nosnippet auf die Antwort-Hotspots.

Hintergrund: Google speist seine AI Overviews (Gemini in der Suche) aus dem
normalen Suchindex. Mit `data-nosnippet` (offiziell dokumentiert, gilt fuer
Snippets UND AI Overviews) sperren wir genau die Bloecke, die sich als
Fertig-Antwort abgreifen lassen — die Seite bleibt voll indexiert, die
Meta-Description bleibt als Anzeigetext erhalten:

  * die "Kurz gesagt"-Box (die Zusammenfassung jedes Ratgebers)
  * alle Vergleichs-/Schnellwahl-Tabellen (werden in <div data-nosnippet>
    gewickelt, weil das Attribut nur auf span/div/section gilt)

Idempotent: bereits markierte Stellen werden erkannt und uebersprungen.

Aufruf:
  python tools/ratgeber_nosnippet.py --dry-run
  python tools/ratgeber_nosnippet.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BOX_SIGNATUR = "border-left:3px solid var(--cyan)"


def schuetze(html: str) -> tuple[str, list[str]]:
    taten = []

    # 1) "Kurz gesagt"-Box: Attribut direkt auf den Box-Div setzen.
    def box(m: re.Match) -> str:
        tag = m.group(0)
        if "data-nosnippet" in tag:
            return tag
        taten.append("Kurz-gesagt-Box markiert")
        return tag.replace("<div ", "<div data-nosnippet ", 1)

    html = re.sub(r"<div [^>]*" + re.escape(BOX_SIGNATUR) + r"[^>]*>",
                  box, html)

    # 2) Tabellen in <div data-nosnippet> wickeln.
    out, pos, n = [], 0, 0
    for m in re.finditer(r"<table.*?</table>", html, flags=re.S):
        vorher = html[max(0, m.start() - 60):m.start()]
        out.append(html[pos:m.start()])
        if "data-nosnippet" in vorher:
            out.append(m.group(0))
        else:
            out.append("<div data-nosnippet>\n" + m.group(0) + "\n</div>")
            n += 1
        pos = m.end()
    out.append(html[pos:])
    if n:
        taten.append(f"{n} Tabelle(n) gewickelt")
    return "".join(out), taten


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    for pfad in sorted(ROOT.glob("ratgeber-*.html")):
        html = pfad.read_text(encoding="utf-8")
        neu, taten = schuetze(html)
        if not taten:
            print(f"OK  {pfad.name}: schon geschuetzt")
            continue
        if a.dry_run:
            print(f"(--dry-run) {pfad.name}: {', '.join(taten)}")
            continue
        pfad.write_text(neu, encoding="utf-8")
        print(f"OK  {pfad.name}: {', '.join(taten)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
