#!/usr/bin/env python3
"""Freistellen des Draco-Labs-Logos für den hellen/dunklen Seiten-Hintergrund.

Das Quell-Logo (branding/logo-master.png) hat einen eingebackenen grauen
Verlaufs-Hintergrund, wodurch es auf der Seite wie ein aufgesetzter Kasten wirkt.
Dieses Skript entfernt den Hintergrund und speichert eine transparente Version,
die sich nahtlos in den Seiten-Hintergrund einfügt (kein sichtbarer Rand).

Verfahren:
1. Hintergrund = entsättigte, mittelhelle Pixel (Grau-Verlauf + Vignette).
2. Nur die vom Bildrand aus zusammenhängende Fläche wird transparent gemacht
   (Magic-Wand), damit dunkle Drachen-Innenflächen erhalten bleiben.
3. Kleine graue Rest-Inseln werden entfernt, weiße/farbige Details bleiben.
4. Kanten leicht gefeathert, auf Inhalts-Bounding-Box zugeschnitten.

Aufruf:  python tools/make_transparent_logo.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

# Quelle liegt im Schwester-Repo draco-labs; Ziel im Website-Repo.
REPO = Path(__file__).resolve().parents[1]
SRC = REPO.parent / "draco-labs" / "branding" / "logo-master.png"
DST = REPO / "assets" / "logo-hero.png"


def main() -> None:
    im = Image.open(SRC).convert("RGBA")
    arr = np.asarray(im).astype(np.float32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = mx - mn
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    # Hintergrund-Kandidaten: entsättigt und nicht hell (Silber bleibt erhalten).
    cand = (sat < 30) & (lum < 135)

    # Nur die vom Rand zusammenhängende Fläche entfernen (Magic-Wand).
    lbl, _ = ndimage.label(cand)
    border = set(np.unique(np.concatenate([lbl[0, :], lbl[-1, :], lbl[:, 0], lbl[:, -1]])))
    border.discard(0)
    keep = ~np.isin(lbl, list(border))

    # Kleine GRAUE Rest-Inseln entfernen (Weiß/Farbe behalten).
    olbl, on = ndimage.label(keep)
    idx = np.arange(1, on + 1)
    sizes = ndimage.sum(np.ones_like(olbl), olbl, index=idx)
    msat = ndimage.mean(sat, olbl, index=idx)
    mlum = ndimage.mean(lum, olbl, index=idx)
    rm = [i + 1 for i in range(on) if sizes[i] < 2000 and msat[i] < 24 and 28 < mlum[i] < 140]
    if rm:
        keep[np.isin(olbl, rm)] = False

    alpha = np.where(keep, 255, 0).astype("uint8")
    a = (Image.fromarray(alpha, "L")
         .filter(ImageFilter.MedianFilter(5))
         .filter(ImageFilter.GaussianBlur(1.0)))
    out = im.copy()
    out.putalpha(a)
    out = out.crop(out.getbbox())

    DST.parent.mkdir(parents=True, exist_ok=True)
    out.save(DST)
    print(f"geschrieben: {DST}  ({out.size[0]}x{out.size[1]})")


if __name__ == "__main__":
    main()
