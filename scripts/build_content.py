#!/usr/bin/env python3
"""
Genereert de statische Drivenn Agency-site in meerdere talen.

- injecteert components/header{.lang}.html + footer{.lang}.html in alle pagina's
- genereert blog-, AI- en case-content uit content/**/*.json (per taal)
- schrijft NL in de root, EN in /eng/, DE in /de/
- bouwt sitemap.xml met hreflang-alternates
- maakt alle paden diepte-correct relatief (werkt op subpad én domein-root)

Draai lokaal: python3 scripts/build_content.py
"""
import json, pathlib, re, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://www.drivennagency.nl"

# Welke talen nu live gebouwd worden. Zet op ["nl","en"] / ["nl","en","de"]
# zodra de betreffende pagina's compleet zijn (voorkomt 404's op halve talenbomen).
ACTIVE = ["nl", "en"]

MONTHS = {
    "nl": ["januari","februari","maart","april","mei","juni","juli","augustus","september","oktober","november","december"],
    "en": ["January","February","March","April","May","June","July","August","September","October","November","December"],
    "de": ["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"],
}

# UI-strings + categorie-labels per taal
UI = {
  "nl": {
    "sfx":"", "dir":"", "code":"nl",
    "cat_ai":{"documenten":"Documenten &amp; administratie","tekst":"Tekst &amp; data","communicatie":"Klantcommunicatie"},
    "ai_default_cat":"AI-oplossing",
    "blog_back":"Terug naar blog", "min_read":"min lezen", "min":"min",
    "blog_cta_h":"Hulp nodig met jouw website of automatisering?",
    "blog_cta_p":"Vraag een gratis websiteconcept aan of laat ons meedenken over de juiste AI-oplossing.",
    "blog_cta_b1":"Gratis websiteconcept", "blog_cta_b2":"AI-oplossingen",
    "home":"Home", "crumb_ai":"AI-oplossingen",
    "ai_what":"Wat het je oplevert", "ai_faq":"Veelgestelde vragen",
    "ai_workswith":"Werkt met", "ai_foryou":"Is dit iets voor jou?",
    "ai_install_note":"Liever niet zelf opzetten? Wij komen het bij je bedrijf installeren en uitleggen.",
    "ai_install_btn":"Vraag installatie aan",
    "ai_soon_badge":"Binnenkort beschikbaar", "ai_soon_short":"Binnenkort",
    "ai_soon_note":"Deze oplossing komt binnenkort. Laat je gegevens achter, dan hoor je het als eerste.",
    "ai_keepposted":"Houd mij op de hoogte", "ai_indev":"In ontwikkeling",
    "ai_buy":"Kopen &amp; ontvangen",
    "ai_buy_note":"Eenmalige aanschaf · handleiding per e-mail · betaling volgt via een beveiligd platform",
    "ai_view":"Bekijk", "cases_view":"Bekijk live website",
    "ai_title_suffix":"AI-oplossingen | Drivenn Agency",
  },
  "en": {
    "sfx":".en", "dir":"eng", "code":"en",
    "cat_ai":{"documenten":"Documents &amp; admin","tekst":"Text &amp; data","communicatie":"Customer communication"},
    "ai_default_cat":"AI solution",
    "blog_back":"Back to blog", "min_read":"min read", "min":"min",
    "blog_cta_h":"Need help with your website or automation?",
    "blog_cta_p":"Request a free website concept or let us help you find the right AI solution.",
    "blog_cta_b1":"Free concept", "blog_cta_b2":"AI solutions",
    "home":"Home", "crumb_ai":"AI solutions",
    "ai_what":"What it saves you", "ai_faq":"Frequently asked questions",
    "ai_workswith":"Works with", "ai_foryou":"Is this for you?",
    "ai_install_note":"Rather not set it up yourself? We'll install it at your business and explain everything.",
    "ai_install_btn":"Request installation",
    "ai_soon_badge":"Coming soon", "ai_soon_short":"Soon",
    "ai_soon_note":"This solution is coming soon. Leave your details and you'll be the first to know.",
    "ai_keepposted":"Keep me posted", "ai_indev":"In development",
    "ai_buy":"Buy &amp; receive",
    "ai_buy_note":"One-off purchase · manual by e-mail · payment via a secure platform",
    "ai_view":"View", "cases_view":"View live website",
    "ai_title_suffix":"AI solutions | Drivenn Agency",
  },
  "de": {
    "sfx":".de", "dir":"de", "code":"de",
    "cat_ai":{"documenten":"Dokumente &amp; Verwaltung","tekst":"Text &amp; Daten","communicatie":"Kundenkommunikation"},
    "ai_default_cat":"KI-Lösung",
    "blog_back":"Zurück zum Blog", "min_read":"Min. Lesezeit", "min":"Min.",
    "blog_cta_h":"Hilfe bei deiner Website oder Automatisierung?",
    "blog_cta_p":"Fordere ein kostenloses Website-Konzept an oder lass uns die passende KI-Lösung finden.",
    "blog_cta_b1":"Kostenloses Konzept", "blog_cta_b2":"KI-Lösungen",
    "home":"Home", "crumb_ai":"KI-Lösungen",
    "ai_what":"Was es dir bringt", "ai_faq":"Häufig gestellte Fragen",
    "ai_workswith":"Funktioniert mit", "ai_foryou":"Ist das etwas für dich?",
    "ai_install_note":"Lieber nicht selbst einrichten? Wir installieren es bei dir im Betrieb und erklären alles.",
    "ai_install_btn":"Installation anfragen",
    "ai_soon_badge":"Bald verfügbar", "ai_soon_short":"Bald",
    "ai_soon_note":"Diese Lösung kommt bald. Hinterlasse deine Daten und du erfährst es als Erster.",
    "ai_keepposted":"Halte mich auf dem Laufenden", "ai_indev":"In Entwicklung",
    "ai_buy":"Kaufen &amp; erhalten",
    "ai_buy_note":"Einmaliger Kauf · Anleitung per E-Mail · Zahlung über eine sichere Plattform",
    "ai_view":"Ansehen", "cases_view":"Live-Website ansehen",
    "ai_title_suffix":"KI-Lösungen | Drivenn Agency",
  },
}

