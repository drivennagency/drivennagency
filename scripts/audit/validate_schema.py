#!/usr/bin/env python3
"""Valideert de structured data (JSON-LD) met de officiële schema.org-validator.

Gebruik:
  python3 scripts/audit/validate_schema.py                 lokale bestanden (de huidige branch)
  python3 scripts/audit/validate_schema.py --live          de live site
  python3 scripts/audit/validate_schema.py pad.html ...    alleen deze bestanden

Standaard wordt per paginasoort één voorbeeld gecontroleerd (homepage, dienst, blog, AI-oplossing,
overzicht, contact) in alle drie de talen. Exitcode 1 bij fouten of als de validator onbereikbaar is.
Let op: de Rich Results Test van Google heeft geen openbare API; deze validator controleert
schema.org-geldigheid. Google-specifieke eisen staan in scripts/check_site.py en de skill.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = "https://www.drivennagency.nl"
ENDPOINT = "https://validator.schema.org/validate"
SAMPLES = ["index.html", "hosting.html", "contact.html", "blog.html", "over-ons.html",
           "blog/seo-basis-mkb.html", "ai-oplossingen/offertes-planningen-facturen.html"]


PAUSE = 4          # seconden tussen verzoeken: de validator begrenst het aantal verzoeken
RETRIES = 4


def validate(field, value):
    data = urllib.parse.urlencode({field: value}).encode()
    for attempt in range(RETRIES):
        req = urllib.request.Request(ENDPOINT, data=data, headers={"User-Agent": "drivenn-seo-audit"})
        try:
            raw = urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")
            return json.loads(raw[raw.find("{"):])   # het antwoord begint met een anti-XSSI-prefix
        except urllib.error.HTTPError as e:
            # 429/405 = te veel verzoeken: even wachten en opnieuw proberen
            if e.code in (405, 429, 503) and attempt < RETRIES - 1:
                time.sleep(PAUSE * 4 * (attempt + 1))
                continue
            raise


def problems(result):
    out = []

    def walk(node):
        for e in node.get("errors", []):
            out.append(f"{node.get('typeGroup')}: {e}")
        for prop in node.get("properties", []):
            for e in prop.get("errors", []):
                out.append(f"{node.get('typeGroup')}.{prop.get('pred')}: {e}")
            if isinstance(prop.get("target"), dict):
                walk(prop["target"])
    for group in result.get("tripleGroups", []):
        for node in group.get("nodes", []):
            walk(node)
    return out


def main(argv):
    live = "--live" in argv
    files = [a for a in argv[1:] if not a.startswith("--")]
    targets = files or [f"{prefix}{rel}" for prefix in ("", "eng/", "de/") for rel in SAMPLES]
    failed = unreachable = 0
    for i, rel in enumerate(targets):
        if i:
            time.sleep(PAUSE)
        try:
            if live:
                path = "/" + rel.replace("index.html", "")
                result = validate("url", SITE + path)
            else:
                result = validate("html", (ROOT / rel).read_text(encoding="utf-8"))
        except Exception as e:   # netwerk of onverwacht antwoord
            print(f"??   {rel}: validator niet bereikbaar ({e})")
            unreachable += 1
            continue
        errs = problems(result)
        types = sorted({g.get("type") for g in result.get("tripleGroups", [])} - {None})
        status = "OK  " if not errs and not result.get("totalNumErrors") else "FOUT"
        print(f"{status} {rel:55} fouten {result.get('totalNumErrors', 0)}, waarschuwingen "
              f"{result.get('totalNumWarnings', 0)}  {', '.join(types)}")
        for e in errs:
            print("     ", e)
        failed += bool(errs or result.get("totalNumErrors"))
    print(f"{len(targets)} pagina's: {failed} met fouten, {unreachable} niet te controleren (validator onbereikbaar).")
    return 1 if failed or unreachable else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
