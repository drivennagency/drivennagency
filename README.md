# Drivenn Agency — website

Statische website (HTML/CSS/JS), gehost op GitHub Pages. Zelfde bouwaanpak als
svanwijksolutions: content in JSON, een build-script genereert de pagina's.

## Structuur

- `index.html`, `websites.html`, `hosting.html`, `concept.html`, `ai-oplossingen.html`,
  `cases.html`, `blog.html`, `over-ons.html`, `contact.html`, `privacy.html`, `404.html`
- `components/header.html` + `components/footer.html` — worden door het build-script
  in elke pagina geïnjecteerd (tussen `<!--#HEADER#-->` / `<!--#FOOTER#-->` markers).
- `content/blog/*.json` — blogposts (nl/en/de). Genereren `blog/<slug>.html`.
- `content/ai/*.json` — AI-oplossingen. Genereren `ai-oplossingen/<slug>.html`.
- `content/cases/*.json` — cases.
- `scripts/build_content.py` — genereert pagina's, kaarten en `sitemap.xml`.
- `admin/` — Sveltia CMS om content toe te voegen zonder code.

## Content toevoegen

Via de CMS (`/admin/`) of door een JSON-bestand toe te voegen in `content/…` en het
build-script te draaien:

```
python3 scripts/build_content.py
```

De GitHub Action `build-content.yml` doet dit automatisch bij elke push die `content/**`,
`components/**` of het script raakt.

### AI-oplossing toevoegen

Voeg een bestand toe in `content/ai/`. Belangrijkste velden: `titel`, `categorie`
(`documenten` / `tekst` / `communicatie`), `prijs`, `banner` (de Canva-afbeelding, 16:9),
`apps` (lijst met app-namen — verschijnen als "werkt met"-badges), `vereiste`
(in één oogopslag), `voordelen`, `faq`. Zet `binnenkort: true` voor een nog-niet-te-koop
oplossing.

## Nog te regelen

1. **Betaalplatform** — de "Kopen"-knop op AI-detailpagina's linkt nu naar het
   contactformulier. Zodra je Stripe of Mollie hebt, vervang die knop door een
   betaallink (of payment-link per product).
2. **CMS-login** — vul in `admin/config.yml` je eigen OAuth-proxy in (`base_url` +
   `auth_endpoint`), net zoals bij de svanwijksolutions-CMS.
3. **Formulieren** — `js/form.js` is Formspree-ready: zet de juiste `action`-URL op de
   formulieren (contact, concept, updates) zodra je een Formspree-endpoint hebt. Nu tonen
   ze alleen een bevestiging.
4. **EN + DE** — de site is nu volledig in het Nederlands. De taalwisselaar verwijst al
   naar `/eng/` en `/de/`; die versies worden als volgende stap gegenereerd.
5. **GitHub Pages** — repo-instellingen → Pages → deploy from branch / of via de
   meegeleverde `pages.yml` workflow. Custom domain staat al in `CNAME`
   (`www.drivennagency.nl`).
