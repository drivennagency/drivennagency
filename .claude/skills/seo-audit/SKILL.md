---
name: seo-audit
description: Volledige SEO-, Search Console- en Google Analytics-audit van drivennagency.nl volgens de actuele richtlijnen van Google. Gebruik bij "/seo-audit", of als de gebruiker vraagt of de site goed vindbaar is, goed geïndexeerd kan worden, of Google Analytics/Search Console officieel goed werken.
---

# SEO-audit voor drivennagency.nl

Doel: aantonen (met metingen, niet met aannames) dat de website voldoet aan de actuele richtlijnen van
Google Search, goed geïndexeerd kan worden, en dat Google Analytics 4 met Consent Mode correct en
AVG-proof werkt. Rapporteer in het Nederlands, zonder Engelse vaktermen waar een gewoon woord kan.

## Veiligheidsregels (altijd)

- **Nooit testdata naar Google Analytics sturen.** Alle browsertests onderscheppen meetverzoeken
  (`scripts/audit/analytics.js` beantwoordt ze met 204). Schrijf geen eigen test die de echte
  `/g/collect` bereikt.
- **Nooit rechtstreeks naar `main`.** Verbeteringen gaan via een branch en een pull request die de
  gebruiker zelf beoordeelt en merget. Nooit force-pushen.
- **Geen content verwijderen** en geen live URL's wijzigen zonder uitdrukkelijk akkoord van de gebruiker.
- **Niets verzinnen** in structured data of de privacyverklaring (geen adres, retourbeleid, btw-nummer,
  reviews of beoordelingen die niet echt bestaan). Ontbreekt een gegeven: vraag het de gebruiker.
- Meld eerlijk wat je niet kon controleren (bijv. velddata van echte bezoekers, Search Console-rapporten
  waar je geen toegang toe hebt).

## Stap 1: richtlijnen actueel houden

De richtlijnen veranderen. Lees vóór de audit het updatelog en verwerk nieuwe punten in de controle:
- https://developers.google.com/search/updates (alle wijzigingen sinds de vorige audit)
- https://developers.google.com/search/docs/fundamentals/ai-optimization-guide (AI Overviews / AI Mode)
- https://developers.google.com/tag-platform/security/guides/consent (Consent Mode)

Noem in het rapport welke recente wijzigingen relevant waren. Stand bij het maken van deze skill
(november 2026): FAQ-rich-results bestaan niet meer sinds 7 mei 2026 (markup mag blijven; Bing gebruikt
het); Google gebruikt `og:image` en schema.org-`image`/`primaryImageOfPage` als voorkeursafbeelding;
URL's met streepjes; llms.txt en speciale "AI-markup" zijn voor Google niet nodig.

## Stap 2: voorbereiden

```bash
# Lokale kopie van de huidige branch serveren (zoals Vercel)
node scripts/audit/server.js . 8123 &

# Hulppakketten in een tijdelijke map (NIET in de repo)
DEPS="$(mktemp -d)"; npm install --prefix "$DEPS" axe-core@4.10.3 lighthouse@12 >/dev/null
python3 -m venv "$DEPS/venv" && "$DEPS/venv/bin/pip" install -q pillow numpy
```
Playwright en Chromium zijn in Claude-cloudsessies al geïnstalleerd (`require('playwright')`). Voor
Lighthouse: `CHROME_PATH=/opt/pw-browsers/chromium` en `--chrome-flags="--headless=new --no-sandbox"`.

## Stap 3: geautomatiseerde controles

Voer ze allemaal uit; bij elke fout eerst de oorzaak vaststellen voordat je iets aanpast.

