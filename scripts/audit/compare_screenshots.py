#!/usr/bin/env python3
"""Vergelijkt twee mappen met schermafbeeldingen (van scripts/audit/screenshots.js) pixel voor pixel.

Gebruik:  python3 scripts/audit/compare_screenshots.py <map-voor> <map-na> [drempel-%]
Vereist:  Pillow en numpy (pip install pillow numpy)

Toont per pagina het percentage gewijzigde pixels, de hoogteverandering en waar de
verschillen zitten (y-bereik), gesorteerd van grootste naar kleinste verschil.
Pagina's onder de drempel (standaard 0.3%) worden alleen geteld.
Bekijk grote verschillen altijd zelf: een verschil is niet per se fout (bv. nieuwe inhoud).
"""
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageChops
except ImportError:
    print("Pillow/numpy ontbreken: pip install pillow numpy")
    sys.exit(2)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    a_dir, b_dir = Path(argv[1]), Path(argv[2])
    threshold = float(argv[3]) if len(argv) > 3 else 0.3
    rows, missing = [], []
    for fa in sorted(a_dir.glob("*.png")):
        fb = b_dir / fa.name
        if not fb.exists():
            missing.append(fa.name)
            continue
        a, b = Image.open(fa).convert("RGB"), Image.open(fb).convert("RGB")
        h = max(a.height, b.height)
        pa = Image.new("RGB", (a.width, h), "white"); pa.paste(a)
        pb = Image.new("RGB", (b.width, h), "white"); pb.paste(b)
        diff = np.asarray(ImageChops.difference(pa, pb)).max(axis=2) > 24
        ys = np.where(diff.any(axis=1))[0]
        where = f"y={ys.min()}..{ys.max()}" if len(ys) else "-"
        rows.append((diff.mean() * 100, fa.name, f"hoogte {a.height}->{b.height}, verschil {where}"))
    rows.sort(reverse=True)
    for pct, name, info in rows:
        if pct > threshold:
            print(f"{pct:6.2f}%  {name}  {info}")
    small = sum(1 for r in rows if r[0] <= threshold)
    for m in missing:
        print("ONTBREEKT in", b_dir, m)
    print(f"{len(rows)} vergeleken: {len(rows) - small} boven {threshold}%, {small} (vrijwel) gelijk.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