def read(p): return pathlib.Path(p).read_text(encoding="utf-8")
def write(p, s):
    pathlib.Path(p).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(p).write_text(s, encoding="utf-8")

def lp(lang):
    """Link-prefix voor interne pagina-links: '/' voor NL, '/eng/' voor EN, '/de/' voor DE."""
    d = UI[lang]["dir"]
    return "/" if not d else f"/{d}/"

def outdir(lang):
    d = UI[lang]["dir"]
    return ROOT if not d else (ROOT/d)

def fmt_date(iso, lang):
    try:
        y,m,d = iso.split("-"); return f"{int(d)} {MONTHS[lang][int(m)-1]} {y}"
    except Exception:
        return iso

def inject_marker(t, name, content):
    return re.sub(r'<!--#'+name+r'#-->.*?<!--#'+name+r'-END#-->',
                  lambda m: '<!--#'+name+'#-->'+content+'<!--#'+name+'-END#-->', t, flags=re.S)

def hreflang_block(path_by_lang):
    """path_by_lang: {lang: absolute-path-without-host}. Bouwt canonical (huidige) + alternates."""
    out = []
    for lg in ACTIVE:
        out.append(f'  <link rel="alternate" hreflang="{UI[lg]["code"]}" href="{SITE}{path_by_lang[lg]}">')
    out.append(f'  <link rel="alternate" hreflang="x-default" href="{SITE}{path_by_lang["nl"]}">')
    return "\n".join(out)

