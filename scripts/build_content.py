#!/usr/bin/env python3
"""
Genereert de statische Drivenn Agency-site:
- injecteert components/header.html + footer.html in alle pagina's
- genereert blogkaarten + blogpagina's uit content/blog/*.json
- genereert AI-kaarten + AI-detailpagina's uit content/ai/*.json
- genereert case-kaarten uit content/cases/*.json
- bouwt sitemap.xml

Draai lokaal: python3 scripts/build_content.py
"""
import json, pathlib, re, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://www.drivennagency.nl"

MONTHS = ["januari","februari","maart","april","mei","juni","juli","augustus","september","oktober","november","december"]
CAT_LABEL = {"documenten":"Documenten &amp; administratie","tekst":"Tekst &amp; data","communicatie":"Klantcommunicatie"}

def read(p): return pathlib.Path(p).read_text(encoding="utf-8")
def write(p, s): pathlib.Path(p).write_text(s, encoding="utf-8")

def inject_marker(t, name, content):
    """Idempotent replace of content between <!--#NAME#--> and <!--#NAME-END#-->."""
    return re.sub(r'<!--#'+name+r'#-->.*?<!--#'+name+r'-END#-->',
                  lambda m: '<!--#'+name+'#-->'+content+'<!--#'+name+'-END#-->', t, flags=re.S)

def fmt_date(iso):
    try:
        y,m,d = iso.split("-"); return f"{int(d)} {MONTHS[int(m)-1]} {y}"
    except Exception:
        return iso

