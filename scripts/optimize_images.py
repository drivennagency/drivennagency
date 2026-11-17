#!/usr/bin/env python3
"""Maakt WebP-versies van de content-afbeeldingen (blogfoto's, cases, AI-banners).

Voor elke .jpg/.jpeg/.png in de mappen hieronder:
  naam.webp          op ware grootte
  naam-640w.webp     640 px breed (alleen als het origineel breder is)

Het build-script zet die automatisch in een <picture> met srcset, zodat browsers het
kleinste geschikte bestand laden. Originelen blijven staan en blijven de terugval.
Bestaande WebP-bestanden worden alleen opnieuw gemaakt als het origineel is veranderd
(vastgelegd met een vingerafdruk in assets/images/webp-manifest.json, zodat een verse
checkout op GitHub niet alles opnieuw maakt).

Vereist Pillow:  pip install pillow
Gebruik:         python3 scripts/optimize_images.py [--check]
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ["assets/images/uploads", "assets/ai-oplossingsbanner", "assets/images/portfolio"]
WIDTHS = (640,)
QUALITY = 80
MANIFEST = ROOT / "assets" / "images" / "webp-manifest.json"


def targets(src):
    base = src.with_suffix("")
    yield base.with_name(base.name + ".webp"), None
    for w in WIDTHS:
        yield base.with_name(f"{base.name}-{w}w.webp"), w


def sources():
    for folder in FOLDERS:
        d = ROOT / folder
        if d.is_dir():
            for f in sorted(d.rglob("*")):
                if f.suffix.lower() in (".jpg", ".jpeg", ".png") and f.is_file():
                    yield f


def fingerprint(src):
    return hashlib.sha1(src.read_bytes()).hexdigest()[:16]


def main(argv):
    check = "--check" in argv
    try:
        from PIL import Image
    except ImportError:
        print("Pillow ontbreekt: pip install pillow")
        return 1
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    made, missing, seen = 0, [], {}
    for src in sources():
        key = src.relative_to(ROOT).as_posix()
        fp = seen[key] = fingerprint(src)
        changed = manifest.get(key) != fp
        with Image.open(src) as im:
            width = im.width
            for dst, w in targets(src):
                if w and w >= width:
                    continue
                if dst.exists() and not changed:
                    continue
                if check:
                    missing.append(dst.relative_to(ROOT).as_posix())
                    continue
                out = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
                if w:
                    out = out.resize((w, round(im.height * w / width)), Image.LANCZOS)
                # Nooit groter dan het origineel: zo nodig de kwaliteit stap voor stap verlagen.
                limit = src.stat().st_size
                for quality in (QUALITY, 72, 64, 56):
                    out.save(dst, "WEBP", quality=quality, method=6)
                    if w or dst.stat().st_size < limit:
                        break
                made += 1
                print(f"  {dst.relative_to(ROOT).as_posix()} ({dst.stat().st_size // 1024} KB, "
                      f"origineel {src.stat().st_size // 1024} KB)")
    if not check and seen != manifest:
        MANIFEST.write_text(json.dumps(seen, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if check:
        for m in missing:
            print("ONTBREEKT", m)
        print(f"{len(missing)} WebP-bestand(en) ontbreken of zijn verouderd.")
        return 1 if missing else 0
    print(f"{made} WebP-bestand(en) gemaakt.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