# ---------------------------------------------------------------------------
# markdown-mini
# ---------------------------------------------------------------------------
def md(text):
    lines = text.split("\n"); out, i = [], 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip(): i += 1; continue
        if ln.startswith("### "): out.append(f"<h3>{inline(ln[4:])}</h3>")
        elif ln.startswith("## "): out.append(f"<h2>{inline(ln[3:])}</h2>")
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(f"<li>{inline(lines[i].strip()[2:])}</li>"); i += 1
            out.append("<ul>"+"".join(items)+"</ul>"); continue
        else: out.append(f"<p>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)

def inline(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"_(.+?)_", r"<em>\1</em>", s)
    return s

# ---------------------------------------------------------------------------
# iconen
# ---------------------------------------------------------------------------
ICON_CAL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>'
ICON_CLOCK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>'
ICON_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>'
ICON_ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
APP_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>'
ICON_CHECK_SMALL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>'
INSTALL_ICO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 2 7l10 5 10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/></svg>'
ARROW_BACK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M19 12H5M11 18l-6-6 6-6"/></svg>'

# ---------------------------------------------------------------------------
# component-injectie (taal-bewust)
# ---------------------------------------------------------------------------
def inject_components(lang):
    sfx = UI[lang]["sfx"]
    header = read(ROOT/f"components/header{sfx}.html").strip()
    footer = read(ROOT/f"components/footer{sfx}.html").strip()
    base = outdir(lang)
    pages = list(base.glob("*.html"))
    for sub in ("blog", "ai-oplossingen"):
        if (base/sub).exists(): pages += list((base/sub).glob("*.html"))
    for p in pages:
        t = read(p)
        t = re.sub(r'<!--#HEADER#-->.*?<!--#HEADER-END#-->',
                   lambda m: '<!--#HEADER#-->'+header+'<!--#HEADER-END#-->', t, flags=re.S)
        t = re.sub(r'<!--#FOOTER#-->.*?<!--#FOOTER-END#-->',
                   lambda m: '<!--#FOOTER#-->'+footer+'<!--#FOOTER-END#-->', t, flags=re.S)
        write(p, t)

# ---------------------------------------------------------------------------
# blog
# ---------------------------------------------------------------------------
BLOG_PAGE = """<!DOCTYPE html>
<html lang="{code}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Drivenn Agency</title>
  <meta name="description" content="{summary}">
  <link rel="stylesheet" href="/assets/css/style.css">
  <link rel="canonical" href="{canon}">
{hreflang}
  <link rel="icon" type="image/x-icon" href="/assets/images/favicon.ico">
  <link rel="icon" type="image/png" sizes="32x32" href="/assets/images/favicon-32x32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/assets/images/apple-touch-icon.png">
  <meta property="og:title" content="{title} | Drivenn Agency">
  <meta property="og:description" content="{summary}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canon}">
  <meta property="og:image" content="{ogimg}">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BlogPosting","headline":"{title}","description":"{summary}","image":"{ogimg}","author":{{"@type":"Organization","name":"Drivenn Agency"}},"publisher":{{"@type":"Organization","name":"Drivenn Agency"}},"datePublished":"{date_iso}"}}
  </script>
</head>
<body data-page="blog">
<!--#HEADER#--><!--#HEADER-END#-->
<main>
  <article>
    <section class="article-hero" style="background-image:linear-gradient(rgba(10,26,48,.82),rgba(14,35,64,.9)),url('{image}');background-size:cover;background-position:center">
      <div class="container">
        <a href="{L}blog.html" class="article-back">{arrow_back} {blog_back}</a>
        <span class="article-hero__cat">{cat}</span>
        <h1>{title}</h1>
        <div class="article-hero__meta">
          <span>{cal} {date}</span>
          <span>{clock} {reading} {min_read}</span>
        </div>
      </div>
    </section>
    <section class="section" style="padding-top:0">
      <div class="article-body">
        {body}
        <div class="article-cta">
          <h3>{cta_h}</h3>
          <p>{cta_p}</p>
          <div class="btn-row center" style="margin-top:16px"><a href="{L}concept.html" class="btn btn--gold">{cta_b1}</a><a href="{L}ai-oplossingen.html" class="btn btn--outline">{cta_b2}</a></div>
        </div>
      </div>
    </section>
  </article>
</main>
<!--#FOOTER#--><!--#FOOTER-END#-->
<script src="/js/main.js"></script>
</body>
</html>
"""

def _blogfields(d, lang):
    o = d.get(lang) or d.get("nl", {})
    title = o.get("titel") or o.get("title","")
    summary = o.get("samenvatting") or o.get("summary","")
    body = o.get("tekst") or o.get("text","")
    cat = o.get("category") or o.get("categorie") or d.get("category","")
    return title, summary, body, cat

def build_blog(lang):
    u = UI[lang]; L = lp(lang); base = outdir(lang)
    (base/"blog").mkdir(parents=True, exist_ok=True)
    posts = []
    for f in sorted((ROOT/"content/blog").glob("*.json")):
        d = json.loads(read(f))
        title, summary, body, cat = _blogfields(d, lang)
        slug = d["slug"]; image = d.get("image",""); date_iso = d.get("date","")
        reading = d.get("reading_time_min", 4)
        paths = {lg: f"{lp(lg)}blog/{slug}.html" for lg in ACTIVE}
        canon = f"{SITE}{paths[lang]}"
        ogimg = image if image.startswith("http") else SITE+image
        page = BLOG_PAGE.format(
            code=u["code"], title=html.escape(title, quote=True), summary=html.escape(summary, quote=True),
            canon=canon, hreflang=hreflang_block(paths), ogimg=ogimg, image=image,
            cat=html.escape(cat), date=fmt_date(date_iso, lang), date_iso=date_iso, reading=reading,
            body=md(body), L=L, arrow_back=ARROW_BACK, blog_back=u["blog_back"], min_read=u["min_read"],
            cal=ICON_CAL, clock=ICON_CLOCK, cta_h=u["blog_cta_h"], cta_p=u["blog_cta_p"],
            cta_b1=u["blog_cta_b1"], cta_b2=u["blog_cta_b2"])
        write(base/f"blog/{slug}.html", page)
        posts.append({"slug":slug,"title":title,"summary":summary,"image":image,"cat":cat,
                      "date_iso":date_iso,"date":fmt_date(date_iso, lang),"reading":reading})
    posts.sort(key=lambda p: p["date_iso"], reverse=True)

    def card(p):
        srch = html.escape((p["title"]+" "+p["summary"]+" "+p["cat"]).lower(), quote=True)
        return f'''<a href="{L}blog/{p['slug']}.html" class="card blog-card reveal" data-blog-card data-search="{srch}">
  <div class="blog-card__img" style="background-image:url('{p['image']}')"></div>
  <div class="card__body">
    <span class="blog-card__cat">{html.escape(p['cat'])}</span>
    <h3>{html.escape(p['title'])}</h3>
    <p>{html.escape(p['summary'])}</p>
    <div class="blog-card__meta"><span>{ICON_CAL} {p['date']}</span><span>{ICON_CLOCK} {p['reading']} {u['min']}</span></div>
  </div>
</a>'''
    all_cards = "\n".join(card(p) for p in posts)
    if (base/"blog.html").exists():
        write(base/"blog.html", inject_marker(read(base/"blog.html"), "BLOG_CARDS", all_cards))
    teaser = "\n".join(card(p) for p in posts[:3])
    if (base/"index.html").exists():
        write(base/"index.html", inject_marker(read(base/"index.html"), "BLOG_TEASER", teaser))
    return posts

# ---------------------------------------------------------------------------
# AI-oplossingen
# ---------------------------------------------------------------------------
AI_PAGE = """<!DOCTYPE html>
<html lang="{code}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | {title_suffix}</title>
  <meta name="description" content="{summary}">
  <link rel="stylesheet" href="/assets/css/style.css">
  <link rel="canonical" href="{canon}">
{hreflang}
  <link rel="icon" type="image/x-icon" href="/assets/images/favicon.ico">
  <link rel="icon" type="image/png" sizes="32x32" href="/assets/images/favicon-32x32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/assets/images/apple-touch-icon.png">
  <meta property="og:title" content="{title} | Drivenn Agency">
  <meta property="og:description" content="{summary}">
  <meta property="og:url" content="{canon}">
</head>
<body data-page="ai">
<!--#HEADER#--><!--#HEADER-END#-->
<main>
  <section class="page-hero" style="text-align:left">
    <div class="container">
      <p class="page-hero__crumb"><a href="{L}index.html">{home}</a> / <a href="{L}ai-oplossingen.html">{crumb_ai}</a> / {cat}</p>
      <h1 style="max-width:22ch;margin:10px 0 16px">{title}</h1>
      <p class="lead" style="margin:0">{summary}</p>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="split" style="align-items:start">
        <div>
          {body}
          <h2 style="margin-top:2rem">{ai_what}</h2>
          <ul class="feature-list">{voordelen}</ul>
          {faq}
        </div>
        <aside>
          <div class="form-card ai-buy" style="position:sticky;top:100px">
            {price_block}
            {buy}
            <div class="ai-buy__sep"></div>
            <div class="ai-buy__apps"><span class="ai-buy__lbl">{workswith}</span><div class="ai-apps">{apps}</div></div>
            {req}
            <p class="ai-buy__install">{install_note}</p>
            <a href="{L}contact.html" class="btn btn--outline" style="width:100%">{install_btn}</a>
          </div>
        </aside>
      </div>
    </div>
  </section>
</main>
<!--#FOOTER#--><!--#FOOTER-END#-->
<script src="/js/main.js"></script>
</body>
</html>
"""

def app_chip(name):
    return f'<span class="ai-app">{APP_ICON}{html.escape(name)}</span>'

def _aifields(d, lang):
    """Basis is NL (platte velden); overschrijf met d[lang] indien aanwezig."""
    o = dict(d)
    tr = d.get(lang)
    if isinstance(tr, dict): o.update(tr)
    return o

def build_ai(lang):
    u = UI[lang]; L = lp(lang); base = outdir(lang)
    (base/"ai-oplossingen").mkdir(parents=True, exist_ok=True)
    sols = []
    for f in sorted((ROOT/"content/ai").glob("*.json")):
        sols.append(json.loads(read(f)))
    sols.sort(key=lambda s: s.get("binnenkort", False))

    for d in sols:
        o = _aifields(d, lang)
        slug = d["slug"]; title = o["titel"]; summary = o["samenvatting"]
        cat = u["cat_ai"].get(d.get("categorie",""), u["ai_default_cat"])
        paths = {lg: f"{lp(lg)}ai-oplossingen/{slug}.html" for lg in ACTIVE}
        canon = f"{SITE}{paths[lang]}"
        body = md(o.get("beschrijving",""))
        voordelen = "".join(f'<li><span class="fl-ico">{ICON_CHECK}</span><span><b>{inline(html.escape(v))}</b></span></li>' for v in o.get("voordelen",[]))
        faqs = o.get("faq",[])
        if faqs:
            items = "".join(f'<div class="faq__item"><button class="faq__q" type="button">{html.escape(q["v"])}<span class="fq-plus"></span></button><div class="faq__a"><p>{html.escape(q["a"])}</p></div></div>' for q in faqs)
            faq = f'<h2 style="margin-top:2.4rem">{u["ai_faq"]}</h2><div class="faq" style="margin:0">{items}</div>'
        else: faq = ""
        apps = "".join(app_chip(a) for a in d.get("apps",[]))
        if o.get("vereiste"):
            req = f'<div class="ai-req">{ICON_CHECK_SMALL}<span><strong>{u["ai_foryou"]}</strong>{html.escape(o.get("vereiste",""))}</span></div>'
        elif d.get("binnenkort"):
            req = f'<div class="ai-req ai-req--soon">{ICON_CLOCK}<span><strong>{u["ai_soon_badge"]}</strong>{u["ai_soon_note"]}</span></div>'
        else: req = ""
        if d.get("binnenkort"):
            price_block = f'<div style="text-align:center;margin-bottom:16px"><span class="ai-card__soon" style="position:static;display:inline-block">{u["ai_soon_badge"]}</span></div>'
            buy = f'<a href="{L}ai-oplossingen.html#updates" class="btn btn--navy" style="width:100%">{u["ai_keepposted"]}</a>'
        else:
            price_block = f'<div class="ai-price" style="font-size:1.9rem;text-align:center;margin-bottom:4px">{html.escape(d.get("prijs",""))}<small style="text-align:center">{html.escape(o.get("prijs_note",""))}</small></div>'
            buy = f'<a href="{L}contact.html" class="btn btn--gold" style="width:100%">{u["ai_buy"]}</a><p class="form-note" style="text-align:center">{u["ai_buy_note"]}</p>'
        page = AI_PAGE.format(code=u["code"], title=html.escape(title,quote=True), title_suffix=u["ai_title_suffix"],
            summary=html.escape(summary,quote=True), canon=canon, hreflang=hreflang_block(paths),
            L=L, home=u["home"], crumb_ai=u["crumb_ai"], cat=cat, body=body, ai_what=u["ai_what"],
            voordelen=voordelen, faq=faq, workswith=u["ai_workswith"], apps=apps, req=req,
            price_block=price_block, buy=buy, install_note=u["ai_install_note"], install_btn=u["ai_install_btn"])
        write(base/f"ai-oplossingen/{slug}.html", page)

    def card(d):
        o = _aifields(d, lang)
        slug=d["slug"]; title=o["titel"]; summary=o["samenvatting"]; catkey=d.get("categorie","")
        cat=u["cat_ai"].get(catkey,u["ai_default_cat"]); cat_plain=cat.replace("&amp;","en")
        srch = html.escape((title+" "+summary+" "+" ".join(d.get("apps",[]))+" "+cat_plain+" "+catkey).lower(), quote=True)
        banner = d.get("banner","")
        bannerhtml = f'<div class="ai-card__banner" style="background-image:url(\'{banner}\')">' if banner else '<div class="ai-card__banner"><span class="ph">DRIVENN · AI</span>'
        soon = f'<span class="ai-card__soon">{u["ai_soon_short"]}</span>' if d.get("binnenkort") else ''
        apps = "".join(app_chip(a) for a in d.get("apps",[]))
        if o.get("vereiste"):
            req = f'<div class="ai-req">{ICON_CHECK_SMALL}<span><strong>{u["ai_foryou"]}</strong>{html.escape(o.get("vereiste",""))}</span></div>'
        elif d.get("binnenkort"):
            req = f'<div class="ai-req ai-req--soon">{ICON_CLOCK}<span><strong>{u["ai_soon_badge"]}</strong>{u["ai_soon_note"]}</span></div>'
        else: req = ''
        if d.get("binnenkort"):
            foot = f'<div class="ai-card__foot"><span class="ai-price" style="font-size:1rem;color:var(--ink-faint)">{u["ai_indev"]}</span><a href="{L}ai-oplossingen/{slug}.html" class="btn btn--outline">{u["ai_view"]}</a></div>'
        else:
            foot = f'<div class="ai-card__foot"><div class="ai-price">{html.escape(d.get("prijs",""))}<small>{html.escape(o.get("prijs_note",""))}</small></div><a href="{L}ai-oplossingen/{slug}.html" class="btn btn--navy">{u["ai_view"]}</a></div>'
        return f'''<div class="ai-card reveal" data-ai-card data-cat="{catkey}" data-search="{srch}">
  {bannerhtml}{soon}</div>
  <div class="ai-card__body">
    <span class="ai-card__cat">{cat}</span>
    <h3>{html.escape(title)}</h3>
    <p>{html.escape(summary)}</p>
    <div class="ai-apps">{apps}</div>
    <div class="ai-card__bottom">{req}{foot}</div>
  </div>
</div>'''
    cards = "\n".join(card(d) for d in sols)
    if (base/"ai-oplossingen.html").exists():
        write(base/"ai-oplossingen.html", inject_marker(read(base/"ai-oplossingen.html"), "AI_CARDS", cards))
    return sols

# ---------------------------------------------------------------------------
# cases
# ---------------------------------------------------------------------------
def build_cases(lang):
    u = UI[lang]; base = outdir(lang)
    cases = [json.loads(read(f)) for f in sorted((ROOT/"content/cases").glob("*.json"))]
    def card(d):
        o = d.get(lang) or d.get("nl",{})
        title=o.get("titel") or o.get("title",""); desc=o.get("beschrijving") or o.get("description","")
        link=d.get("link","#"); img=d.get("image",""); cat=d.get("categorie","Website")
        return f'''<a href="{link}" target="_blank" rel="noopener" class="card reveal">
  <div class="blog-card__img" style="background-image:url('{img}')"></div>
  <div class="card__body">
    <span class="blog-card__cat">{html.escape(cat)}</span>
    <h3>{html.escape(title)}</h3>
    <p>{html.escape(desc)}</p>
    <span class="btn--ghost" style="margin-top:auto">{u['cases_view']} {ICON_ARROW}</span>
  </div>
</a>'''
    cards = "\n".join(card(d) for d in cases)
    if (base/"cases.html").exists():
        write(base/"cases.html", inject_marker(read(base/"cases.html"), "CASES_CARDS", cards))
    if (base/"index.html").exists():
        write(base/"index.html", inject_marker(read(base/"index.html"), "CASES_TEASER", cards))
    return cases

# ---------------------------------------------------------------------------
# relativize (per pagina, diepte-correct)
# ---------------------------------------------------------------------------
def relativize(t, depth):
    prefix = "../" * depth
    t = re.sub(r'(href|src|poster|data-src)="/(?!/)', lambda m: f'{m.group(1)}="{prefix}', t)
    t = re.sub(r"url\((\s*['\"]?)/(?!/)", lambda m: f"url({m.group(1)}{prefix}", t)
    return t

def relativize_all():
    pages = []
    for lang in ACTIVE:
        base = outdir(lang)
        pages += list(base.glob("*.html"))
        for sub in ("blog", "ai-oplossingen"):
            if (base/sub).exists(): pages += list((base/sub).glob("*.html"))
    for p in pages:
        depth = len(p.relative_to(ROOT).parts) - 1
        write(p, relativize(read(p), depth))

# ---------------------------------------------------------------------------
# SEO: canonical + hreflang (statische pagina's) en structured data
# ---------------------------------------------------------------------------
def _strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).replace("&amp;", "&").strip()