def md(text):
    """Minimale markdown -> HTML (##, ###, **bold**, - lijst, paragrafen)."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1; continue
        if ln.startswith("### "):
            out.append(f"<h3>{inline(ln[4:])}</h3>")
        elif ln.startswith("## "):
            out.append(f"<h2>{inline(ln[3:])}</h2>")
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(f"<li>{inline(lines[i].strip()[2:])}</li>"); i += 1
            out.append("<ul>"+"".join(items)+"</ul>"); continue
        else:
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)

def inline(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"_(.+?)_", r"<em>\1</em>", s)
    return s

ICON_CAL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>'
ICON_CLOCK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>'
ICON_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>'
ICON_ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
APP_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>'

# ---------------------------------------------------------------------------
# component injection
# ---------------------------------------------------------------------------
def inject_components():
    header = read(ROOT/"components/header.html").strip()
    footer = read(ROOT/"components/footer.html").strip()
    pages = [p for p in ROOT.glob("*.html")]
    pages += [p for p in (ROOT/"blog").glob("*.html")] if (ROOT/"blog").exists() else []
    pages += [p for p in (ROOT/"ai-oplossingen").glob("*.html")] if (ROOT/"ai-oplossingen").exists() else []
    # Idempotent injection between unique comment markers (survives repeated builds,
    # unlike a nested-<div> match which breaks on the first inner </div>).
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
<html lang="nl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Drivenn Agency</title>
  <meta name="description" content="{summary}">
  <link rel="stylesheet" href="/assets/css/style.css">
  <link rel="canonical" href="{canon}">
  <link rel="alternate" hreflang="nl" href="{canon}">
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
        <a href="/blog.html" class="article-back">{arrow_back} Terug naar blog</a>
        <span class="article-hero__cat">{cat}</span>
        <h1>{title}</h1>
        <div class="article-hero__meta">
          <span>{cal} {date}</span>
          <span>{clock} {reading} min lezen</span>
        </div>
      </div>
    </section>
    <section class="section" style="padding-top:0">
      <div class="article-body">
        {body}
        <div class="article-cta">
          <h3>Hulp nodig met jouw website of automatisering?</h3>
          <p>Vraag een gratis websiteconcept aan of laat ons meedenken over de juiste AI-oplossing.</p>
          <div class="btn-row center" style="margin-top:16px"><a href="/concept.html" class="btn btn--gold">Gratis concept</a><a href="/ai-oplossingen.html" class="btn btn--outline">AI-oplossingen</a></div>
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

def build_blog():
    (ROOT/"blog").mkdir(exist_ok=True)
    posts = []
    for f in sorted((ROOT/"content/blog").glob("*.json")):
        d = json.loads(read(f))
        nl = d.get("nl", {})
        title = nl.get("titel") or nl.get("title","")
        summary = nl.get("samenvatting") or nl.get("summary","")
        body = md(nl.get("tekst") or nl.get("text",""))
        slug = d["slug"]; image = d.get("image",""); cat = d.get("category","")
        date_iso = d.get("date",""); reading = d.get("reading_time_min", 4)
        canon = f"{SITE}/blog/{slug}.html"
        ogimg = image if image.startswith("http") else SITE+image
        page = BLOG_PAGE.format(
            title=html.escape(title, quote=True), summary=html.escape(summary, quote=True),
            canon=canon, ogimg=ogimg, image=image, cat=cat, date=fmt_date(date_iso),
            date_iso=date_iso, reading=reading, body=body,
            cal=ICON_CAL, clock=ICON_CLOCK, arrow_back='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><path d="M19 12H5M11 18l-6-6 6-6"/></svg>')
        write(ROOT/f"blog/{slug}.html", page)
        posts.append({"slug":slug,"title":title,"summary":summary,"image":image,"cat":cat,"date_iso":date_iso,"date":fmt_date(date_iso),"reading":reading})
    posts.sort(key=lambda p: p["date_iso"], reverse=True)

    def card(p):
        srch = html.escape((p["title"]+" "+p["summary"]+" "+p["cat"]).lower(), quote=True)
        return f'''<a href="/blog/{p['slug']}.html" class="card blog-card reveal" data-blog-card data-search="{srch}">
  <div class="blog-card__img" style="background-image:url('{p['image']}')"></div>
  <div class="card__body">
    <span class="blog-card__cat">{p['cat']}</span>
    <h3>{html.escape(p['title'])}</h3>
    <p>{html.escape(p['summary'])}</p>
    <div class="blog-card__meta"><span>{ICON_CAL} {p['date']}</span><span>{ICON_CLOCK} {p['reading']} min</span></div>
  </div>
</a>'''

    all_cards = "\n".join(card(p) for p in posts)
    write(ROOT/"blog.html", inject_marker(read(ROOT/"blog.html"), "BLOG_CARDS", all_cards))

    teaser = "\n".join(card(p) for p in posts[:3])
    write(ROOT/"index.html", inject_marker(read(ROOT/"index.html"), "BLOG_TEASER", teaser))
    return posts

# ---------------------------------------------------------------------------
# AI solutions
# ---------------------------------------------------------------------------
AI_PAGE = """<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | AI-oplossingen | Drivenn Agency</title>
  <meta name="description" content="{summary}">
  <link rel="stylesheet" href="/assets/css/style.css">
  <link rel="canonical" href="{canon}">
  <link rel="alternate" hreflang="nl" href="{canon}">
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
      <p class="page-hero__crumb"><a href="/index.html">Home</a> / <a href="/ai-oplossingen.html">AI-oplossingen</a> / {cat}</p>
      <span class="article-hero__cat">{cat}</span>
      <h1 style="max-width:22ch;margin:14px 0 16px">{title}</h1>
      <p class="lead" style="margin:0">{summary}</p>
    </div>
  </section>

  <section class="section">
    <div class="container">
      <div class="split" style="align-items:start">
        <div>
          {body}
          <h2 style="margin-top:2rem">Wat het je oplevert</h2>
          <ul class="feature-list">{voordelen}</ul>
          {faq}
        </div>
        <aside>
          <div class="form-card" style="position:sticky;top:100px">
            {price_block}
            <div class="ai-apps" style="margin-bottom:14px">{apps}</div>
            {req}
            {buy}
            <div class="install-banner" style="margin-top:18px;padding:18px 20px">
              <div class="ib-ico" style="width:44px;height:44px">{install_ico}</div>
              <div class="install-banner__txt"><h4 style="font-size:1rem">Laat het ons installeren</h4><p style="font-size:.85rem">Liever niet zelf opzetten? Wij komen het bij je bedrijf inrichten.</p></div>
            </div>
            <a href="/contact.html" class="btn btn--outline" style="width:100%;margin-top:12px">Vraag installatie aan</a>
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

