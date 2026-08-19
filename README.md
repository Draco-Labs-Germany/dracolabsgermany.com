# dracolabsgermany.com

Website der Draco Labs Germany — Drohnen · Prototyping · Beratung.
Statische Seite, gehostet über GitHub Pages.

Dieses Repo ist öffentlich und enthält nur ausgelieferte Dateien.
Die Werkzeuge, die die Seiten erzeugen und prüfen (`check_ratgeber.py`,
`ratgeber_karussell.py`, `sitemap_build.py`, `og_bild.py` und die übrigen),
liegen im privaten Repo `draco-labs` unter `tools/` und schreiben von dort
hierher. Aufruf also aus `draco-labs`, nicht aus diesem Verzeichnis:

    python tools/check_ratgeber.py

## Arbeitsregeln

- **Nicht von Hand editieren**, was ein Werkzeug erzeugt: Kopf-Navigation,
  Footer, Social-Leiste, Partnerblock, Video-Einbettungen, Standbilder,
  Meta-Tags, `og:`-Bilder, `robots.txt` und `sitemap.xml` werden nachgezogen
  und überschreiben Handarbeit beim nächsten Lauf.
- **Commits nur als „Draco Labs Germany <info@dracolabsgermany.com>"** über den
  SSH-Alias `github-dracolabs` — nie unter dem privaten Konto.
- **Live ist erst, was gepusht ist.** Der Push ist die letzte Stufe der
  Inhaltskette; den täglichen Nachlauf (erschienene Videos einbetten, Sitemap,
  Push) fährt der `homeserver` um 20:00.
- Seiten, die bewusst **nicht** in der `sitemap.xml` stehen: Rechtsseiten,
  `tiktok-callback.html` und vorübergehend offline genommene Teilelisten.