FAQ_RE = re.compile(r'class="faq__q"[^>]*>(.*?)<span class="fq-plus"></span></button><div class="faq__a"><p>(.*?)</p>', re.S)

def fix_static_head(lang):
    """Zet op elke statische pagina een correcte canonical + hreflang-set (alleen
    ACTIVE talen, dus geen 404-verwijzingen). Draait niet op de gegenereerde
    blog-/AI-detailpagina's; die krijgen hun head al uit hun template."""
    base = outdir(lang)
    for p in base.glob("*.html"):
        key = p.name
        t = read(p)
        canon = f"{SITE}{lp(lang)}" if key == "index.html" else f"{SITE}{lp(lang)}{key}"
        def href(lg):
            return f"{SITE}{lp(lg)}" if key == "index.html" else f"{SITE}{lp(lg)}{key}"
        links = [f'<link rel="canonical" href="{canon}">']
        for lg in ACTIVE:
            links.append(f'<link rel="alternate" hreflang="{UI[lg]["code"]}" href="{href(lg)}">')
        links.append(f'<link rel="alternate" hreflang="x-default" href="{href("nl")}">')
        block = "<!--HEADLINKS-->" + "".join(links) + "<!--/HEADLINKS-->"
        t = re.sub(r'<!--HEADLINKS-->.*?<!--/HEADLINKS-->', '', t, flags=re.S)
        t = re.sub(r'\s*<link rel="canonical"[^>]*>', '', t)
        t = re.sub(r'\s*<link rel="alternate" hreflang="[^"]*"[^>]*>', '', t)
        t = t.replace('</head>', '  ' + block + '\n</head>', 1)
        write(p, t)