INSTALL_ICO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 2 7l10 5 10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/></svg>'

def app_chip(name):
    return f'<span class="ai-app">{APP_ICON}{html.escape(name)}</span>'

def build_ai():
    (ROOT/"ai-oplossingen").mkdir(exist_ok=True)
    sols = []
    for f in sorted((ROOT/"content/ai").glob("*.json")):
        sols.append(json.loads(read(f)))
    # published first, then binnenkort; keep file order otherwise
    sols.sort(key=lambda s: s.get("binnenkort", False))

    for d in sols:
        slug = d["slug"]; title = d["titel"]; summary = d["samenvatting"]
        cat = CAT_LABEL.get(d.get("categorie",""), "AI-oplossing")
        canon = f"{SITE}/ai-oplossingen/{slug}.html"
        body = md(d.get("beschrijving",""))
        voordelen = "".join(f'<li><span class="fl-ico">{ICON_CHECK}</span><span><b>{inline(html.escape(v))}</b></span></li>' for v in d.get("voordelen",[]))
        faqs = d.get("faq",[])
        if faqs:
            items = "".join(f'<div class="faq__item"><button class="faq__q" type="button">{html.escape(q["v"])}<span class="fq-plus"></span></button><div class="faq__a"><p>{html.escape(q["a"])}</p></div></div>' for q in faqs)
            faq = f'<h2 style="margin-top:2.4rem">Veelgestelde vragen</h2><div class="faq" style="margin:0">{items}</div>'
        else:
            faq = ""
        apps = "".join(app_chip(a) for a in d.get("apps",[]))
        req = f'<div class="ai-req">{ICON_CHECK_SMALL}<span>{html.escape(d["vereiste"])}</span></div>' if d.get("vereiste") else ""
        if d.get("binnenkort"):
            price_block = '<div style="text-align:center;margin-bottom:16px"><span class="ai-card__soon" style="position:static;display:inline-block">Binnenkort beschikbaar</span></div>'
            buy = '<a href="/ai-oplossingen.html#updates" class="btn btn--navy" style="width:100%">Houd mij op de hoogte</a>'
        else:
            price_block = f'<div class="ai-price" style="font-size:1.9rem;text-align:center;margin-bottom:4px">{html.escape(d.get("prijs",""))}<small style="text-align:center">{html.escape(d.get("prijs_note",""))}</small></div>'
            buy = f'<a href="/contact.html" class="btn btn--gold" style="width:100%">Kopen &amp; ontvangen</a><p class="form-note" style="text-align:center">Eenmalige aanschaf · handleiding per e-mail · betaling volgt via een beveiligd platform</p>'
        page = AI_PAGE.format(title=html.escape(title,quote=True), summary=html.escape(summary,quote=True),
            canon=canon, cat=cat, body=body, voordelen=voordelen, faq=faq, apps=apps, req=req,
            price_block=price_block, buy=buy, install_ico=INSTALL_ICO)
        write(ROOT/f"ai-oplossingen/{slug}.html", page)

    def card(d):
        slug=d["slug"]; title=d["titel"]; summary=d["samenvatting"]; catkey=d.get("categorie","")
        cat=CAT_LABEL.get(catkey,"AI-oplossing")
        cat_plain = cat.replace("&amp;","en")
        srch = html.escape((title+" "+summary+" "+" ".join(d.get("apps",[]))+" "+cat_plain+" "+catkey).lower(), quote=True)
        banner = d.get("banner","")
        if banner:
            bannerhtml = f'<div class="ai-card__banner" style="background-image:url(\'{banner}\')">'
        else:
            bannerhtml = '<div class="ai-card__banner"><span class="ph">DRIVENN · AI</span>'
        soon = '<span class="ai-card__soon">Binnenkort</span>' if d.get("binnenkort") else ''
        apps = "".join(app_chip(a) for a in d.get("apps",[]))
        req = f'<div class="ai-req">{ICON_CHECK_SMALL}<span>{html.escape(d["vereiste"])}</span></div>' if d.get("vereiste") else ''
        if d.get("binnenkort"):
            foot = f'<div class="ai-card__foot"><span class="ai-price" style="font-size:1rem;color:var(--ink-faint)">In ontwikkeling</span><a href="/ai-oplossingen/{slug}.html" class="btn btn--outline">Bekijk</a></div>'
        else:
            foot = f'<div class="ai-card__foot"><div class="ai-price">{html.escape(d.get("prijs",""))}<small>{html.escape(d.get("prijs_note",""))}</small></div><a href="/ai-oplossingen/{slug}.html" class="btn btn--navy">Bekijk</a></div>'
        return f'''<div class="ai-card reveal" data-ai-card data-cat="{catkey}" data-search="{srch}">
  {bannerhtml}{soon}</div>
  <div class="ai-card__body">
    <span class="ai-card__cat">{cat}</span>
    <h3>{html.escape(title)}</h3>
    <p>{html.escape(summary)}</p>
    <div class="ai-apps">{apps}</div>
    {req}
    {foot}
  </div>
</div>'''

    cards = "\n".join(card(d) for d in sols)
    write(ROOT/"ai-oplossingen.html", inject_marker(read(ROOT/"ai-oplossingen.html"), "AI_CARDS", cards))
    return sols