| # | Commando | Wat het bewijst | Moet |
|---|---|---|---|
| 1 | `python3 scripts/build_content.py --check` | gegenereerde pagina's zijn up-to-date | "Alles is up-to-date" |
| 2 | `python3 scripts/check_site.py` | links, ankers, titels, descriptions, canonical, wederkerige hreflang, og-tags, JSON-LD, FAQ zichtbaar, sitemap | 0 fouten |
| 3 | `python3 -m unittest discover -s tests` en `node --test tests/*.test.js` | build-script en API's | alles OK |
| 4 | `python3 scripts/audit/googlebot_crawl.py` (live) en `... http://localhost:8123` | elke sitemap-URL als Googlebot Smartphone: 200, canonical, geen noindex, robots.txt, 404's, redirects | 0 fouten |
| 5 | `python3 scripts/audit/validate_schema.py` en `--live` | structured data geldig volgens schema.org | 0 fouten |
| 6 | `node scripts/audit/pages.js` | geen JS-fouten, kapotte bestanden of horizontaal scrollen (desktop + mobiel) | 0 problemen |
| 7 | `AXE_DIR="$DEPS" node scripts/audit/a11y.js` | toegankelijkheid (WCAG AA): contrast, labels, alt, koppen | 0 ernstig |
| 8 | `node scripts/audit/interactions.js` | menu, taalwissel, skip-link, zoeken, FAQ, filter, formulieren | alles OK |
| 9 | `node scripts/audit/analytics.js` (live) | GA4 + Consent Mode: niets vóór toestemming, page_view met gcs=G101, form_start/generate_lead, geen e-mail/telefoon naar Google, weigeren/intrekken werkt | alles OK |
| 10 | Lighthouse mobiel op `/`, een blog, een AI-pagina, `/blog.html`, `/concept.html` (live) | Core Web Vitals (lab) en categoriescores | SEO 100, toegankelijkheid ≥ 95, best practices ≥ 95; LCP < 2,5 s, CLS < 0,1, TBT < 200 ms |
| 11 | `node scripts/audit/screenshots.js` vóór en na een wijziging + `"$DEPS/venv/bin/python" scripts/audit/compare_screenshots.py voor na` | opmaak niet onbedoeld veranderd | verschillen verklaard |

Let op bij #5: validator.schema.org begrenst het aantal verzoeken (HTTP 429/405). Het script wacht en
probeert opnieuw; een pagina met "??" is niet gecontroleerd. Draai die later los opnieuw
(`python3 scripts/audit/validate_schema.py <pad>`) in plaats van hem als goedgekeurd te melden.

Lighthouse-voorbeeld:
```bash
CHROME_PATH=/opt/pw-browsers/chromium "$DEPS/node_modules/.bin/lighthouse" https://www.drivennagency.nl/ \
  --quiet --chrome-flags="--headless=new --no-sandbox" --output=json --output-path="$DEPS/lh.json" \
  --only-categories=performance,accessibility,best-practices,seo
```
Lighthouse simuleert een trage telefoon; meld naast de score ook de werkelijk gemeten tijden
(`metrics.observedLargestContentfulPaint`). Echte bezoekersdata (CrUX) staat in Search Console en in
PageSpeed Insights (heeft een dagquotum).

## Stap 4: controlelijst (handmatig nalopen, met bron)

**Indexering (Search Essentials, technische eisen)**
- Googlebot niet geblokkeerd (robots.txt, geen login), pagina's geven 200, indexeerbare tekst in HTML.
- Eén URL per stuk content; varianten (`/index.html`, zonder www, http) permanent doorverwezen.
- Sitemap: alleen canonieke, indexeerbare URL's; absolute URL's; `lastmod` alleen als die klopt.
- `noindex` alleen op bewuste pagina's (privacy, bedankt, 404) en die staan niet in de sitemap.

**Titels en snippets** (title-link, snippet)
- Unieke, beschrijvende `<title>` per pagina en taal; merknaam aan het eind; geen keyword-stuffing.
- Unieke meta description per pagina; zichtbare `<h1>` die bij de titel past.

**Meertaligheid** (localized-versions)
- `hreflang` voor nl/en/de + `x-default`, absolute URL's, naar zichzelf én wederkerig; `<html lang>` klopt.
- Taalwisselaar linkt naar dezelfde pagina in de andere taal; geen automatische redirect op IP.
- Open punt (beslissing gebruiker): Engelse/Duitse URL's gebruiken nog Nederlandse woorden
  (`/eng/nieuwe-website.html`). Google raadt woorden in de taal van de bezoeker aan. Alleen wijzigen
  met akkoord én 301-redirects.

