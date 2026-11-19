// Opent elke pagina op desktop (1366px) en mobiel (390px) en meldt:
// JavaScript-fouten, bestanden die niet laden (4xx/5xx), kapotte afbeeldingen en horizontaal scrollen.
// Gebruik: node scripts/audit/pages.js [basis-URL]   (standaard http://localhost:8123)
const { pages, playwright } = require('./lib');
const BASE = (process.argv[2] || 'http://localhost:8123').replace(/\/$/, '');

(async () => {
  const { chromium } = playwright();
  const browser = await chromium.launch();
  const list = pages();
  const problems = [];
  for (const vp of [{ name: 'desktop', width: 1366, height: 900 }, { name: 'mobiel', width: 390, height: 844, isMobile: true, hasTouch: true }]) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.isMobile, hasTouch: !!vp.hasTouch });
    // Externe meetverzoeken nooit echt versturen.
    await ctx.route(/googletagmanager\.com|google-analytics\.com|api\.web3forms\.com/, r => r.abort());
    for (const rel of list) {
      const page = await ctx.newPage();
      const issues = [];
      page.on('pageerror', e => issues.push('JS-fout: ' + String(e).slice(0, 200)));
      page.on('console', m => { if (m.type() === 'error' && !/ERR_FAILED|net::/.test(m.text())) issues.push('console: ' + m.text().slice(0, 200)); });
      page.on('response', r => { if (r.url().startsWith(BASE) && r.status() >= 400 && !r.request().isNavigationRequest()) issues.push(`HTTP ${r.status()}: ${r.url().replace(BASE, '')}`); });
      const res = await page.goto(`${BASE}/${rel}`, { waitUntil: 'load' });
      const expect404 = rel.endsWith('404.html');
      if (!res || (res.status() !== 200 && !expect404)) issues.push(`pagina gaf status ${res && res.status()}`);
      await page.waitForTimeout(200);
      const data = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth - window.innerWidth,
        broken: [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.loading !== 'lazy').map(i => i.getAttribute('src')),
      }));
      if (data.overflow > 1) issues.push(`horizontaal scrollen (+${data.overflow}px)`);
      data.broken.forEach(src => issues.push('afbeelding laadt niet: ' + src));
      issues.forEach(i => problems.push(`${vp.name} ${rel}: ${i}`));
      await page.close();
    }
    await ctx.close();
  }
  await browser.close();
  problems.forEach(p => console.log('FOUT', p));
  console.log(`${list.length} pagina's x 2 schermformaten gecontroleerd: ${problems.length} probleem/problemen.`);
  process.exit(problems.length ? 1 : 0);
})();
