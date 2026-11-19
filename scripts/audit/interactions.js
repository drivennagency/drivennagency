// Klik-tests van de belangrijkste functies: mobiel menu, taalwissel (naar dezelfde pagina),
// skip-link, actieve menu-item, blog zoeken, FAQ, AI-filter, #updates-anker, formulieren (fout + succes).
// Externe verzoeken (Google, Web3Forms) worden onderschept; er wordt niets echt verstuurd.
// Gebruik: node scripts/audit/interactions.js [basis-URL]   (standaard http://localhost:8123)
const { playwright } = require('./lib');
const B = (process.argv[2] || 'http://localhost:8123').replace(/\/$/, '');
const results = [];
const ok = (name, cond, extra) => results.push(`${cond ? 'OK  ' : 'FOUT'} ${name}${extra ? '  [' + extra + ']' : ''}`);

(async () => {
  const { chromium } = playwright();
  const b = await chromium.launch();
  const errs = [];
  async function ctxWith(opts, formResponse) {
    const ctx = await b.newContext(opts);
    await ctx.addInitScript(() => { try { localStorage.setItem('drivenn-consent', 'denied'); } catch (e) {} });
    await ctx.route(/googletagmanager\.com|google-analytics\.com/, r => r.abort());
    await ctx.route(/api\.web3forms\.com/, r => formResponse(r));
    return ctx;
  }
  const success = r => r.fulfill({ status: 200, contentType: 'application/json', body: '{"success":true}' });
  const failure = r => r.fulfill({ status: 500, contentType: 'application/json', body: '{"success":false}' });
  const watch = p => { p.on('pageerror', e => errs.push(String(e))); p.on('dialog', d => { errs.push('onverwachte pop-up: ' + d.message()); d.dismiss(); }); };

  // Mobiel menu
  let ctx = await ctxWith({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }, success);
  let p = await ctx.newPage(); watch(p);
  await p.goto(B + '/eng/hosting.html');
  await p.click('.nav__burger');
  ok('Mobiel menu opent', await p.$eval('.mobile-overlay', e => e.classList.contains('open')));
  ok('Focus op de sluitknop', await p.evaluate(() => document.activeElement.classList.contains('mobile-overlay__close')));
  for (let i = 0; i < 30; i++) await p.keyboard.press('Tab');
  ok('Focus blijft in het menu', await p.evaluate(() => !!document.activeElement.closest('.mobile-overlay')));
  await p.keyboard.press('Escape');
  ok('Escape sluit het menu en geeft focus terug', !(await p.$eval('.mobile-overlay', e => e.classList.contains('open'))) && await p.evaluate(() => document.activeElement.classList.contains('nav__burger')));
  await ctx.close();

  // Taalwissel, skip-link, actief menu-item, zoeken, FAQ, AI-filter, anker
  ctx = await ctxWith({ viewport: { width: 1366, height: 900 } }, success);
  p = await ctx.newPage(); watch(p);
  for (const [from, lang, to] of [['/hosting.html', 'de', '/de/hosting.html'], ['/eng/blog/seo-basis-mkb.html', 'nl', '/blog/seo-basis-mkb.html'], ['/de/', 'en', '/eng/']]) {
    await p.goto(B + from);
    await p.click('.lang-switch__current');
    await Promise.all([p.waitForNavigation(), p.click(`.lang-switch__menu a[data-lang="${lang}"]`)]);
    ok(`Taalwissel ${from} -> ${lang}`, new URL(p.url()).pathname === to, new URL(p.url()).pathname);
  }
  await p.goto(B + '/eng/blog.html');
  ok('Actief menu-item (aria-current)', (await p.getAttribute('.nav__links a[data-page="blog"]', 'aria-current')) === 'page');
  await p.keyboard.press('Tab');
  ok('Eerste Tab = skip-link', await p.evaluate(() => document.activeElement.classList.contains('skip-link')));
  const first = await p.$eval('[data-blog-card] h3', e => e.textContent.trim().split(/\s+/)[0].toLowerCase());
  await p.fill('#blog-search', first);
  const shown = await p.$$eval('[data-blog-card]', cs => cs.filter(c => c.style.display !== 'none').length);
  ok('Blog zoeken filtert', shown >= 1, `${shown} zichtbaar bij "${first}"`);
  await p.fill('#blog-search', 'zzzqqq');
  ok('Blog: melding bij geen resultaten', await p.$eval('#blog-empty', e => getComputedStyle(e).display !== 'none'));
  await p.goto(B + '/hosting.html');
  const q = await p.$('.faq__q'); await q.click();
  ok('FAQ klapt open (aria-expanded)', (await q.getAttribute('aria-expanded')) === 'true');
  await p.goto(B + '/ai-oplossingen.html');
  await p.click('.ai-chip[data-cat="tekst"]');
  const cats = await p.$$eval('[data-ai-card]', cs => cs.filter(c => c.style.display !== 'none').map(c => c.dataset.cat));
  ok('AI-filter op categorie', cats.length > 0 && cats.every(c => c === 'tekst'), cats.join(','));
  ok('Anker #updates bestaat', !!(await p.$('#updates')));
  await ctx.close();

  // Formulier: fout, dan succes
  let mode = 'fail';
  ctx = await ctxWith({ viewport: { width: 1366, height: 900 } }, r => (mode === 'fail' ? failure : success)(r));
  p = await ctx.newPage(); watch(p);
  await p.goto(B + '/eng/contact.html');
  const form = 'form[data-form]';
  for (const el of await p.$$(`${form} input:not([type=hidden]):not([name=botcheck]), ${form} textarea`)) {
    const t = await el.getAttribute('type');
    if (t === 'email') await el.fill('test@example.com'); else if (t === 'tel') await el.fill('0612345678');
    else if (t === 'checkbox') await el.check(); else await el.fill('Test');
  }
  await p.click(`${form} [type=submit]`); await p.waitForTimeout(600);
  const st = await p.$eval(`${form} .form-status`, e => ({ hidden: e.hidden, text: e.textContent })).catch(() => null);
  ok('Formulier: foutmelding in de pagina, in de juiste taal', st && !st.hidden && /^Something went wrong/.test(st.text), st && st.text.slice(0, 40));
  mode = 'ok';
  await p.click(`${form} [type=submit]`); await p.waitForTimeout(600);
  ok('Formulier: succesmelding na verzenden', await p.$eval('.form-success', e => e.classList.contains('show')));
  await ctx.close();

  await b.close();
  results.forEach(r => console.log(r));
  if (errs.length) errs.forEach(e => console.log('FOUT pagina:', e));
  const failed = results.filter(r => r.startsWith('FOUT')).length + errs.length;
  console.log(`${results.length} klik-tests: ${failed} mislukt.`);
  process.exit(failed ? 1 : 0);
})();
