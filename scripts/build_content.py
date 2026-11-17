#!/usr/bin/env python3
"""
Bouwt de statische Drivenn Agency-site (NL in de root, EN in /eng/, DE in /de/).

Wat dit script doet, in deze volgorde:

1. Leest de content uit content/blog, content/ai en content/cases (JSON, door het
   CMS beheerd) en genereert daaruit de blog- en AI-detailpagina's per taal.
2. Loopt daarna over ELKE pagina (handgeschreven + gegenereerd) en:
   - zet header en footer erin (components/header*.html, footer*.html);
   - vult de kaart-blokken (blog, AI, cases) tussen hun <!--#...#--> markers;
   - maakt alle interne links en bestandspaden root-absoluut (/contact.html),
     zodat ze op elke diepte werken, ook op de 404-pagina;
   - bouwt het beheerde deel van de <head> opnieuw op: stylesheet, favicons,
     canonical, hreflang, Open Graph, Twitter-kaart, structured data, analytics.
3. Schrijft sitemap.xml.

Belangrijk voor wie een pagina met de hand aanpast:
- Alles tussen <!--AUTO:HEAD--> en <!--/AUTO:HEAD--> wordt bij elke build
  overschreven. Zet daar dus niets handmatig neer.
- Buiten dat blok beheer je zelf: <title>, <meta name="description">, een
  eventuele <meta name="robots" content="noindex"> en optioneel een afwijkende
  og:title / og:description / og:image.
- Het script is idempotent: twee keer draaien levert exact dezelfde bestanden op.

Gebruik:
    python3 scripts/build_content.py           # bouwen
    python3 scripts/build_content.py --check   # alleen controleren of alles up-to-date is
"""
import hashlib
import html
import json
import pathlib
import posixpath
import re
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://www.drivennagency.nl"
BRAND = "Drivenn Agency"

# ---------------------------------------------------------------------------
# Configuratie
# ---------------------------------------------------------------------------
# Talen: "dir" is de map op de site, "sfx" het achtervoegsel van de componenten.
LANGS = {
    "nl": {"dir": "",    "sfx": "",    "code": "nl", "locale": "nl_NL"},
    "en": {"dir": "eng", "sfx": ".en", "code": "en", "locale": "en_GB"},
    "de": {"dir": "de",  "sfx": ".de", "code": "de", "locale": "de_DE"},
}
ACTIVE = ["nl", "en", "de"]
DEFAULT_LANG = "nl"

GA_ID = "G-4VXJQRECQ6"           # Google Analytics 4 (laadt pas na cookie-akkoord)
THEME_COLOR = "#0E2340"
DEFAULT_OG_IMAGE = "/assets/images/og-default.jpg"   # 1200x630
LOGO_SQUARE = "/assets/logo/logo-op-witte-achtergrond.png"
ORG_ID = f"{SITE}/#organization"
WEBSITE_ID = f"{SITE}/#website"
# Alleen echte, bestaande profielen: Google gebruikt deze als 'sameAs'.
SOCIAL_PROFILES = ["https://www.instagram.com/drivennagency/"]
ORG = {
    "email": "info@drivennagency.nl",
    "telephone": "+31681835935",
    "kvk": "86749439",
    "region": "Westland",
    "country": "NL",
}
# Lettertypen die boven de vouw nodig zijn: vooraf laden scheelt een omweg via de CSS.
PRELOAD_FONTS = ["/assets/fonts/poppins-latin-700-normal.woff2",
                 "/assets/fonts/open-sans-latin-400-normal.woff2"]
# Pagina's die een dienst beschrijven krijgen Service-structured data.
SERVICE_PAGES = {"nieuwe-website.html", "redesign.html", "hosting.html"}
# Vaste volgorde van de statische pagina's in de sitemap (rest volgt alfabetisch).
SITEMAP_ORDER = ["index.html", "websites.html", "nieuwe-website.html", "redesign.html", "hosting.html",
                 "ai-oplossingen.html", "concept.html", "cases.html", "blog.html", "over-ons.html",
                 "contact.html"]
TITLE_MAX = 65   # langere <title>'s kapt Google af; dan laten we het merk-achtervoegsel weg

MONTHS = {
    "nl": ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september",
           "oktober", "november", "december"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September",
           "Oktober", "November", "Dezember"],
}

# Vaste teksten per taal (HTML: '&' is al als &amp; geschreven).
UI = {
    "nl": {
        "cat_ai": {"documenten": "Documenten &amp; administratie", "tekst": "Tekst &amp; data",
                   "communicatie": "Klantcommunicatie"},
        "ai_default_cat": "AI-oplossing",
        "blog_back": "Terug naar blog", "min_read": "min lezen", "min": "min",
        "blog_cta_h": "Hulp nodig met jouw website of automatisering?",
        "blog_cta_p": "Vraag een gratis websiteconcept aan of laat ons meedenken over de juiste AI-oplossing.",
        "blog_cta_b1": "Gratis websiteconcept", "blog_cta_b2": "AI-oplossingen",
        "blog_related": "Lees ook", "crumb_blog": "Blog",
        "home": "Home", "crumb_ai": "AI-oplossingen",
        "ai_what": "Wat het je oplevert", "ai_faq": "Veelgestelde vragen",
        "ai_workswith": "Werkt met", "ai_foryou": "Is dit iets voor jou?",
        "ai_install_note": "Liever niet zelf opzetten? Wij komen het bij je bedrijf installeren en uitleggen.",
        "ai_install_btn": "Vraag installatie aan",
        "ai_soon_badge": "Binnenkort beschikbaar", "ai_soon_short": "Binnenkort",
        "ai_soon_note": "Deze oplossing komt binnenkort. Laat je gegevens achter, dan hoor je het als eerste.",
        "ai_keepposted": "Houd mij op de hoogte", "ai_indev": "In ontwikkeling",
        "ai_buy": "Kopen &amp; ontvangen",
        "ai_buy_note": "Eenmalige aanschaf · handleiding per e-mail · betaling volgt via een beveiligd platform",
        "ai_view": "Bekijk", "cases_view": "Bekijk live website",
        "ai_title_suffix": "AI-oplossingen",
        "org_description": "Moderne websites op maat en slimme AI-automatiseringen voor het MKB.",
        "og_image_alt": "Drivenn Agency: moderne websites en slimme AI-automatisering",
    },
    "en": {
        "cat_ai": {"documenten": "Documents &amp; admin", "tekst": "Text &amp; data",
                   "communicatie": "Customer communication"},
        "ai_default_cat": "AI solution",
        "blog_back": "Back to blog", "min_read": "min read", "min": "min",
        "blog_cta_h": "Need help with your website or automation?",
        "blog_cta_p": "Request a free website concept or let us help you find the right AI solution.",
        "blog_cta_b1": "Free concept", "blog_cta_b2": "AI solutions",
        "blog_related": "Keep reading", "crumb_blog": "Blog",
        "home": "Home", "crumb_ai": "AI solutions",
        "ai_what": "What it saves you", "ai_faq": "Frequently asked questions",
        "ai_workswith": "Works with", "ai_foryou": "Is this for you?",
        "ai_install_note": "Rather not set it up yourself? We'll install it at your business and explain everything.",
        "ai_install_btn": "Request installation",
        "ai_soon_badge": "Coming soon", "ai_soon_short": "Soon",
        "ai_soon_note": "This solution is coming soon. Leave your details and you'll be the first to know.",
        "ai_keepposted": "Keep me posted", "ai_indev": "In development",
        "ai_buy": "Buy &amp; receive",
        "ai_buy_note": "One-off purchase · manual by e-mail · payment via a secure platform",
        "ai_view": "View", "cases_view": "View live website",
        "ai_title_suffix": "AI solutions",
        "org_description": "Custom-built modern websites and smart AI automations for small and medium-sized businesses.",
        "og_image_alt": "Drivenn Agency: modern websites and smart AI automation",
    },
    "de": {
        "cat_ai": {"documenten": "Dokumente &amp; Verwaltung", "tekst": "Text &amp; Daten",
                   "communicatie": "Kundenkommunikation"},
        "ai_default_cat": "KI-Lösung",
        "blog_back": "Zurück zum Blog", "min_read": "Min. Lesezeit", "min": "Min.",
        "blog_cta_h": "Hilfe bei deiner Website oder Automatisierung?",
        "blog_cta_p": "Fordere ein kostenloses Website-Konzept an oder lass uns die passende KI-Lösung finden.",
        "blog_cta_b1": "Kostenloses Konzept", "blog_cta_b2": "KI-Lösungen",
        "blog_related": "Weiterlesen", "crumb_blog": "Blog",
        "home": "Home", "crumb_ai": "KI-Lösungen",
        "ai_what": "Was es dir bringt", "ai_faq": "Häufig gestellte Fragen",
        "ai_workswith": "Funktioniert mit", "ai_foryou": "Ist das etwas für dich?",
        "ai_install_note": "Lieber nicht selbst einrichten? Wir installieren es bei dir im Betrieb und erklären alles.",
        "ai_install_btn": "Installation anfragen",
        "ai_soon_badge": "Bald verfügbar", "ai_soon_short": "Bald",
        "ai_soon_note": "Diese Lösung kommt bald. Hinterlasse deine Daten und du erfährst es als Erster.",
        "ai_keepposted": "Halte mich auf dem Laufenden", "ai_indev": "In Entwicklung",
        "ai_buy": "Kaufen &amp; erhalten",
        "ai_buy_note": "Einmaliger Kauf · Anleitung per E-Mail · Zahlung über eine sichere Plattform",
        "ai_view": "Ansehen", "cases_view": "Live-Website ansehen",
        "ai_title_suffix": "KI-Lösungen",
        "org_description": "Moderne Websites nach Maß und smarte KI-Automatisierungen für kleine und mittlere Unternehmen.",
        "og_image_alt": "Drivenn Agency: moderne Websites und smarte KI-Automatisierung",
    },
}

