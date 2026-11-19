# Drivenn Agency: website

Statische website (HTML/CSS/JS) in drie talen, gehost op **Vercel** op
<https://www.drivennagency.nl>. Content staat in JSON en wordt via Sveltia CMS (`/admin/`)
beheerd; een Python-script bouwt daar de pagina's van.

## Structuur

| Map / bestand | Inhoud |
| --- | --- |
| `*.html`, `eng/`, `de/` | Pagina's in het Nederlands (root), Engels (`/eng/`) en Duits (`/de/`). Ze zijn tegelijk bron én resultaat: het build-script werkt alleen de beheerde delen bij. |
| `blog/`, `ai-oplossingen/` (ook onder `eng/` en `de/`) | Volledig gegenereerde detailpagina's. Niet met de hand aanpassen. |
| `content/blog`, `content/ai`, `content/cases` | De content (JSON, per taal), bewerkbaar via het CMS. |
| `components/` | Header en footer per taal. |
| `assets/` | CSS, lettertypes, afbeeldingen, video. |
| `js/` | `main.js` (menu, taalwissel, animaties, filters), `form.js` (formulieren via Web3Forms), `consent.js` (cookiebanner + Google Analytics met Consent Mode), `concept.js` (wizard voor het gratis websiteconcept). |
| `api/` | Serverless functies op Vercel: CMS-login (`auth`, `callback`) en dashboardcijfers (`search-console-stats`, `analytics-stats`, `social-stats`). Gedeelde code staat in `api/_lib/` (wordt niet als endpoint gepubliceerd). |
| `scripts/build_content.py` | Bouwt alle pagina's, kaarten, `<head>`, structured data en `sitemap.xml`. |
| `scripts/optimize_images.py` | Maakt WebP-versies (+640 px) van content-afbeeldingen; de build zet ze in een `<picture>`. GitHub doet dit automatisch na een upload. |
| `scripts/check_site.py` | Controleert de gebouwde site (links, ankers, canonical, hreflang, structured data, sitemap). |
| `tests/` | Tests voor de API-functies (`node --test`) en het build-script (`unittest`). |
| `vercel.json` | Beveiligings- en cacheheaders, redirects van `/index.html` naar `/`. |
| `.vercelignore` | Houdt bronbestanden (`scripts/`, `components/`, `tests/`) van de live site. |

## Werken aan de site

```bash
python3 scripts/optimize_images.py        # WebP-versies van nieuwe foto's maken (vereist: pip install pillow)
python3 scripts/build_content.py          # alles opnieuw bouwen
python3 scripts/build_content.py --check  # alleen controleren of alles up-to-date is
python3 scripts/check_site.py             # links, SEO en structured data controleren
node --test tests/*.test.js               # API-tests
python3 -m unittest discover -s tests      # tests voor het build-script
```

Er zijn geen externe pakketten nodig (alleen Python 3 en Node 18+).

**Wat het build-script beheert** (dus niet met de hand aanpassen, het wordt overschreven):

- alles tussen `<!--AUTO:HEAD-->` en `<!--/AUTO:HEAD-->`: stylesheet, favicons, canonical,
  hreflang (incl. `x-default`), Open Graph/Twitter, robots, JSON-LD en de Analytics-configuratie;
- header en footer tussen `<!--#HEADER#-->` / `<!--#FOOTER#-->`;
- kaarten tussen `<!--#BLOG_CARDS#-->`, `<!--#BLOG_TEASER#-->`, `<!--#AI_CARDS#-->`,
  `<!--#CASES_CARDS#-->` en `<!--#CASES_TEASER#-->`;
- de pagina's in `blog/` en `ai-oplossingen/`, en `sitemap.xml`.

Titel en meta description staan gewoon in de pagina zelf en mag je aanpassen. Een eigen
`og:title`/`og:description`/`og:image` buiten het AUTO-blok blijft ook behouden.

Alle interne links zijn paden vanaf de root (`/contact.html`, `/eng/blog.html`), zodat ze op
elke diepte werken (ook op de 404-pagina). CSS en JS krijgen automatisch `?v=<hash>`, zodat
browsers na een wijziging direct de nieuwe versie laden.

## Automatisch

- **`build-content.yml`**: bij een push naar `main` die content, componenten, CSS, JS of HTML
  raakt, bouwt GitHub Actions de site opnieuw, controleert hem en commit het resultaat. Faalt een
  controle, dan wordt er niets gecommit en zie je de fout in het tabblad *Actions*.
- **`checks.yml`**: bij elke pull request dezelfde controles, zodat fouten zichtbaar zijn
  vóórdat je merget.

## Content toevoegen

Via het CMS op `/admin/` (inloggen met GitHub) of door een JSON-bestand toe te voegen in
`content/…` en daarna te bouwen.

- **Blog** (`content/blog/<slug>.json`): per taal `titel`/`title`, samenvatting, `tekst`
  (eenvoudige Markdown: koppen, lijsten, citaten, links), `date` (JJJJ-MM-DD), `category`,
  `image`, `reading_time_min`. Optioneel `updated` (JJJJ-MM-DD) voor een bijgewerkt artikel.
- **AI-oplossing** (`content/ai/<slug>.json`): `titel`, `categorie`
  (`documenten` / `tekst` / `communicatie`), `prijs`, `banner` (1200×630), `apps`,
  `vereiste`, `voordelen`, `faq`. `binnenkort: true` voor een oplossing die nog niet te koop is.
- **Case** (`content/cases/<slug>.json`).

## Omgevingsvariabelen (Vercel)

| Variabele | Voor |
| --- | --- |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | CMS-login via GitHub OAuth |
| `CMS_ALLOWED_ORIGINS` (optioneel) | Extra adressen (kommagescheiden) waarvandaan het CMS mag inloggen, naast www.drivennagency.nl en drivennagency.nl |
| `GOOGLE_SC_CLIENT_EMAIL`, `GOOGLE_SC_PRIVATE_KEY`, `GOOGLE_SC_SITE_URL` | Search Console-cijfers |
| `GA4_PROPERTY_ID` (+ optioneel `GOOGLE_GA_CLIENT_EMAIL`, `GOOGLE_GA_PRIVATE_KEY`) | Websitebezoekers uit GA4 |
| `META_PAGE_ACCESS_TOKEN`, `META_IG_BUSINESS_ID`, `META_PAGE_ID` | Instagram/Facebook-cijfers |

## Nog te regelen

1. **Betaalplatform**: de "Kopen"-knop op AI-detailpagina's linkt naar het contactformulier.
   Vervang die door een betaallink zodra Stripe of Mollie is ingericht.
2. **`pages.yml`**: deze handmatige GitHub Pages-workflow wordt niet meer gebruikt (de site
   draait op Vercel) en kan weg.
