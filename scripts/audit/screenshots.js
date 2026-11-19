// Maakt schermafbeeldingen (volledige pagina) van alle pagina's op desktop en mobiel,
// zonder animaties en met cookiemelding weggeklikt, zodat twee versies pixel voor pixel te vergelijken zijn.
// Gebruik: node scripts/audit/screenshots.js <basis-URL> <uitvoermap>
// Vergelijken: python3 scripts/audit/compare_screenshots.py <map-voor> <map-na>
const fs = require('fs'), path = require('path');
const { pages, playwright } = require('./lib');
const BASE = (process.argv[2] || 'http://localhost:8123').replace(/\/$/, '');
const OUT = process.argv[3];
if (!OUT) { console.error('Gebruik: node scripts/audit/screenshots.js <basis-URL> <uitvoermap>'); process.exit(2); }

(async () => {
  const { chromium } = playwright();
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const list = pages();
  for (const vp of [{ name: 'desktop', width: 1366, height: 900 }, { name: 'mobile', width: 390, height: 844, isMobile: true }]) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, reducedMotion: 'reduce', isMobile: !!vp.isMobile, deviceScaleFactor: 1 });
    await ctx.addInitScript(() => { try { localStorage.setItem('drivenn-consent', 'denied'); } catch (e) {} });
    await ctx.route(/googletagmanager\.com|google-analytics\.com/, r => r.abort());
    for (const rel of list) {
      const page = await ctx.newPage();
      await page.goto(`${BASE}/${rel}`, { waitUntil: 'load' });
      await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important} video{visibility:hidden!important}' });
      // lazy-loaded afbeeldingen laden door de pagina eenmaal door te scrollen
      await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); } window.scrollTo(0, 0); });
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(OUT, `${vp.name}__${rel.replace(/\//g, '__')}.png`), fullPage: true });
      await page.close();
    }
    await ctx.close();
  }
  await browser.close();
  console.log(`${list.length * 2} schermafbeeldingen in ${OUT}`);
})();
