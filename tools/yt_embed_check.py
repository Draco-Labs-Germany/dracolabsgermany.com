#!/usr/bin/env python3
"""Prueft YouTube-Videos, bevor wir sie auf der Website einbetten.

Warum ein Tool: Ein Embed, das der Uploader gesperrt hat, zeigt beim Leser nur
"Video ansehen auf YouTube" statt eines Players; ein geloeschtes oder privat
gestelltes Video zeigt gar nichts.  Beides faellt bei uns sonst erst auf, wenn
es jemand meldet.  Das Skript beantwortet je Video drei Fragen:

  1. Gibt es das Video oeffentlich?      (oEmbed-Endpunkt antwortet)
  2. Von welchem Kanal stammt es?        (author_name/author_url aus oEmbed)
  3. Darf es eingebettet werden?         (playableInEmbed auf der Watch-Seite)

Fremde Videos duerfen wir einbetten, wenn der Uploader das Einbetten erlaubt:
Der Player laeuft dann von YouTube aus, wir spiegeln nichts.  Genau das prueft
Punkt 3.  Ohne Argumente werden die im Repo eingebetteten IDs geprueft, sonst
die uebergebenen.

Mit --details kommen zusaetzlich Laufzeit, Veroeffentlichungsdatum und der
Beschreibungsanfang dazu.  Das braucht man, um fremde Videos einzuordnen, etwa
um eigene Aufnahmen von Re-Uploads fremder Sendungen zu unterscheiden.

Aufruf:  python tools/yt_embed_check.py [--details] [VIDEO_ID_ODER_URL ...]
"""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:                                  # Windows-Konsole ist cp1252, ✔ wirft sonst.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent
KOPF = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ID_RE = re.compile(r"(?:youtu\.be/|v=|embed/)([A-Za-z0-9_-]{11})")


def video_id(text: str) -> str:
    m = ID_RE.search(text)
    return m.group(1) if m else text


def hole(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=KOPF)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def pruefe(vid: str) -> dict:
    """Titel, Kanal und Einbettbarkeit eines Videos ermitteln."""
    ergebnis = {"id": vid, "titel": None, "kanal": None, "kanal_url": None,
                "oeffentlich": False, "einbettbar": None, "fehler": None}
    oembed = ("https://www.youtube.com/oembed?format=json&url="
              + urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}", safe=""))
    try:
        d = json.loads(hole(oembed))
        ergebnis.update(oeffentlich=True, titel=d.get("title"),
                        kanal=d.get("author_name"), kanal_url=d.get("author_url"))
    except urllib.error.HTTPError as e:
        ergebnis["fehler"] = f"oEmbed HTTP {e.code} (nicht oeffentlich?)"
        return ergebnis
    except Exception as e:                       # Netzfehler, Timeout, kaputtes JSON
        ergebnis["fehler"] = f"oEmbed: {e}"
        return ergebnis

    try:                                          # Einbett-Flag der Watch-Seite
        seite = hole(f"https://www.youtube.com/watch?v={vid}")
        if '"playableInEmbed":true' in seite:
            ergebnis["einbettbar"] = True
        elif '"playableInEmbed":false' in seite:
            ergebnis["einbettbar"] = False
        for schluessel, muster in (("dauer", r'"lengthSeconds":"(\d+)"'),
                                   ("datum", r'"publishDate":"([\d-]+)"'),
                                   ("text", r'"shortDescription":"(.*?)","isCrawlable"')):
            m = re.search(muster, seite)
            if m:
                ergebnis[schluessel] = m.group(1)
    except Exception as e:
        ergebnis["fehler"] = f"Watch-Seite: {e}"
    return ergebnis


def dauer_lesbar(sekunden: str | None) -> str:
    if not sekunden:
        return "?"
    s = int(sekunden)
    return f"{s // 60}:{s % 60:02d}"


def eingebettete_ids() -> list[str]:
    """Alle IDs, die im Repo schon in einem Player stecken."""
    ids = []
    for seite in sorted(ROOT.glob("*.html")):
        for m in re.finditer(r"youtube(?:-nocookie)?\.com/embed/([A-Za-z0-9_-]{11})",
                             seite.read_text(encoding="utf-8")):
            if m.group(1) not in ids:
                ids.append(m.group(1))
    return ids


def main() -> None:
    details = "--details" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    ids = [video_id(a) for a in args] or eingebettete_ids()
    if not ids:
        sys.exit("Keine Video-IDs uebergeben und keine im Repo gefunden.")

    schlecht = 0
    for vid in ids:
        r = pruefe(vid)
        if not r["oeffentlich"]:
            print(f"  X  {vid}  {r['fehler']}")
            schlecht += 1
            continue
        zeichen = {True: "OK ", False: "X  ", None: "?  "}[r["einbettbar"]]
        if r["einbettbar"] is not True:
            schlecht += 1
        print(f"  {zeichen}{vid}  {r['kanal']}  |  {r['titel']}")
        if r["einbettbar"] is False:
            print("       Einbetten vom Uploader gesperrt, nur verlinken.")
        elif r["einbettbar"] is None:
            print(f"       Einbett-Flag nicht lesbar ({r['fehler'] or 'kein Flag'}), von Hand pruefen.")
        if r["kanal_url"]:
            print(f"       Kanal: {r['kanal_url']}")
        if details:
            print(f"       {dauer_lesbar(r.get('dauer'))} min, "
                  f"vom {r.get('datum', '?')}")
            text = (r.get("text") or "").encode().decode("unicode_escape", "replace")
            print(f"       {text[:300].strip() or '(keine Beschreibung)'}")

    print(f"\n{len(ids)} Video(s) geprueft, {schlecht} auffaellig.")
    sys.exit(1 if schlecht else 0)


if __name__ == "__main__":
    main()
