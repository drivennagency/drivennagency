#!/usr/bin/env python3
"""Controleert de gegenereerde website op fouten die Google of bezoekers zouden merken.

Gebruik:  python3 scripts/check_site.py          (exitcode 1 bij fouten)

Wat er gecontroleerd wordt, per HTML-pagina:
  - interne links en bronnen (href/src/srcset) wijzen naar een bestaand bestand;
  - #ankers bestaan op de doelpagina;
  - <html lang>, precies één <title>, één <h1>, meta description;
  - indexeerbare pagina's: canonical naar zichzelf, hreflang voor alle talen + x-default,
    en wederkerige hreflang (pagina A verwijst naar B en B terug naar A);
  - JSON-LD is geldige JSON met @context/@type; FAQ-vragen staan ook zichtbaar op de pagina;
  - afbeeldingen hebben een alt-attribuut;
en voor de sitemap: elke URL bestaat, is indexeerbaar en elke indexeerbare pagina staat erin.
Waarschuwingen (bv. lange titels) laten de controle niet falen.
"""
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://www.drivennagency.nl"
SKIP_DIRS = {"admin", "components", "node_modules", ".git", ".github", "scripts", "tests", "content"}
LANG_OF = {"": "nl", "eng": "en", "de": "de"}
TITLE_WARN, DESC_MIN, DESC_MAX = 65, 50, 170


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.imgs = set(), [], []
        self.titles, self.h1, self.meta, self.linkrel = [], 0, {}, []
        self.jsonld, self.lang = [], None
        self._in_title = self._in_ld = self._in_script = False
        self._buf, self.text = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("name"):
            self.ids.add(a["name"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title, self._buf = True, []
        elif tag == "h1":
            self.h1 += 1
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta.setdefault(key, []).append(a.get("content", ""))
        elif tag == "link":
            self.linkrel.append(a)
        elif tag == "script":
            self._in_script = True
            if a.get("type") == "application/ld+json":
                self._in_ld, self._buf = True, []
        elif tag == "img":
            self.imgs.append(a)
        for attr in ("href", "src", "poster", "data-src"):
            if a.get(attr) and tag != "link" or (tag == "link" and attr == "href" and a.get("rel") in ("stylesheet", "icon", "apple-touch-icon", "manifest", "preload")):
                if a.get(attr):
                    self.links.append((tag, attr, a[attr]))
        if a.get("srcset"):
            for part in a["srcset"].split(","):
                if part.strip():
                    self.links.append((tag, "srcset", part.strip().split()[0]))

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self.titles.append("".join(self._buf).strip())
            self._in_title = False
        elif tag == "script":
            if self._in_ld:
                self.jsonld.append("".join(self._buf))
            self._in_ld = self._in_script = False

    def handle_data(self, data):
        if self._in_title or self._in_ld:
            self._buf.append(data)
        elif not self._in_script:
            self.text.append(data)


def html_files():
    for p in sorted(ROOT.rglob("*.html")):
        rel = p.relative_to(ROOT)
        if rel.parts[0] in SKIP_DIRS:
            continue
        yield rel


def url_for(rel):
    s = rel.as_posix()
    if s.endswith("index.html"):
        s = s[: -len("index.html")]
    return SITE + "/" + s


def file_for(path):
    """Pad zoals de server het ziet -> bestand in de repo (of None)."""
    path = unquote(path)
    target = ROOT / path.lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"
    if target.is_file():
        return target
    if target.is_dir() and (target / "index.html").is_file():
        return target / "index.html"
    return None


def main():
    errors, warnings = [], []
    pages = {}
    for rel in html_files():
        parser = Page()
        parser.feed((ROOT / rel).read_text(encoding="utf-8"))
        pages[rel] = parser

    by_url = {url_for(rel): rel for rel in pages}

    for rel, pg in pages.items():
        where = rel.as_posix()
        err = lambda msg: errors.append(f"{where}: {msg}")
        warn = lambda msg: warnings.append(f"{where}: {msg}")
        robots = " ".join(pg.meta.get("robots", []))
        noindex = "noindex" in robots
        is_404 = rel.name == "404.html"
        folder = rel.parts[0] if len(rel.parts) > 1 and rel.parts[0] in LANG_OF else ""
        expected_lang = LANG_OF.get(folder, "nl")

        # Basis
        if pg.lang != expected_lang:
            err(f'<html lang="{pg.lang}"> verwacht "{expected_lang}"')
        if len(pg.titles) != 1 or not pg.titles[0]:
            err(f"{len(pg.titles)} <title>-elementen (verwacht 1, niet leeg)")
        elif not noindex:
            # Google: geen harde limiet, wel afkapping. De merknaam hoort erbij, dus we kijken
            # naar het beschrijvende deel vóór " | ".
            core = pg.titles[0].split(" | ")[0]
            if len(core) > TITLE_WARN:
                warn(f"titel (zonder merknaam) is {len(core)} tekens (> {TITLE_WARN}): {pg.titles[0]}")
            if pg.titles[0] != "Drivenn Agency" and "Drivenn Agency" not in pg.titles[0]:
                warn(f"titel zonder merknaam: {pg.titles[0]}")
        if pg.h1 != 1:
            err(f"{pg.h1} <h1>-koppen (verwacht 1)")
        desc = pg.meta.get("description", [])
        if len(desc) != 1 and not is_404:
            err(f"{len(desc)} meta descriptions (verwacht 1)")
        elif desc and not noindex and not (DESC_MIN <= len(desc[0]) <= DESC_MAX):
            warn(f"meta description is {len(desc[0])} tekens (advies {DESC_MIN}-{DESC_MAX})")

        # Links en ankers
        for tag, attr, value in pg.links:
            value = html.unescape(value)
            parts = urlsplit(value)
            if parts.scheme in ("mailto", "tel", "javascript", "data") or value.startswith("#") and len(value) == 1:
                continue
            if parts.scheme in ("http", "https"):
                if parts.netloc in ("www.drivennagency.nl", "drivennagency.nl") and tag in ("a",):
                    warn(f"absolute interne link {value} (gebruik een pad)")
                continue
            if not parts.path:
                if parts.fragment and parts.fragment not in pg.ids:
                    err(f"anker #{parts.fragment} bestaat niet op deze pagina")
                continue
            if not parts.path.startswith("/"):
                err(f"relatieve link {value} (gebruik een pad vanaf de root)")
                continue
            target = file_for(parts.path)
            if target is None:
                err(f"kapotte link {tag}[{attr}] -> {value}")
                continue
            if parts.path.endswith("/index.html") and tag == "a":
                warn(f"link naar {parts.path}; gebruik de map zonder index.html")
            if parts.fragment and target.suffix == ".html":
                trel = target.relative_to(ROOT)
                if trel in pages and parts.fragment not in pages[trel].ids:
                    err(f"anker {value} bestaat niet op {trel.as_posix()}")

        for img in pg.imgs:
            if "alt" not in img:
                err(f"afbeelding zonder alt: {img.get('src')}")

        # JSON-LD
        for block in pg.jsonld:
            try:
                data = json.loads(block)
            except ValueError as e:
                err(f"ongeldige JSON-LD: {e}")
                continue
            items = data if isinstance(data, list) else data.get("@graph", [data])
            for item in items:
                if "@type" not in item:
                    err("JSON-LD zonder @type")
                if item is data and "@context" not in data:
                    err("JSON-LD zonder @context")
                if item.get("@type") == "FAQPage":
                    visible = re.sub(r"\s+", " ", " ".join(pg.text))
                    for q in item.get("mainEntity", []):
                        name = re.sub(r"\s+", " ", q.get("name", "")).strip()
                        if name and name not in visible:
                            err(f"FAQ-vraag staat niet zichtbaar op de pagina: {name}")
                        if "&#" in json.dumps(q, ensure_ascii=False):
                            err(f"FAQ bevat HTML-entiteiten: {name}")

        # Canonical + hreflang
        canon = [l.get("href") for l in pg.linkrel if l.get("rel") == "canonical"]
        alts = {l.get("hreflang"): l.get("href") for l in pg.linkrel if l.get("rel") == "alternate" and l.get("hreflang")}
        if is_404:
            if canon:
                err("404-pagina hoort geen canonical te hebben")
            continue
        if noindex:
            continue
        own = url_for(rel)
        if canon != [own]:
            err(f"canonical {canon} verwacht [{own}]")
        if alts.get(expected_lang) != own:
            err(f"hreflang {expected_lang} verwijst niet naar de pagina zelf")
        if "x-default" not in alts:
            err("hreflang x-default ontbreekt")
        for code, href in alts.items():
            trel = by_url.get(href)
            if trel is None:
                err(f"hreflang {code} -> {href} bestaat niet")
                continue
            back = {l.get("hreflang"): l.get("href") for l in pages[trel].linkrel if l.get("rel") == "alternate"}
            if code != "x-default" and back.get(expected_lang) != own:
                err(f"hreflang {code} -> {href} verwijst niet terug (wederkerigheid)")
        og = pg.meta.get("og:url", [])
        if og != [own]:
            err(f"og:url {og} verwacht [{own}]")
        for key in ("og:title", "og:description", "og:image"):
            if not pg.meta.get(key):
                err(f"{key} ontbreekt")

    # Sitemap
    try:
        tree = ET.parse(ROOT / "sitemap.xml")
    except (ET.ParseError, OSError) as e:
        errors.append(f"sitemap.xml: {e}")
        tree = None
    if tree is not None:
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [u.findtext("s:loc", namespaces=ns) for u in tree.getroot().findall("s:url", ns)]
        if len(locs) != len(set(locs)):
            errors.append("sitemap.xml: dubbele URL's")
        for u in tree.getroot().findall("s:url", ns):
            lm = u.findtext("s:lastmod", namespaces=ns)
            if lm and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lm):
                errors.append(f"sitemap.xml: ongeldige lastmod {lm}")
        indexable = {url_for(r) for r, pg in pages.items()
                     if r.name != "404.html" and "noindex" not in " ".join(pg.meta.get("robots", []))}
        for loc in locs:
            if loc not in by_url:
                errors.append(f"sitemap.xml: {loc} bestaat niet")
            elif loc not in indexable:
                errors.append(f"sitemap.xml: {loc} is niet indexeerbaar (noindex/404)")
        for missing in sorted(indexable - set(locs)):
            errors.append(f"sitemap.xml: indexeerbare pagina ontbreekt: {missing}")

    for w in warnings:
        print("WAARSCHUWING", w)
    for e in errors:
        print("FOUT", e)
    print(f"{len(pages)} pagina's gecontroleerd: {len(errors)} fout(en), {len(warnings)} waarschuwing(en).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
