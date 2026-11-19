// Gedeelde hulpfuncties voor de browsertests in scripts/audit/.
const fs = require('fs'), path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const SKIP = new Set(['node_modules', 'components', 'admin', 'scripts', 'tests', 'content', '.git', '.github', '.claude']);

// Alle HTML-pagina's van de site, relatief aan de repo (bv. "eng/blog.html").
function pages(root = ROOT) {
  const out = [];
  (function walk(d) {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      if (e.name.startsWith('.') || SKIP.has(e.name)) continue;
      const f = path.join(d, e.name);
      if (e.isDirectory()) walk(f);
      else if (e.name.endsWith('.html')) out.push(path.relative(root, f).split(path.sep).join('/'));
    }
  })(root);
  return out.sort();
}

// "eng/index.html" -> "/eng/"
function urlPath(rel) {
  return '/' + rel.replace(/(^|\/)index\.html$/, '$1');
}

// Playwright laden; in Claude-cloudsessies is het al geïnstalleerd.
function playwright() {
  try { return require('playwright'); } catch (e) {
    console.error('Playwright ontbreekt. Installeer het met: npm install playwright && npx playwright install chromium');
    process.exit(2);
  }
}

// Gegevens uit een Google Analytics-meetverzoek (URL + eventuele POST-body met meerdere events).
function parseGaHit(url, body) {
  const u = new URL(url);
  const events = [u.searchParams.get('en')]
    .concat((body || '').split('\n').map(l => (l.match(/(?:^|&)en=([^&]+)/) || [])[1]))
    .filter(Boolean);
  let page = null;
  try { page = new URL(u.searchParams.get('dl')).pathname; } catch (e) { /* geen dl */ }
  return { tid: u.searchParams.get('tid'), gcs: u.searchParams.get('gcs'), page, title: u.searchParams.get('dt'), events,
    params: [...u.searchParams.keys()].filter(k => k.startsWith('ep.')).map(k => `${k}=${u.searchParams.get(k)}`) };
}

// Regex voor alle Google Analytics/advertentie-eindpunten die we onderscheppen (nooit echt versturen).
const GA_HIT = /\/g\/collect|google\.com\/ccm|doubleclick\.net|googleadservices\.com|\/pagead\//;

module.exports = { ROOT, pages, urlPath, playwright, parseGaHit, GA_HIT };