def _faq_schema(t):
    items = FAQ_RE.findall(t)
    if not items:
        return None
    qa = [{"@type": "Question", "name": _strip_tags(q),
           "acceptedAnswer": {"@type": "Answer", "text": _strip_tags(a)}} for q, a in items]
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": qa}

def _breadcrumb_schema(t, lang):
    m = re.search(r'<p class="page-hero__crumb">(.*?)</p>', t, re.S)
    if not m:
        return None
    inner = m.group(1)
    items = []
    pos = 1
    for hrefv, label in re.findall(r'<a href="([^"]+)">(.*?)</a>', inner):
        items.append({"@type": "ListItem", "position": pos, "name": _strip_tags(label),
                      "item": f"{SITE}{lp(lang)}" if hrefv == "index.html" else f"{SITE}{lp(lang)}{hrefv}"})
        pos += 1
    tail = _strip_tags(inner.rsplit('</a>', 1)[-1]).lstrip('/ ').strip()
    if tail:
        items.append({"@type": "ListItem", "position": pos, "name": tail})
    if len(items) < 2:
        return None
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}

def inject_seo_schema(lang):
    base = outdir(lang)
    pages = list(base.glob("*.html"))
    for sub in ("blog", "ai-oplossingen"):
        if (base/sub).exists():
            pages += list((base/sub).glob("*.html"))
    for p in pages:
        t = read(p)
        t = re.sub(r'<!--SEOSCHEMA-->.*?<!--/SEOSCHEMA-->', '', t, flags=re.S)
        blocks = [b for b in (_faq_schema(t), _breadcrumb_schema(t, lang)) if b]
        if blocks:
            scripts = "".join('<script type="application/ld+json">' + json.dumps(b, ensure_ascii=False) + '</script>' for b in blocks)
            t = t.replace('</head>', '  <!--SEOSCHEMA-->' + scripts + '<!--/SEOSCHEMA-->\n</head>', 1)
        write(p, t)