# Korte paginanamen voor de Google Analytics-rapporten (de taalcode komt erachter).
PAGE_NAMES = {
    "nl": {"index.html": "Home", "websites.html": "Websites", "nieuwe-website.html": "Nieuwe website",
           "redesign.html": "Redesign", "hosting.html": "Hosting", "ai-oplossingen.html": "AI-oplossingen",
           "cases.html": "Cases", "blog.html": "Blog", "over-ons.html": "Over ons", "contact.html": "Contact",
           "concept.html": "Gratis websiteconcept", "privacy.html": "Privacyverklaring", "404.html": "404",
           "bedankt.html": "Bedankt"},
    "en": {"index.html": "Home", "websites.html": "Websites", "nieuwe-website.html": "New website",
           "redesign.html": "Redesign", "hosting.html": "Hosting", "ai-oplossingen.html": "AI solutions",
           "cases.html": "Cases", "blog.html": "Blog", "over-ons.html": "About", "contact.html": "Contact",
           "concept.html": "Free website concept", "privacy.html": "Privacy policy", "404.html": "404",
           "bedankt.html": "Thank you"},
    "de": {"index.html": "Home", "websites.html": "Websites", "nieuwe-website.html": "Neue Website",
           "redesign.html": "Redesign", "hosting.html": "Hosting", "ai-oplossingen.html": "KI-Lösungen",
           "cases.html": "Referenzen", "blog.html": "Blog", "over-ons.html": "Über uns", "contact.html": "Kontakt",
           "concept.html": "Kostenloses Website-Konzept", "privacy.html": "Datenschutz", "404.html": "404",
           "bedankt.html": "Danke"},
}

ICON_CAL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>'
ICON_CLOCK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>'
ICON_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>'
ICON_ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
ICON_ARROW_BACK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M19 12H5M11 18l-6-6 6-6"/></svg>'
ICON_APP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>'

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class BuildError(Exception):
    """Content of bronbestand klopt niet; de build stopt met een leesbare melding."""


WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)


# ---------------------------------------------------------------------------
# Bestanden en URL's
# ---------------------------------------------------------------------------
def read(path):
    return pathlib.Path(path).read_text(encoding="utf-8")


def esc(s):
    """Tekst -> veilig in HTML (ook binnen een attribuut)."""
    return html.escape(str(s), quote=True)


def lang_prefix(lang):
    d = LANGS[lang]["dir"]
    return "/" if not d else f"/{d}/"


def lang_dir(lang):
    d = LANGS[lang]["dir"]
    return ROOT if not d else ROOT / d


def page_url(lang, rel):
    """Root-absolute URL van een pagina. De homepage is de map zelf (/, /eng/, /de/)."""
    return lang_prefix(lang) + ("" if rel == "index.html" else rel)


HOME_FILES = {lang_prefix(lg) + "index.html": lang_prefix(lg) for lg in LANGS}
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_asset_versions = {}


def asset_version(url_path):
    """Korte hash van de inhoud van een CSS/JS-bestand, voor ?v= in de URL. Daardoor
    mag de browser het bestand lang bewaren en haalt hij na een wijziging toch
    meteen de nieuwe versie op."""
    if url_path not in _asset_versions:
        f = ROOT / url_path.lstrip("/")
        _asset_versions[url_path] = hashlib.sha1(f.read_bytes()).hexdigest()[:10] if f.is_file() else None
    return _asset_versions[url_path]


def _is_versioned(path):
    return path.startswith(("/assets/css/", "/js/")) and path.endswith((".css", ".js"))


def absolute_url(value, page_dir):
    """Maakt van een interne verwijzing een root-absoluut pad. Externe links,
    ankers, mailto:, tel:, data: e.d. blijven ongemoeid."""
    if not value or value.startswith(("#", "?", "//")) or _SCHEME_RE.match(value):
        return value
    cut = min((i for i in (value.find("?"), value.find("#")) if i != -1), default=len(value))
    path, tail = value[:cut], value[cut:]
    trailing = path.endswith("/")
    path = posixpath.normpath(posixpath.join("/", page_dir, path))
    if trailing and path != "/":
        path += "/"
    path = HOME_FILES.get(path, path)
    if _is_versioned(path):
        version = asset_version(path)
        frag = tail[tail.find("#"):] if "#" in tail else ""
        tail = (f"?v={version}" if version else "") + frag
    return path + tail


_ATTR_URL_RE = re.compile(r'\b(href|src|poster|data-src|action)="([^"]*)"')
_CSS_URL_RE = re.compile(r"url\((\s*['\"]?)([^)'\"]+)")
_SCRIPT_SPLIT_RE = re.compile(r"(<script\b[^>]*>.*?</script>)", re.S | re.I)


def absolutize(text, page_dir):
    """Past absolute_url toe op alle href/src/... en url(...) in de pagina.
    De inhoud van <script>-blokken blijft onaangeroerd (alleen de src van de tag zelf)."""
    def fix_attrs(chunk):
        return _ATTR_URL_RE.sub(lambda m: f'{m.group(1)}="{absolute_url(m.group(2), page_dir)}"', chunk)

    out = []
    for part in _SCRIPT_SPLIT_RE.split(text):
        if part[:7].lower() == "<script":
            end = part.index(">") + 1
            out.append(fix_attrs(part[:end]) + part[end:])
        else:
            part = fix_attrs(part)
            out.append(_CSS_URL_RE.sub(lambda m: f"url({m.group(1)}{absolute_url(m.group(2), page_dir)}", part))
    return "".join(out)


