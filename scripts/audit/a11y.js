// Toegankelijkheidstest met axe-core op alle pagina's (WCAG 2 AA): kleurcontrast, labels, alt-teksten,
// koppen, linknamen, taal, landmarks.
// Vereist axe-core:  npm install --prefix <map> axe-core@4.10.3   en dan  AXE_DIR=<map> node scripts/audit/a11y.js
// Gebruik: node scripts/audit/a11y.js [basis-URL]   (standaard http://localhost:8123)
// Exitcode 1 bij ernstige meldingen (alles behalve 'heading-order', dat alleen gemeld wordt).
const fs = require('fs'), path = require('path');
const { pages, playwright } = require('./lib');
const BASE = (process.argv[2] || 'http://localhost:8123').replace(/\/$/, '');

let axeSource;
try {
  const dir = process.env.AXE_DIR ? path.join(process.env.AXE_DIR, 'node_modules', 'axe-core') : path.dirname(require.resolve('axe-core'));
  axeSource = fs.readFileSync(path.join(dir, 'axe.min.js'), 'utf8');
} catch (e) {
  console.error('axe-core niet gevonden. Installeer: npm install --prefix /tmp/audit-deps axe-core@4.10.3 en zet AXE_DIR=/tmp/audit-deps');
  process.exit(2);
}

const RULES = ['color-contrast', 'heading-order', 'link-name', 'image-alt', 'label', 'button-name', 'document-title',
  'html-has-lang', 'html-lang-valid', 'landmark-one-main', 'list', 'listitem', 'duplicate-id-aria', 'aria-valid-attr',
  'aria-required-attr', 'frame-title', 'input-image-alt', 'select-name'];
const SOFT = new Set(['heading-order']);

(async () => {
  const { chromium } = playwright();
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, reducedMotion: 'reduce' });
  await ctx.addInitScript(() => { try { localStorage.setItem('drivenn-consent', 'denied'); } catch (e) {} });
  await ctx.route(/googletagmanager\.com|google-analytics\.com/, r => r.abort());
  const agg = new Map();
  const list = pages();
  for (const rel of list) {
    const page = await ctx.newPage();
    await page.goto(`${BASE}/${rel}`, { waitUntil: 'load' });
    await page.addScriptTag({ content: axeSource });
    const violations = await page.evaluate(async rules => (await axe.run(document, { runOnly: rules })).violations
      .map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target.join(' ') + ' :: ' + ((n.any[0] || n.all[0] || {}).message || '').slice(0, 140)) })), RULES);
    for (const v of violations) for (const n of v.nodes) {
      const key = `${v.id} | ${n.replace(/\d+(\.\d+)?/g, '#')}`;
      if (!agg.has(key)) agg.set(key, { id: v.id, pages: [] });
      agg.get(key).pages.push(rel);
    }
    await page.close();
  }
  await browser.close();
  const rows = [...agg.entries()].sort((a, b) => b[1].pages.length - a[1].pages.length);
  let hard = 0;
  for (const [key, v] of rows) {
    const soft = SOFT.has(v.id);
    if (!soft) hard += v.pages.length;
    console.log(`${soft ? 'INFO' : 'FOUT'} ${v.pages.length}x ${key}  (bv. ${v.pages[0]})`);
  }
  const total = rows.reduce((s, [, v]) => s + v.pages.length, 0);
  console.log(`${list.length} pagina's getest met axe-core: ${total} melding(en), waarvan ${hard} ernstig.`);
  process.exit(hard ? 1 : 0);
})();