**Structured data** (sd-policies, organization, article, breadcrumb, site-names, product-snippet)
- Alleen markup voor zichtbare inhoud; meest specifieke types; `@id`-koppelingen kloppen.
- WebSite (sitenaam) alleen op de hoofd-homepage. Organization/ProfessionalService op de homepages.
- Per pagina een WebPage-node met `inLanguage`, `isPartOf`, `primaryImageOfPage`, `breadcrumb`.
- BlogPosting: headline, image (ImageObject), datePublished/dateModified met tijdzone, author, publisher.
- Product (AI-oplossingen): naam, afbeelding, offers met prijs/valuta/beschikbaarheid. Search Console kan
  aanbevolen velden missen (retourbeleid, verzending): alleen invullen met echte gegevens van de gebruiker.

**Afbeeldingen** (google-images)
- Belangrijke afbeeldingen als `<img>` (niet als CSS-achtergrond), met beschrijvende alt-tekst,
  `width`/`height`, WebP-variant via `scripts/optimize_images.py`, `og:image` per pagina.

**Links**: beschrijvende linkteksten (geen "klik hier"/"meer info"), geen kapotte interne links,
externe links met `rel="noopener"`.

**Page experience**: HTTPS, mobielvriendelijk, geen hinderlijke pop-ups (cookiemelding is klein en
onderaan), Core Web Vitals goed (LCP < 2,5 s, INP < 200 ms, CLS < 0,1).

**AI Overviews / AI Mode**: geen extra eisen; pagina's moeten geïndexeerd en snippet-geschikt zijn
(geen `nosnippet`); structured data moet overeenkomen met zichtbare tekst.

**Google Analytics 4 en privacy** (GA-voorwaarden sectie 7, Consent Mode v2)
- `consent default` (alle vier denied) vóór elke meting; update bij keuze; keuze onthouden;
  intrekken mogelijk via "Cookie-instellingen" (footer en privacyverklaring).
- Geen persoonsgegevens (e-mail, telefoon) naar Google.
- Privacyverklaring (nl/en/de) noemt: gebruik van GA en de cookies, link naar
  https://policies.google.com/technologies/partner-sites, intrekken, verwerkers (Vercel, Web3Forms),
  klachtrecht. Controleer dat de tekst nog klopt met wat de code doet.
- Bekend gedrag (nov. 2026): in de geautomatiseerde testbrowser stuurt de Google-tag de page_view op
  vervolgpagina's pas na ±5 s. Google's eigen standaardsnippet doet in dezelfde test precies hetzelfde,
  dus het is geen fout in onze code; de gebruiker controleert het in GA4 → Realtime.

**Instellingen die alleen de gebruiker kan doen** (noem ze in het rapport als ze nog openstaan)
- Search Console: sitemap ingediend, Pagina-indexering zonder onverwachte uitsluitingen, Verbeteringen
  (kruimelpaden, producten) zonder fouten, opname in generatieve AI-functies aan.
- GA4: "door gebruikers verstrekte gegevens (automatische detectie)" uit (alleen nodig voor Google Ads);
  `generate_lead` als belangrijke gebeurtenis; bewaartermijn bewust gekozen.
- Google Bedrijfsprofiel en Bing Webmaster Tools (import uit Search Console).

## Stap 5: rapport

Kort en concreet, in deze volgorde:
1. **Conclusie** in één of twee zinnen (voldoet de site, en wat is het belangrijkste open punt).
2. **Gemeten**: per controle uit stap 3 de uitkomst (aantallen, scores).
3. **Gevonden problemen**, ernstigste eerst, elk met: wat, waar, waarom het telt (met bron), voorstel.
4. **Wat alleen de gebruiker kan doen** (instellingen in Search Console/GA4 e.d.).
5. **Niet kunnen controleren**, en waarom.
6. **Bronnen** als klikbare links.

## Stap 6: verbeteren (alleen als de gebruiker dat wil)

- Werk op een branch; pas bronnen aan (componenten, `content/`, `scripts/build_content.py`, CSS/JS),
  niet de gegenereerde HTML, en bouw opnieuw met `python3 scripts/build_content.py`.
- Draai daarna alle controles uit stap 3 opnieuw, inclusief schermafbeeldingen vóór/na, en verklaar
  elk visueel verschil.
- Commit met een duidelijke Nederlandse beschrijving, push de branch en bied een pull request aan.