# ---------------------------------------------------------------------------
# sitemap (alle talen + hreflang)
# ---------------------------------------------------------------------------
def build_sitemap(all_posts, all_sols, all_cases):
    static = ["index.html","websites.html","nieuwe-website.html","redesign.html","hosting.html",
              "ai-oplossingen.html","concept.html","cases.html","blog.html","over-ons.html","contact.html"]
    entries = []  # (loc, {lang:loc})
    def loc(lang, page):
        pre = lp(lang)
        return f"{SITE}{pre}{'' if page=='index.html' else page}" if page=="index.html" else f"{SITE}{pre}{page}"
    for page in static:
        alts = {lg: (f"{SITE}{lp(lg)}" if page=="index.html" else f"{SITE}{lp(lg)}{page}") for lg in ACTIVE}
        for lg in ACTIVE: entries.append((alts[lg], alts))
    for s in all_sols["nl"]:
        alts = {lg: f"{SITE}{lp(lg)}ai-oplossingen/{s['slug']}.html" for lg in ACTIVE}
        for lg in ACTIVE: entries.append((alts[lg], alts))
    for p in all_posts["nl"]:
        alts = {lg: f"{SITE}{lp(lg)}blog/{p['slug']}.html" for lg in ACTIVE}
        for lg in ACTIVE: entries.append((alts[lg], alts))
    rows = []
    XH = 'xmlns:xhtml="http://www.w3.org/1999/xhtml"'
    for loc_, alts in entries:
        links = "".join(f'<xhtml:link rel="alternate" hreflang="{UI[lg]["code"]}" href="{alts[lg]}"/>' for lg in ACTIVE)
        rows.append(f'  <url><loc>{loc_}</loc>{links}</url>')
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" {XH}>\n' + "\n".join(rows) + "\n</urlset>\n"
    write(ROOT/"sitemap.xml", xml)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    all_posts, all_sols, all_cases = {}, {}, {}
    for lang in ACTIVE:
        all_posts[lang] = build_blog(lang)
        all_sols[lang]  = build_ai(lang)
        all_cases[lang] = build_cases(lang)
        inject_components(lang)
        fix_static_head(lang)
        inject_seo_schema(lang)
    build_sitemap(all_posts, all_sols, all_cases)
    relativize_all()
    langs = ", ".join(ACTIVE)
    print(f"Gegenereerd voor talen: {langs} — {len(all_posts['nl'])} blogs, {len(all_sols['nl'])} AI, {len(all_cases['nl'])} cases per taal.")
