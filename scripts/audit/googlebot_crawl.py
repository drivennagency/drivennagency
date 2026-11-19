#!/usr/bin/env python3
"""Haalt de site op zoals Googlebot Smartphone dat doet en controleert of alles indexeerbaar is.

Gebruik:  python3 scripts/audit/googlebot_crawl.py [basis-URL]
          (standaard https://www.drivennagency.nl; voor lokaal: http://localhost:8123)

Controleert:
  - robots.txt (bereikbaar, verwijst naar de sitemap, blokkeert geen pagina's/CSS/JS);
  - sitemap.xml (geldige XML, absolute URL's);
  - elke sitemap-URL: status 200 zonder redirect, HTML, canonical naar zichzelf, geen noindex
    (meta of X-Robots-Tag), hreflang met x-default, HTML onder 2 MB, geldige JSON-LD;
  - randgevallen: onbekende pagina's geven 404, /index.html-varianten verwijzen permanent door,
    http en zonder-www komen uit op https://www.
Exitcode 1 bij fouten.
"""
import gzip
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

UA = ("Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/135.0.0.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
CANONICAL_HOST = "https://www.drivennagency.nl"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    try:
        r = OPENER.open(req, timeout=30)
        status, headers, body = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        status, headers, body = e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
    if headers.get("content-encoding") == "gzip":
        body = gzip.decompress(body)
    return status, headers, body


def main(argv):
    base = (argv[1] if len(argv) > 1 else CANONICAL_HOST).rstrip("/")
    live = base.startswith(CANONICAL_HOST)
    errors, notes = [], []

    st, h, robots = get(base + "/robots.txt")
    robots = robots.decode("utf-8", "replace")
    if st != 200:
        errors.append(f"robots.txt geeft status {st}")
    if "Sitemap:" not in robots:
        errors.append("robots.txt verwijst niet naar de sitemap")
    for line in robots.splitlines():
        m = re.match(r"\s*Disallow:\s*(\S+)", line, re.I)
        if m and m.group(1) not in ("/api/",):
            notes.append(f"robots.txt blokkeert {m.group(1)} (bewust?)")

    st, h, sm = get(base + "/sitemap.xml")
    if st != 200:
        errors.append(f"sitemap.xml geeft status {st}")
        sm = b"<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'/>"
    try:
        root = ET.fromstring(sm)
    except ET.ParseError as e:
        print(f"FOUT sitemap.xml is geen geldige XML: {e}")
        return 1
    urls = [u.findtext("s:loc", namespaces=NS) for u in root.findall("s:url", NS)]
    if len(urls) != len(set(urls)):
        errors.append("sitemap.xml bevat dubbele URL's")
    print(f"robots.txt en sitemap gelezen: {len(urls)} URL's")

    for url in urls:
        fetch = url.replace(CANONICAL_HOST, base) if not live else url
        st, h, body = get(fetch)
        text = body.decode("utf-8", "replace")
        where = urlsplit(url).path
        if not url.startswith(CANONICAL_HOST + "/"):
            errors.append(f"{where}: sitemap-URL is niet absoluut op {CANONICAL_HOST}")
        if st != 200:
            errors.append(f"{where}: status {st} {h.get('location', '')}".strip())
            continue
        if "text/html" not in h.get("content-type", ""):
            errors.append(f"{where}: Content-Type {h.get('content-type')}")
        canon = re.findall(r'<link rel="canonical" href="([^"]+)"', text)
        if canon != [url]:
            errors.append(f"{where}: canonical {canon} (verwacht {url})")
        robots_meta = " ".join(re.findall(r'<meta name="robots" content="([^"]+)"', text))
        if "noindex" in robots_meta or "noindex" in h.get("x-robots-tag", ""):
            errors.append(f"{where}: staat in de sitemap maar heeft noindex")
        hreflang = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', text))
        if "x-default" not in hreflang:
            errors.append(f"{where}: hreflang x-default ontbreekt")
        if len(body) > 2_000_000:
            errors.append(f"{where}: HTML is {len(body)} bytes (Googlebot leest de eerste 2 MB)")
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
            try:
                json.loads(block)
            except ValueError as e:
                errors.append(f"{where}: ongeldige JSON-LD ({e})")

    # Randgevallen
    for path, want in [("/deze-pagina-bestaat-niet-" + "x9", 404), ("/eng/bestaat-niet-x9", 404)]:
        st, _, _ = get(base + path)
        if st != want:
            errors.append(f"{path}: status {st}, verwacht {want} (anders: 'soft 404' in Search Console)")
    if live:
        for path, target in [("/index.html", "/"), ("/eng/index.html", "/eng/"), ("/de/index.html", "/de/")]:
            st, h, _ = get(base + path)
            if st not in (301, 308) or not h.get("location", "").endswith(target):
                errors.append(f"{path}: {st} -> {h.get('location')}, verwacht permanente redirect naar {target}")
        for variant in ["http://drivennagency.nl/", "https://drivennagency.nl/", "http://www.drivennagency.nl/"]:
            url, hops = variant, 0
            while hops < 5:
                st, h, _ = get(url)
                if st in (301, 302, 307, 308):
                    url, hops = h.get("location"), hops + 1
                else:
                    break
            if url != CANONICAL_HOST + "/" or st != 200:
                errors.append(f"{variant} komt uit op {url} ({st}), verwacht {CANONICAL_HOST}/")
            elif hops > 2:
                notes.append(f"{variant}: {hops} redirects tot {CANONICAL_HOST}/")

    for n in notes:
        print("LET OP", n)
    for e in errors:
        print("FOUT", e)
    print(f"{len(urls)} sitemap-URL's gecontroleerd als Googlebot Smartphone: {len(errors)} fout(en).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