# ---------------------------------------------------------------------------
# Afbeeldingen: breedte/hoogte uitlezen (voorkomt verspringen tijdens het laden)
# ---------------------------------------------------------------------------
_image_sizes = {}
_JPEG_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def image_size(url_path):
    """(breedte, hoogte) van een lokale PNG/JPEG/WebP/GIF, of None."""
    if url_path in _image_sizes:
        return _image_sizes[url_path]
    size = None
    f = ROOT / url_path.split("?")[0].lstrip("/")
    try:
        data = f.read_bytes()
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            size = struct.unpack(">II", data[16:24])
        elif data[:6] in (b"GIF87a", b"GIF89a"):
            size = struct.unpack("<HH", data[6:10])
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            chunk = data[12:16]
            if chunk == b"VP8 ":
                w, h = struct.unpack("<HH", data[26:30])
                size = (w & 0x3FFF, h & 0x3FFF)
            elif chunk == b"VP8L":
                bits = struct.unpack("<I", data[21:25])[0]
                size = ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
            elif chunk == b"VP8X":
                size = (int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1)
        elif data[:2] == b"\xff\xd8":
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in _JPEG_SOF:
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    size = (w, h)
                    break
                if marker in (0xD8, 0x01, 0xFF) or 0xD0 <= marker <= 0xD7:
                    i += 2 if marker != 0xFF else 1
                    continue
                i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    except (OSError, struct.error, IndexError):
        size = None
    _image_sizes[url_path] = tuple(size) if size else None
    return _image_sizes[url_path]


def img_tag(src, alt, cls=None, lazy=True):
    """<img> met alt, afmetingen en (standaard) uitgesteld laden."""
    attrs = [f'src="{esc(src)}"', f'alt="{esc(alt)}"']
    size = image_size(src) if src.startswith("/") else None
    if size:
        attrs += [f'width="{size[0]}"', f'height="{size[1]}"']
    if cls:
        attrs.append(f'class="{cls}"')
    if lazy:
        attrs += ['loading="lazy"', 'decoding="async"']
    return "<img " + " ".join(attrs) + ">"


# ---------------------------------------------------------------------------
# Mini-markdown (voor de tekstvelden uit het CMS)
# ---------------------------------------------------------------------------
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def md_inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)

    def link(m):
        url = html.unescape(m.group(2))
        external = url.startswith(("http://", "https://")) and not url.startswith(SITE)
        extra = ' target="_blank" rel="noopener"' if external else ""
        return f'<a href="{html.escape(url, quote=True)}"{extra}>{m.group(1)}</a>'
    s = _MD_LINK_RE.sub(link, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    # _cursief_ alleen op woordgrenzen, zodat bestands_namen en URL's heel blijven
    s = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"<em>\1</em>", s)
    return s


_MD_UL = re.compile(r"^\s*[-*+]\s+(.*)$")
_MD_OL = re.compile(r"^\s*\d+[.)]\s+(.*)$")