ICON_CHECK_SMALL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>'

# ---------------------------------------------------------------------------
# cases
# ---------------------------------------------------------------------------
def build_cases():
    cases = [json.loads(read(f)) for f in sorted((ROOT/"content/cases").glob("*.json"))]
    def card(d):
        nl=d.get("nl",{}); title=nl.get("titel",""); desc=nl.get("beschrijving","")
        link=d.get("link","#"); img=d.get("image",""); cat=d.get("categorie","Website")
        return f'''<a href="{link}" target="_blank" rel="noopener" class="card reveal">
  <div class="blog-card__img" style="background-image:url('{img}')"></div>
  <div class="card__body">
    <span class="blog-card__cat">{html.escape(cat)}</span>
    <h3>{html.escape(title)}</h3>
    <p>{html.escape(desc)}</p>
    <span class="btn--ghost" style="margin-top:auto">Bekijk live website {ICON_ARROW}</span>
  </div>
</a>'''
    cards = "\n".join(card(d) for d in cases)
    write(ROOT/"cases.html", inject_marker(read(ROOT/"cases.html"), "CASES_CARDS", cards))
    write(ROOT/"index.html", inject_marker(read(ROOT/"index.html"), "CASES_TEASER", cards))
    return cases

# ---------------------------------------------------------------------------
# sitemap
# ---------------------------------------------------------------------------
def build_sitemap(posts, sols, cases):
    urls = []
    static = [("/",1.0),("/websites.html",0.9),("/hosting.html",0.8),("/ai-oplossingen.html",0.9),
              ("/concept.html",0.9),("/cases.html",0.8),("/blog.html",0.8),("/over-ons.html",0.7),("/contact.html",0.7)]
    for path,pr in static:
        urls.append((SITE+path, pr))
    for s in sols:
        urls.append((f"{SITE}/ai-oplossingen/{s['slug']}.html", 0.7))
    for p in posts:
        urls.append((f"{SITE}/blog/{p['slug']}.html", 0.6))
    body = "\n".join(f'  <url><loc>{u}</loc><priority>{pr}</priority></url>' for u,pr in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n'
    write(ROOT/"sitemap.xml", xml)

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    posts = build_blog()
    sols = build_ai()
    cases = build_cases()
    inject_components()   # after content is generated, so blog/ai pages get header/footer too
    build_sitemap(posts, sols, cases)
    print(f"Gegenereerd: {len(posts)} blogposts, {len(sols)} AI-oplossingen, {len(cases)} cases.")