def md(text):
    """Zet de beperkte markdown uit het CMS om naar HTML: koppen, lijsten, citaten,
    vet/cursief en links. Elke niet-lege regel is een eigen alinea."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if heading:
            level = min(max(len(heading.group(1)), 2), 4)   # één h1 per pagina: '#' wordt h2
            out.append(f"<h{level}>{md_inline(heading.group(2).strip())}</h{level}>")
            i += 1
            continue
        list_rx = _MD_UL if _MD_UL.match(ln) else _MD_OL if _MD_OL.match(ln) else None
        if list_rx:
            tag = "ul" if list_rx is _MD_UL else "ol"
            items = []
            while i < len(lines) and list_rx.match(lines[i]):
                items.append(f"<li>{md_inline(list_rx.match(lines[i]).group(1).strip())}</li>")
                i += 1
            out.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue
        if ln.lstrip().startswith(">"):
            quote = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quote.append(md_inline(lines[i].lstrip()[1:].strip()))
                i += 1
            out.append("<blockquote><p>" + " ".join(quote) + "</p></blockquote>")
            continue
        out.append(f"<p>{md_inline(ln.strip())}</p>")
        i += 1
    return "\n".join(out)


def plain(markup):
    """HTML -> platte tekst (voor structured data)."""
    return html.unescape(re.sub(r"<[^>]+>", "", markup)).strip()


def fmt_date(iso, lang):
    try:
        y, m, d = iso.split("-")
        return f"{int(d)} {MONTHS[lang][int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return iso


def page_title(*parts):
    """'Titel | Rubriek | Drivenn Agency', maar zonder de achterste delen als het
    geheel te lang wordt voor de zoekresultaten."""
    parts = [p for p in parts if p]
    while len(parts) > 1 and len(html.unescape(" | ".join(parts))) > TITLE_MAX:
        parts.pop()
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Content inlezen
# ---------------------------------------------------------------------------
def _shared(d, key, default=None):
    """Leest een voor alle talen gelijk veld. Sveltia CMS bewaart zulke velden
    binnen elke taal (single_file-structuur); oudere bestanden hebben ze op het
    hoogste niveau. Beide vormen worden ondersteund."""
    if key in d and not isinstance(d[key], dict):
        return d[key]
    return (d.get(DEFAULT_LANG) or {}).get(key, default)


def _localized(d, lang):
    """NL als basis, aangevuld/overschreven met de vertaling."""
    base = dict(d.get(DEFAULT_LANG) or {})
    tr = d.get(lang)
    if lang != DEFAULT_LANG and isinstance(tr, dict):
        base.update({k: v for k, v in tr.items() if v not in (None, "", [])})
    return base


def _load_json(folder):
    items = []
    for f in sorted((ROOT / "content" / folder).glob("*.json")):
        try:
            data = json.loads(read(f))
        except json.JSONDecodeError as e:
            raise BuildError(f"{f.relative_to(ROOT)} is geen geldige JSON: {e}")
        if not isinstance(data, dict):
            raise BuildError(f"{f.relative_to(ROOT)}: verwacht een JSON-object.")
        slug = _shared(data, "slug") or f.stem
        if not SLUG_RE.match(str(slug)):
            raise BuildError(f"{f.relative_to(ROOT)}: slug '{slug}' mag alleen kleine letters, cijfers en "
                             "streepjes bevatten.")
        items.append((f, slug, data))
    slugs = [s for _, s, _ in items]
    for s in sorted(set(slugs)):
        if slugs.count(s) > 1:
            raise BuildError(f"content/{folder}: de slug '{s}' komt meer dan één keer voor.")
    return items


def load_posts():
    posts = []
    for f, slug, d in _load_json("blog"):
        name = f.relative_to(ROOT)
        date = str(_shared(d, "date", "") or "")[:10]
        if not DATE_RE.match(date):
            raise BuildError(f"{name}: datum '{date}' moet de vorm JJJJ-MM-DD hebben.")
        updated = str(_shared(d, "updated", "") or "")[:10]
        post = {"slug": slug, "date": date,
                "updated": updated if DATE_RE.match(updated) and updated > date else date,
                "image": _shared(d, "image", "") or "",
                "reading": _shared(d, "reading_time_min", 4) or 4, "lang": {}}
        for lang in ACTIVE:
            o = _localized(d, lang)
            title = o.get("titel") or o.get("title") or ""
            if not title:
                raise BuildError(f"{name}: titel ontbreekt.")
            own = d.get(lang) or {}
            if lang != DEFAULT_LANG and not (own.get("tekst") or own.get("text")):
                warn(f"{name}: geen {lang}-vertaling van de tekst; de Nederlandse tekst wordt getoond.")
            post["lang"][lang] = {
                "title": title,
                "summary": o.get("samenvatting") or o.get("summary") or "",
                "body": o.get("tekst") or o.get("text") or "",
                "cat": o.get("category") or o.get("categorie") or _shared(d, "category", "") or "",
            }
        posts.append(post)
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts


def load_solutions():
    sols = []
    for f, slug, d in _load_json("ai"):
        name = f.relative_to(ROOT)
        sol = {"slug": slug, "categorie": _shared(d, "categorie", "") or "",
               "apps": _shared(d, "apps", []) or [], "binnenkort": bool(_shared(d, "binnenkort", False)),
               "prijs": _shared(d, "prijs", "") or "",
               "stripe_link": (_shared(d, "stripe_link", "") or "").strip(), "lang": {}}
        for lang in ACTIVE:
            o = _localized(d, lang)
            if not o.get("titel"):
                raise BuildError(f"{name}: titel ontbreekt.")
            sol["lang"][lang] = {
                "title": o["titel"], "summary": o.get("samenvatting", ""),
                "body": o.get("beschrijving", ""), "voordelen": o.get("voordelen") or [],
                "faq": [q for q in (o.get("faq") or []) if isinstance(q, dict) and q.get("v") and q.get("a")],
                "vereiste": o.get("vereiste", ""), "prijs_note": o.get("prijs_note", ""),
                # de banner kan per taal verschillen (tekst in de afbeelding)
                "banner": (d.get(lang) or {}).get("banner") or _shared(d, "banner", "") or "",
            }
        sols.append(sol)
    sols.sort(key=lambda s: s["binnenkort"])   # stabiel: 'binnenkort' achteraan, rest op bestandsnaam
    return sols


def load_cases():
    cases = []
    for _f, slug, d in _load_json("cases"):
        case = {"slug": slug, "link": _shared(d, "link", "") or "", "image": _shared(d, "image", "") or "",
                "cat": _shared(d, "categorie", "Website") or "Website", "lang": {}}
        for lang in ACTIVE:
            o = _localized(d, lang)
            case["lang"][lang] = {"title": o.get("titel") or o.get("title") or "",
                                  "desc": o.get("beschrijving") or o.get("description") or ""}
        cases.append(case)
    return cases


# ---------------------------------------------------------------------------
# Kaarten (overzichten en teasers)
# ---------------------------------------------------------------------------
def blog_card(post, lang):
    u, o = UI[lang], post["lang"][lang]
    search = esc((o["title"] + " " + o["summary"] + " " + o["cat"]).lower())
    image = img_tag(post["image"], "") if post["image"] else ""
    return f'''<a href="{page_url(lang, "blog/" + post["slug"] + ".html")}" class="card blog-card reveal" data-blog-card data-search="{search}">
  <div class="blog-card__img">{image}</div>
  <div class="card__body">
    <span class="blog-card__cat">{esc(o["cat"])}</span>
    <h3>{esc(o["title"])}</h3>
    <p>{esc(o["summary"])}</p>
    <div class="blog-card__meta"><span>{ICON_CAL} <time datetime="{post["date"]}">{fmt_date(post["date"], lang)}</time></span><span>{ICON_CLOCK} {post["reading"]} {u["min"]}</span></div>
  </div>
</a>'''


def app_chip(name):
    return f'<span class="ai-app">{ICON_APP}{esc(name)}</span>'


def _ai_requirement(sol, lang):
    u, o = UI[lang], sol["lang"][lang]
    if o["vereiste"]:
        return f'<div class="ai-req">{ICON_CHECK}<span><strong>{u["ai_foryou"]}</strong>{esc(o["vereiste"])}</span></div>'
    if sol["binnenkort"]:
        return f'<div class="ai-req ai-req--soon">{ICON_CLOCK}<span><strong>{u["ai_soon_badge"]}</strong>{u["ai_soon_note"]}</span></div>'
    return ""


def ai_card(sol, lang):
    u, o = UI[lang], sol["lang"][lang]
    cat = u["cat_ai"].get(sol["categorie"], u["ai_default_cat"])
    search = esc((o["title"] + " " + o["summary"] + " " + " ".join(sol["apps"]) + " " +
                  plain(cat).replace("&", "en") + " " + sol["categorie"]).lower())
    url = page_url(lang, "ai-oplossingen/" + sol["slug"] + ".html")
    banner = img_tag(o["banner"], "") if o["banner"] else '<span class="ph">DRIVENN · AI</span>'
    soon = f'<span class="ai-card__soon">{u["ai_soon_short"]}</span>' if sol["binnenkort"] else ""
    label = esc(f'{plain(u["ai_view"])}: {o["title"]}')
    if sol["binnenkort"]:
        foot = (f'<div class="ai-card__foot"><span class="ai-price" style="font-size:1rem;color:var(--ink-faint)">{u["ai_indev"]}</span>'
                f'<a href="{url}" class="btn btn--outline" aria-label="{label}">{u["ai_view"]}</a></div>')
    else:
        foot = (f'<div class="ai-card__foot"><div class="ai-price">{esc(sol["prijs"])}<small>{esc(o["prijs_note"])}</small></div>'
                f'<a href="{url}" class="btn btn--navy" aria-label="{label}">{u["ai_view"]}</a></div>')
    return f'''<div class="ai-card reveal" data-ai-card data-cat="{esc(sol["categorie"])}" data-search="{search}">
  <div class="ai-card__banner">{banner}{soon}</div>
  <div class="ai-card__body">
    <span class="ai-card__cat">{cat}</span>
    <h3><a href="{url}">{esc(o["title"])}</a></h3>
    <p>{esc(o["summary"])}</p>
    <div class="ai-apps">{"".join(app_chip(a) for a in sol["apps"])}</div>
    <div class="ai-card__bottom">{_ai_requirement(sol, lang)}{foot}</div>
  </div>
</div>'''


def case_card(case, lang):
    u, o = UI[lang], case["lang"][lang]
    image = img_tag(case["image"], "") if case["image"] else ""
    return f'''<a href="{esc(case["link"] or "#")}" target="_blank" rel="noopener" class="card reveal">
  <div class="blog-card__img">{image}</div>
  <div class="card__body">
    <span class="blog-card__cat">{esc(case["cat"])}</span>
    <h3>{esc(o["title"])}</h3>
    <p>{esc(o["desc"])}</p>
    <span class="btn--ghost" style="margin-top:auto">{u["cases_view"]} {ICON_ARROW}</span>
  </div>
</a>'''


# ---------------------------------------------------------------------------
# Detailpagina's (worden daarna net als elke andere pagina afgewerkt)
# ---------------------------------------------------------------------------
PAGE_SHELL = """<!DOCTYPE html>
<html lang="{code}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
{head_extra}  <!--AUTO:HEAD--><!--/AUTO:HEAD-->
</head>
<body data-page="{data_page}">
<!--#HEADER#--><!--#HEADER-END#-->
<main>
{main}
</main>
<!--#FOOTER#--><!--#FOOTER-END#-->
<script src="/js/main.js"></script>
</body>
</html>
"""


def related_posts(post, posts):
    """Tot drie andere artikelen: eerst dezelfde categorie, daarna de nieuwste."""
    others = [p for p in posts if p["slug"] != post["slug"]]
    cat = post["lang"][DEFAULT_LANG]["cat"]
    others.sort(key=lambda p: p["lang"][DEFAULT_LANG]["cat"] != cat)   # stabiel: datumvolgorde blijft
    return others[:3]


def render_blog_page(post, posts, lang):
    u, o = UI[lang], post["lang"][lang]
    image = post["image"]
    background = f",url('{image}')" if image else ""
    head_extra = ""
    if image:
        head_extra = (f'  <link rel="preload" as="image" href="{esc(image)}" fetchpriority="high">\n'
                      f'  <meta property="og:image" content="{SITE}{esc(image)}">\n')
    related_html = ""
    related = related_posts(post, posts)
    if related:
        cards = "\n".join(blog_card(p, lang) for p in related)
        related_html = f'''
  <section class="section section--alt">
    <div class="container container--wide">
      <div class="sec-head center"><h2>{u["blog_related"]}</h2></div>
      <div class="grid-3">{cards}</div>
    </div>
  </section>'''
    main = f'''  <article>
    <section class="article-hero" style="background-image:linear-gradient(rgba(10,26,48,.82),rgba(14,35,64,.9)){background};background-size:cover;background-position:center">
      <div class="container">
        <a href="{page_url(lang, "blog.html")}" class="article-back">{ICON_ARROW_BACK} {u["blog_back"]}</a>
        <span class="article-hero__cat">{esc(o["cat"])}</span>
        <h1>{esc(o["title"])}</h1>
        <div class="article-hero__meta">
          <span>{ICON_CAL} <time datetime="{post["date"]}">{fmt_date(post["date"], lang)}</time></span>
          <span>{ICON_CLOCK} {post["reading"]} {u["min_read"]}</span>
        </div>
      </div>
    </section>
    <section class="section" style="padding-top:0">
      <div class="article-body">
        {md(o["body"])}
        <div class="article-cta">
          <h3>{u["blog_cta_h"]}</h3>
          <p>{u["blog_cta_p"]}</p>
          <div class="btn-row center" style="margin-top:16px"><a href="{page_url(lang, "concept.html")}" class="btn btn--gold">{u["blog_cta_b1"]}</a><a href="{page_url(lang, "ai-oplossingen.html")}" class="btn btn--outline">{u["blog_cta_b2"]}</a></div>
        </div>
      </div>
    </section>
  </article>{related_html}'''
    return PAGE_SHELL.format(code=LANGS[lang]["code"], title=page_title(esc(o["title"]), BRAND),
                             description=esc(o["summary"]), head_extra=head_extra, data_page="blog", main=main)


def render_ai_page(sol, lang):
    u, o = UI[lang], sol["lang"][lang]
    cat = u["cat_ai"].get(sol["categorie"], u["ai_default_cat"])
    voordelen = "".join(f'<li><span class="fl-ico">{ICON_CHECK}</span><span><b>{md_inline(v)}</b></span></li>'
                        for v in o["voordelen"])
    faq = ""
    if o["faq"]:
        items = "".join(
            f'<div class="faq__item"><button class="faq__q" type="button">{esc(q["v"])}<span class="fq-plus"></span></button>'
            f'<div class="faq__a"><p>{esc(q["a"])}</p></div></div>' for q in o["faq"])
        faq = f'<h2 style="margin-top:2.4rem">{u["ai_faq"]}</h2><div class="faq" style="margin:0">{items}</div>'
    banner_block = img_tag(o["banner"], o["title"], cls="ai-detail__banner", lazy=False) if o["banner"] else ""
    if sol["binnenkort"]:
        price_block = (f'<div style="text-align:center;margin-bottom:16px"><span class="ai-card__soon" '
                       f'style="position:static;display:inline-block">{u["ai_soon_badge"]}</span></div>')
        buy = (f'<a href="{page_url(lang, "ai-oplossingen.html")}#updates" class="btn btn--navy" '
               f'style="width:100%">{u["ai_keepposted"]}</a>')
    else:
        price_block = (f'<div class="ai-price" style="font-size:1.9rem;text-align:center;margin-bottom:4px">'
                       f'{esc(sol["prijs"])}<small style="text-align:center">{esc(o["prijs_note"])}</small></div>')
        buy_href = esc(sol["stripe_link"]) if sol["stripe_link"] else page_url(lang, "contact.html")
        buy = (f'<a href="{buy_href}" class="btn btn--gold" style="width:100%">{u["ai_buy"]}</a>'
               f'<p class="form-note" style="text-align:center">{u["ai_buy_note"]}</p>')
    head_extra = f'  <meta property="og:image" content="{SITE}{esc(o["banner"])}">\n' if o["banner"] else ""
    main = f'''  <section class="page-hero" style="text-align:left">
    <div class="container">
      <p class="page-hero__crumb"><a href="{page_url(lang, "index.html")}">{u["home"]}</a> / <a href="{page_url(lang, "ai-oplossingen.html")}">{u["crumb_ai"]}</a> / {cat}</p>
      <h1 style="max-width:22ch;margin:10px 0 16px">{esc(o["title"])}</h1>
      <p class="lead" style="margin:0">{esc(o["summary"])}</p>
      {banner_block}
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="split" style="align-items:start">
        <div>
          {md(o["body"])}
          <h2 style="margin-top:2rem">{u["ai_what"]}</h2>
          <ul class="feature-list">{voordelen}</ul>
          {faq}
        </div>
        <aside>
          <div class="form-card ai-buy" style="position:sticky;top:100px">
            {price_block}
            {buy}
            <div class="ai-buy__sep"></div>
            <div class="ai-buy__apps"><span class="ai-buy__lbl">{u["ai_workswith"]}</span><div class="ai-apps">{"".join(app_chip(a) for a in sol["apps"])}</div></div>
            {_ai_requirement(sol, lang)}
            <p class="ai-buy__install">{u["ai_install_note"]}</p>
            <a href="{page_url(lang, "contact.html")}" class="btn btn--outline" style="width:100%">{u["ai_install_btn"]}</a>
          </div>
        </aside>
      </div>
    </div>
  </section>'''
    return PAGE_SHELL.format(code=LANGS[lang]["code"],
                             title=page_title(esc(o["title"]), u["ai_title_suffix"], BRAND),
                             description=esc(o["summary"]), head_extra=head_extra, data_page="ai", main=main)


# ---------------------------------------------------------------------------
# Structured data (schema.org, volgens de richtlijnen van Google Search)
# ---------------------------------------------------------------------------
def schema_organization(lang):
    logo = image_size(LOGO_SQUARE) or (None, None)
    return {
        "@type": "ProfessionalService", "@id": ORG_ID, "name": BRAND,
        "description": UI[lang]["org_description"], "url": SITE + "/",
        "logo": {"@type": "ImageObject", "url": SITE + LOGO_SQUARE, "width": logo[0], "height": logo[1]},
        "image": SITE + DEFAULT_OG_IMAGE,
        "email": ORG["email"], "telephone": ORG["telephone"],
        "address": {"@type": "PostalAddress", "addressRegion": ORG["region"], "addressCountry": ORG["country"]},
        "areaServed": {"@type": "Country", "name": "NL"},
        "iso6523Code": "0106:" + ORG["kvk"],   # 0106 = register van de Kamer van Koophandel
        "contactPoint": {"@type": "ContactPoint", "contactType": "customer service",
                         "telephone": ORG["telephone"], "email": ORG["email"],
                         "availableLanguage": [LANGS[lg]["code"] for lg in ACTIVE]},
        "sameAs": SOCIAL_PROFILES,
    }


def schema_website():
    return {"@type": "WebSite", "@id": WEBSITE_ID, "name": BRAND, "url": SITE + "/",
            "inLanguage": [LANGS[lg]["code"] for lg in ACTIVE], "publisher": {"@id": ORG_ID}}


_FAQ_ITEM_RE = re.compile(
    r'class="faq__q"[^>]*>(.*?)<span class="fq-plus"></span></button>\s*<div class="faq__a"[^>]*>(.*?)</div>', re.S)
_FAQ_MD_RE = re.compile(r"<p><strong>(.*?)</strong></p>\s*<p>(.*?)</p>", re.S)


def schema_faq(body, lang):
    """FAQ-structured data, uitsluitend uit vragen die zichtbaar op de pagina staan
    (accordeon op dienst-/AI-pagina's, of een 'Veelgestelde vragen'-kop in een blog)."""
    pairs = _FAQ_ITEM_RE.findall(body)
    if not pairs:
        m = re.search(rf'<h2>{re.escape(UI[lang]["ai_faq"])}</h2>(.*?)(?=<h2>|<div class="article-cta">|$)',
                      body, re.S)
        pairs = _FAQ_MD_RE.findall(m.group(1)) if m else []
    items = [{"@type": "Question", "name": plain(q), "acceptedAnswer": {"@type": "Answer", "text": plain(a)}}
             for q, a in pairs if plain(q) and plain(a)]
    return {"@type": "FAQPage", "mainEntity": items} if items else None


def schema_breadcrumb(trail):
    """trail: [(naam, url-of-None), ...]; het laatste item is de huidige pagina."""
    if len(trail) < 2:
        return None
    items = []
    for pos, (name, url) in enumerate(trail, 1):
        item = {"@type": "ListItem", "position": pos, "name": name}
        if url:
            item["item"] = SITE + url
        items.append(item)
    return {"@type": "BreadcrumbList", "itemListElement": items}


def breadcrumb_from_page(body):
    """Leest het zichtbare kruimelpad (<p class="page-hero__crumb">) van de pagina."""
    m = re.search(r'<p class="page-hero__crumb">(.*?)</p>', body, re.S)
    if not m:
        return None
    inner = m.group(1)
    trail = [(plain(label), href) for href, label in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', inner)]
    tail = plain(inner.rsplit("</a>", 1)[-1]).lstrip("/ ").strip()
    if tail:
        trail.append((tail, None))
    return schema_breadcrumb(trail)


def schema_blog_posting(post, lang, canon):
    o = post["lang"][lang]
    data = {
        "@type": "BlogPosting", "mainEntityOfPage": {"@type": "WebPage", "@id": canon},
        "headline": o["title"][:110], "description": o["summary"],
        "datePublished": post["date"], "dateModified": post["updated"],
        "inLanguage": LANGS[lang]["code"],
        "author": {"@type": "Organization", "@id": ORG_ID, "name": BRAND, "url": SITE + "/"},
        "publisher": {"@type": "Organization", "@id": ORG_ID, "name": BRAND,
                      "logo": {"@type": "ImageObject", "url": SITE + LOGO_SQUARE}},
    }
    if o["cat"]:
        data["articleSection"] = o["cat"]
    if post["image"]:
        data["image"] = [SITE + post["image"]]
    return data


def price_number(prijs):
    """'€ 1.299,50' -> '1299.50'; geen bedrag -> None."""
    m = re.search(r"\d[\d.,]*", prijs or "")
    if not m:
        return None
    raw = m.group(0).rstrip(".,")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
        raw = raw.replace(".", "")
    return raw


def schema_product(sol, lang, canon):
    price = None if sol["binnenkort"] else price_number(sol["prijs"])
    if not price:
        return None
    o = sol["lang"][lang]
    return {
        "@type": "Product", "name": o["title"], "description": o["summary"],
        "image": [SITE + (o["banner"] or DEFAULT_OG_IMAGE)],
        "brand": {"@type": "Brand", "name": BRAND},
        "category": plain(UI[lang]["cat_ai"].get(sol["categorie"], UI[lang]["ai_default_cat"])),
        "offers": {"@type": "Offer", "price": price, "priceCurrency": "EUR",
                   "availability": "https://schema.org/InStock", "url": canon,
                   "seller": {"@id": ORG_ID}},
    }


def schema_service(title, description, canon):
    return {"@type": "Service", "name": title, "description": description, "url": canon,
            "provider": {"@id": ORG_ID}, "areaServed": {"@type": "Country", "name": "NL"}}


def jsonld_tag(data):
    payload = {"@context": "https://schema.org", **data}
    return ('<script type="application/ld+json">'
            + json.dumps(payload, ensure_ascii=False).replace("</", "<\\/") + "</script>")


# ---------------------------------------------------------------------------
# De <head> (beheerd blok)
# ---------------------------------------------------------------------------
AUTO_OPEN, AUTO_CLOSE = "<!--AUTO:HEAD-->", "<!--/AUTO:HEAD-->"
_AUTO_RE = re.compile(re.escape(AUTO_OPEN) + ".*?" + re.escape(AUTO_CLOSE), re.S)
_PLACEHOLDER = "\x00AUTOHEAD\x00"
_STYLESHEET_RE = re.compile(r'<link\b[^>]*\bhref="[^"]*assets/css/style\.css[^"]*"[^>]*>')
# Tags die het script zelf in het beheerde blok zet; handgeschreven exemplaren verdwijnen.
_MANAGED_TAG_RES = [re.compile(p, re.I) for p in (
    r'<link\b[^>]*\brel="(?:icon|shortcut icon|apple-touch-icon|canonical|manifest)"[^>]*>',
    r'<link\b[^>]*\brel="alternate"[^>]*\bhreflang="[^"]*"[^>]*>',
    r'<link\b[^>]*\brel="preload"[^>]*\bas="font"[^>]*>',
    r'<meta\b[^>]*\bproperty="og:(?:url|locale|locale:alternate|type|site_name|image:width|image:height|image:alt)"[^>]*>',
    r'<meta\b[^>]*\bproperty="article:[^"]*"[^>]*>',
    r'<meta\b[^>]*\bname="twitter:[^"]*"[^>]*>',
    r'<meta\b[^>]*\bname="theme-color"[^>]*>',
)]
_LEGACY_BLOCK_RES = [re.compile(rf"[ \t]*<!--{n}-->.*?<!--/{n}-->\n?", re.S)
                     for n in ("HEADLINKS", "SEOSCHEMA", "ANALYTICS")]
_JSONLD_RE = re.compile(r'[ \t]*<script type="application/ld\+json">.*?</script>\n?', re.S)


def _meta(head, attr, name):
    m = re.search(rf'<meta\s+{attr}="{re.escape(name)}"\s+content="([^"]*)"\s*/?>', head)
    return m.group(1) if m else None


def _drop_meta(head, attr, name):
    return re.sub(rf'[ \t]*<meta\s+{attr}="{re.escape(name)}"\s+content="[^"]*"\s*/?>\n?', "", head)


def build_head(head, page, body):
    """Geeft de volledige nieuwe inhoud van <head> terug."""
    lang, rel, kind = page["lang"], page["rel"], page["kind"]
    where = page["path"].relative_to(ROOT)

    for rx in _LEGACY_BLOCK_RES:
        head = rx.sub("", head)
    if _AUTO_RE.search(head):
        head = _AUTO_RE.sub(_PLACEHOLDER, head, count=1)
    elif _STYLESHEET_RE.search(head):
        # eerste keer: het blok komt op de plek van de stylesheet (de volgorde t.o.v.
        # een eventuele <style> op de pagina blijft daardoor gelijk)
        head = _STYLESHEET_RE.sub(_PLACEHOLDER, head, count=1)
    else:
        head = head.rstrip() + "\n  " + _PLACEHOLDER + "\n"
    head = _STYLESHEET_RE.sub("", head)
    for rx in _MANAGED_TAG_RES:
        head = rx.sub("", head)
    if kind in ("home", "blog", "ai"):
        head = _JSONLD_RE.sub("", head)   # wordt hieronder opnieuw opgebouwd uit de content

    title_m = re.search(r"<title>(.*?)</title>", head, re.S)
    if not title_m or not title_m.group(1).strip():
        raise BuildError(f"{where}: <title> ontbreekt.")
    title = title_m.group(1).strip()
    description = _meta(head, "name", "description")
    if not description and kind != "404":
        warn(f'{where}: <meta name="description"> ontbreekt.')
    noindex = "noindex" in (_meta(head, "name", "robots") or "")

    canon = SITE + page["url"]
    default_image = SITE + DEFAULT_OG_IMAGE
    # og:title/description/image mogen per pagina afwijken; gelijk aan de standaard = opruimen.
    og = {}
    for key, defaults in (("og:title", (title,)), ("og:description", (description or "",)),
                          ("og:image", (default_image, SITE + LOGO_SQUARE))):
        authored = _meta(head, "property", key)
        if authored is not None and (not authored or authored in defaults):
            head = _drop_meta(head, "property", key)
            authored = None
        og[key] = authored
    if kind == "404":
        for key in og:
            head = _drop_meta(head, "property", key)

    lines = [f'<link rel="preload" href="{font}" as="font" type="font/woff2" crossorigin>' for font in PRELOAD_FONTS]
    lines += [
        f'<link rel="stylesheet" href="{absolute_url("/assets/css/style.css", "")}">',
        '<link rel="icon" href="/assets/images/favicon.ico" sizes="any">',
        '<link rel="icon" type="image/png" sizes="32x32" href="/assets/images/favicon-32x32.png">',
        '<link rel="icon" type="image/png" sizes="192x192" href="/assets/images/icon-192.png">',
        '<link rel="apple-touch-icon" sizes="180x180" href="/assets/images/apple-touch-icon.png">',
        '<link rel="manifest" href="/site.webmanifest">',
        f'<meta name="theme-color" content="{THEME_COLOR}">',
    ]
    if kind == "404":
        # De 404-pagina wordt op elke onbekende URL getoond: geen canonical/hreflang.
        # Bezoekers van /de/... en /eng/... gaan door naar de 404 in hun eigen taal.
        if lang == DEFAULT_LANG:
            dirs = "|".join(LANGS[lg]["dir"] for lg in ACTIVE if LANGS[lg]["dir"])
            if dirs:
                lines.append('<script>(function(){var m=location.pathname.match(/^\\/(' + dirs + ')\\//);'
                             'if(m&&location.pathname!=="/"+m[1]+"/404.html")'
                             'location.replace("/"+m[1]+"/404.html");})();</script>')
    else:
        if not noindex:
            lines.append('<meta name="robots" content="index, follow, max-image-preview:large, '
                         'max-snippet:-1, max-video-preview:-1">')
        lines.append(f'<link rel="canonical" href="{canon}">')
        alternates = page["alternates"]
        if len(alternates) > 1:
            lines += [f'<link rel="alternate" hreflang="{LANGS[lg]["code"]}" href="{SITE}{alternates[lg]}">'
                      for lg in ACTIVE if lg in alternates]
            if DEFAULT_LANG in alternates:
                lines.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}{alternates[DEFAULT_LANG]}">')

        og_title = og["og:title"] or title
        og_desc = og["og:description"] or description or ""
        og_image = og["og:image"] or default_image
        lines += [f'<meta property="og:type" content="{"article" if kind == "blog" else "website"}">',
                  f'<meta property="og:site_name" content="{BRAND}">',
                  f'<meta property="og:locale" content="{LANGS[lang]["locale"]}">']
        lines += [f'<meta property="og:locale:alternate" content="{LANGS[lg]["locale"]}">'
                  for lg in ACTIVE if lg != lang and lg in alternates]
        lines.append(f'<meta property="og:url" content="{canon}">')
        if og["og:title"] is None:
            lines.append(f'<meta property="og:title" content="{title}">')
        if og["og:description"] is None and og_desc:
            lines.append(f'<meta property="og:description" content="{og_desc}">')
        if og["og:image"] is None:
            lines.append(f'<meta property="og:image" content="{default_image}">')
        size = image_size(og_image[len(SITE):]) if og_image.startswith(SITE + "/") else None
        if size:
            lines += [f'<meta property="og:image:width" content="{size[0]}">',
                      f'<meta property="og:image:height" content="{size[1]}">']
        elif og_image.startswith(SITE + "/"):
            warn(f"{where}: og:image {og_image} bestaat niet of is geen leesbare afbeelding.")
        image_alt = esc(UI[lang]["og_image_alt"]) if og_image == default_image else title.split(" | ")[0]
        lines.append(f'<meta property="og:image:alt" content="{image_alt}">')
        if kind == "blog":
            post = page["post"]
            lines += [f'<meta property="article:published_time" content="{post["date"]}">',
                      f'<meta property="article:modified_time" content="{post["updated"]}">']
            if post["lang"][lang]["cat"]:
                lines.append(f'<meta property="article:section" content="{esc(post["lang"][lang]["cat"])}">')
        lines += ['<meta name="twitter:card" content="summary_large_image">',
                  f'<meta name="twitter:title" content="{og_title}">',
                  f'<meta name="twitter:description" content="{og_desc}">',
                  f'<meta name="twitter:image" content="{og_image}">']

        schemas = []
        if kind == "home":
            schemas += [schema_organization(lang), schema_website()]
        if kind == "blog":
            post = page["post"]
            schemas.append(schema_blog_posting(post, lang, canon))
            schemas.append(schema_breadcrumb([(UI[lang]["home"], page_url(lang, "index.html")),
                                              (UI[lang]["crumb_blog"], page_url(lang, "blog.html")),
                                              (post["lang"][lang]["title"], None)]))
        else:
            schemas.append(breadcrumb_from_page(body))
        if kind == "ai":
            schemas.append(schema_product(page["solution"], lang, canon))
        if kind == "static" and rel in SERVICE_PAGES:
            schemas.append(schema_service(html.unescape(title.split(" | ")[0]),
                                          html.unescape(description or ""), canon))
        schemas.append(schema_faq(body, lang))
        lines += [jsonld_tag(s) for s in schemas if s]

    # analytics: laadt pas na toestemming, zie js/consent.js
    name = PAGE_NAMES[lang].get(rel) if kind in ("static", "home", "404") else None
    if not name:
        name = html.unescape(title).split(" | ")[0].strip()
    config = {"id": GA_ID, "page": f"{name} – {LANGS[lang]['code'].upper()}", "lang": lang}
    lines.append("<script>window.DRIVENN_GA=" + json.dumps(config, ensure_ascii=False).replace("</", "<\\/")
                 + ";</script>")
    lines.append(f'<script src="{absolute_url("/js/consent.js", "")}" defer></script>')

    block = AUTO_OPEN + "\n" + "\n".join("  " + ln for ln in lines) + "\n  " + AUTO_CLOSE
    head = re.sub(r"[ \t]+\n", "\n", head)                  # resten van verwijderde tags
    head = re.sub(r"\n{2,}", "\n", head)
    return head.replace(_PLACEHOLDER, block)


# ---------------------------------------------------------------------------
# Een pagina afwerken
# ---------------------------------------------------------------------------
_components = {}


def component(name, lang):
    key = (name, lang)
    if key not in _components:
        f = ROOT / "components" / f"{name}{LANGS[lang]['sfx']}.html"
        if not f.is_file():
            raise BuildError(f"Component ontbreekt: {f.relative_to(ROOT)}")
        _components[key] = read(f).strip()
    return _components[key]


def fill_marker(text, name, content):
    """Vervangt alles tussen <!--#NAAM#--> en <!--#NAAM-END#-->."""
    rx = re.compile(r"<!--#" + name + r"#-->.*?<!--#" + name + r"-END#-->", re.S)
    return rx.sub(lambda m: f"<!--#{name}#-->{content}<!--#{name}-END#-->", text)


_LANG_LINK_RE = re.compile(r'(<a\s+href=")[^"]*("\s+data-lang="([a-z]+)")')


def localize_header(header, page):
    """De taalwisselaar wijst naar dezelfde pagina in de andere taal en het actieve
    menu-item wordt hier al gemarkeerd (werkt dus ook zonder JavaScript)."""
    def lang_link(m):
        target = page["alternates"].get(m.group(3)) or page_url(m.group(3), "index.html")
        return m.group(1) + target + m.group(2)
    header = _LANG_LINK_RE.sub(lang_link, header)
    if page["data_page"]:
        header = re.sub(r'(<a\s+href="[^"]*"\s+data-page="' + re.escape(page["data_page"]) + r'")>',
                        r'\1 class="active" aria-current="page">', header)
    return header


def finalize(text, page, site):
    """Zet componenten, kaarten en de <head> in één pagina. `site` bevat de content."""
    lang = page["lang"]
    m = re.search(r'<body[^>]*\bdata-page="([^"]*)"', text)
    page["data_page"] = m.group(1) if m else ""

    text = fill_marker(text, "HEADER", localize_header(component("header", lang), page))
    text = fill_marker(text, "FOOTER", component("footer", lang))
    if page["kind"] in ("static", "home"):
        blocks = {
            "BLOG_CARDS": lambda: "\n".join(blog_card(p, lang) for p in site["posts"]),
            "BLOG_TEASER": lambda: "\n".join(blog_card(p, lang) for p in site["posts"][:3]),
            "AI_CARDS": lambda: "\n".join(ai_card(s, lang) for s in site["solutions"]),
            "CASES_CARDS": lambda: "\n".join(case_card(c, lang) for c in site["cases"]),
            "CASES_TEASER": lambda: "\n".join(case_card(c, lang) for c in site["cases"]),
        }
        for name, render in blocks.items():
            if f"<!--#{name}#-->" in text:
                text = fill_marker(text, name, render())

    # <main id="main"> is het doel van de 'direct naar inhoud'-link in de header
    text = re.sub(r"<main(?![^>]*\bid=)([^>]*)>", r'<main id="main"\1>', text, count=1)
    # pagina's met een formulier hebben js/form.js nodig
    if "data-form" in text and "js/form.js" not in text:
        text = text.replace("</body>", '<script src="/js/form.js"></script>\n</body>', 1)

    text = absolutize(text, posixpath.dirname(page["url_file"]).lstrip("/"))

    m = re.search(r"<head[^>]*>(.*?)</head>", text, re.S)
    if not m:
        raise BuildError(f"{page['path'].relative_to(ROOT)}: <head> ontbreekt.")
    new_head = build_head(m.group(1), page, text[m.end():])
    return text[:m.start(1)] + new_head + text[m.end(1):]


# ---------------------------------------------------------------------------
# Sitemap
# ---------------------------------------------------------------------------
def build_sitemap(pages):
    """Alleen indexeerbare, canonieke URL's, met de taalvarianten erbij."""
    rows = []
    for page in pages:
        if page["kind"] == "404" or page["noindex"]:
            continue
        alternates = page["alternates"]
        links = ""
        if len(alternates) > 1:
            links = "".join(f'<xhtml:link rel="alternate" hreflang="{LANGS[lg]["code"]}" href="{SITE}{alternates[lg]}"/>'
                            for lg in ACTIVE if lg in alternates)
            if DEFAULT_LANG in alternates:
                links += f'<xhtml:link rel="alternate" hreflang="x-default" href="{SITE}{alternates[DEFAULT_LANG]}"/>'
        lastmod = f'<lastmod>{page["post"]["updated"]}</lastmod>' if page["kind"] == "blog" else ""
        rows.append(f'  <url><loc>{SITE}{page["url"]}</loc>{lastmod}{links}</url>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(rows) + "\n</urlset>\n")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def collect_pages(site):
    """Alle pagina's van de site, elk met zijn brontekst en taalvarianten."""
    pages = []

    def add(lang, rel, kind, source, **extra):
        pages.append({"lang": lang, "rel": rel, "kind": kind, "path": lang_dir(lang) / rel,
                      "url": page_url(lang, rel), "url_file": lang_prefix(lang) + rel,
                      "source": source, **extra})

    static = {lang: sorted(p.name for p in lang_dir(lang).glob("*.html")) for lang in ACTIVE}
    order = {name: i for i, name in enumerate(SITEMAP_ORDER)}
    for rel in sorted(set().union(*static.values()), key=lambda r: (order.get(r, len(order)), r)):
        for lang in ACTIVE:
            if rel in static[lang]:
                kind = "home" if rel == "index.html" else "404" if rel == "404.html" else "static"
                add(lang, rel, kind, read(lang_dir(lang) / rel))
    for sol in site["solutions"]:
        for lang in ACTIVE:
            add(lang, f"ai-oplossingen/{sol['slug']}.html", "ai", render_ai_page(sol, lang), solution=sol)
    for post in site["posts"]:
        for lang in ACTIVE:
            add(lang, f"blog/{post['slug']}.html", "blog", render_blog_page(post, site["posts"], lang), post=post)

    existing = {(p["lang"], p["rel"]) for p in pages}
    for page in pages:
        page["alternates"] = {lg: page_url(lg, page["rel"]) for lg in ACTIVE if (lg, page["rel"]) in existing}
        page["noindex"] = bool(re.search(r'<meta\s+name="robots"\s+content="[^"]*noindex', page["source"]))
    return pages


def build():
    """Geeft (site, {pad: nieuwe inhoud}, [vervallen bestanden]) terug zonder iets te schrijven."""
    site = {"posts": load_posts(), "solutions": load_solutions(), "cases": load_cases()}
    pages = collect_pages(site)
    outputs = {page["path"]: finalize(page["source"], page, site) for page in pages}
    outputs[ROOT / "sitemap.xml"] = build_sitemap(pages)

    # Detailpagina's waarvan de bron (JSON) is verwijderd, moeten ook van de site af.
    stale = []
    for lang in ACTIVE:
        for sub in ("blog", "ai-oplossingen"):
            folder = lang_dir(lang) / sub
            if folder.is_dir():
                stale += [p for p in sorted(folder.glob("*.html")) if p not in outputs]
    return site, outputs, stale


def main(argv):
    check_only = "--check" in argv
    try:
        site, outputs, stale = build()
    except BuildError as e:
        print(f"FOUT: {e}", file=sys.stderr)
        return 1

    changed = [p for p, text in outputs.items() if not p.is_file() or read(p) != text]
    for w in WARNINGS:
        print(f"Let op: {w}", file=sys.stderr)
    if check_only:
        for p in changed:
            print(f"niet up-to-date: {p.relative_to(ROOT)}")
        for p in stale:
            print(f"hoort te vervallen: {p.relative_to(ROOT)}")
        if changed or stale:
            print("Draai: python3 scripts/build_content.py", file=sys.stderr)
            return 1
        print("Alles is up-to-date.")
        return 0

    for p in changed:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(outputs[p], encoding="utf-8")
    for p in stale:
        p.unlink()
    print(f"Gegenereerd voor talen: {', '.join(ACTIVE)} — {len(site['posts'])} blogs, "
          f"{len(site['solutions'])} AI, {len(site['cases'])} cases per taal. "
          f"{len(changed)} bestand(en) bijgewerkt, {len(stale)} verwijderd.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
