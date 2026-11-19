// Controleert Google Analytics 4 + Consent Mode met de ECHTE Google-tag.
// VEILIG: elk meetverzoek naar Google wordt onderschept en beantwoord met 204, er komt dus nooit
// testdata in Google Analytics terecht. Formulieren naar Web3Forms worden ook onderschept.
//
// Gebruik: node scripts/audit/analytics.js [basis-URL]   (standaard https://www.drivennagency.nl)
//
// Controleert:
//  1. zonder keuze: alleen 'consent default' (alles denied), geen gtag.js, geen meetverzoeken
//  2. accepteren: gtag.js met het juiste meet-ID, page_view met gcs=G101 (statistiek aan, advertenties uit)
//  3. volgende pagina: keuze onthouden, page_view met de juiste taal (ep.site_language)
//  4. contactformulier: form_start + generate_lead, en GEEN e-mailadres/telefoonnummer naar Google
//  5. weigeren: geen gtag.js, geen meetverzoeken, geen _ga-cookies
//  6. intrekken via 'Cookie-instellingen': _ga-cookies worden verwijderd
const { playwright, parseGaHit, GA_HIT } = require('./lib');
const BASE = (process.argv[2] || 'https://www.drivennagency.nl').replace(/\/$/, '');
const GA_ID = 'G-4VXJQRECQ6';
const EMAIL = 'audit-test@voorbeeld.invalid', PHONE = '0612345678';

const results = [];
const check = (name, ok, detail) => results.push({ name, ok: !!ok, detail });

async function newContext(browser, consent) {
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, locale: 'nl-NL' });
  if (consent) await ctx.addInitScript(c => { try { localStorage.setItem('drivenn-consent', c); } catch (e) {} }, consent);
  const hits = [], tags = [];
  await ctx.route(GA_HIT, r => { hits.push({ url: r.request().url(), body: r.request().postData() || '' }); r.fulfill({ status: 204, body: '' }); });
  await ctx.route(/api\.web3forms\.com/, r => r.fulfill({ status: 200, contentType: 'application/json', body: '{"success":true}' }));
  ctx.on('request', r => { if (r.url().includes('googletagmanager.com/gtag/js')) tags.push(r.url()); });
  return { ctx, hits, tags };
}

async function waitFor(fn, ms = 12000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { if (await fn()) return true; await new Promise(r => setTimeout(r, 150)); }
  return false;
}

(async () => {
  const { chromium } = playwright();
  const browser = await chromium.launch();
  const errors = [];

  // 1 + 2 + 3: geen keuze -> accepteren -> volgende pagina
  {
    const { ctx, hits, tags } = await newContext(browser, null);
    const p = await ctx.newPage();
    p.on('pageerror', e => errors.push(String(e)));
    await p.goto(BASE + '/', { waitUntil: 'networkidle' });
    const dl = await p.evaluate(() => (window.dataLayer || []).map(a => Array.from(a)));
    const def = dl.find(a => a[0] === 'consent' && a[1] === 'default');
    check('Consent Mode v2: standaard alles geweigerd',
      def && ['ad_storage', 'ad_user_data', 'ad_personalization', 'analytics_storage'].every(k => def[2][k] === 'denied'), JSON.stringify(def && def[2]));
    check('Zonder keuze: geen Google-tag en geen meetverzoeken', tags.length === 0 && hits.length === 0, `tag ${tags.length}, hits ${hits.length}`);
    check('Cookiemelding zichtbaar', !!(await p.$('.cookie-banner')));

    await p.click('.cookie-accept');
    await waitFor(() => hits.some(h => parseGaHit(h.url, h.body).events.includes('page_view')));
    check('Na accepteren: Google-tag geladen met juist meet-ID', tags.some(t => t.includes(GA_ID)), tags[0]);
    const pv = hits.map(h => parseGaHit(h.url, h.body)).find(h => h.events.includes('page_view'));
    check('Na accepteren: page_view verstuurd', !!pv, pv && `${pv.page} "${pv.title}"`);
    check('Toestemmingsstatus gcs=G101 (statistiek aan, advertenties uit)', pv && pv.gcs === 'G101', pv && pv.gcs);

    const n0 = hits.length;
    await p.goto(BASE + '/eng/blog.html', { waitUntil: 'load' });
    const got = await waitFor(() => hits.slice(n0).some(h => parseGaHit(h.url, h.body).events.includes('page_view')));
    const pv2 = hits.slice(n0).map(h => parseGaHit(h.url, h.body)).find(h => h.events.includes('page_view'));
    check('Volgende pagina: keuze onthouden, page_view verstuurd', got, pv2 && pv2.page);
    check('Taal meegestuurd (site_language=en)', pv2 && pv2.params.includes('ep.site_language=en'), pv2 && pv2.params.join(' '));
    await ctx.close();
  }

  // 4: contactformulier met akkoord
  {
    const { ctx, hits } = await newContext(browser, 'granted');
    const p = await ctx.newPage();
    p.on('pageerror', e => errors.push(String(e)));
    await p.goto(BASE + '/contact.html', { waitUntil: 'load' });
    await waitFor(() => hits.length > 0);
    const form = 'form[data-form]';
    for (const el of await p.$$(`${form} input:not([type=hidden]):not([name=botcheck]), ${form} textarea, ${form} select`)) {
      const type = await el.getAttribute('type'); const tag = await el.evaluate(e => e.tagName);
      if (tag === 'SELECT') await el.selectOption({ index: 1 }).catch(() => {});
      else if (type === 'email') await el.fill(EMAIL);
      else if (type === 'tel') await el.fill(PHONE);
      else if (type === 'checkbox') await el.check();
      else await el.fill('Audit test');
    }
    await p.click(`${form} [type=submit]`);
    await waitFor(() => hits.some(h => parseGaHit(h.url, h.body).events.includes('generate_lead')), 10000);
    await p.goto('about:blank'); await new Promise(r => setTimeout(r, 1000));
    const events = new Set(hits.flatMap(h => parseGaHit(h.url, h.body).events));
    check('Formulier: form_start gemeten', events.has('form_start'), [...events].join(','));
    check('Formulier: generate_lead gemeten (aanvraag)', events.has('generate_lead'), [...events].join(','));
    const all = hits.map(h => decodeURIComponent(h.url) + '\n' + decodeURIComponent(h.body)).join('\n');
    const leaks = [EMAIL, PHONE, 'voorbeeld.invalid'].filter(s => all.includes(s))
      .concat(['&em=', '?em=', '&ph=', '&tu=', 'ecid='].filter(s => all.includes(s)));
    check('Geen e-mailadres/telefoonnummer of gebruikersgegevens naar Google', leaks.length === 0, leaks.join(', ') || 'niets gevonden');
    await ctx.close();
  }

  // 5 + 6: weigeren en intrekken
  {
    const { ctx, hits, tags } = await newContext(browser, null);
    const p = await ctx.newPage();
    await p.goto(BASE + '/de/', { waitUntil: 'networkidle' });
    await p.click('.cookie-decline'); await p.waitForTimeout(1500);
    await p.goto(BASE + '/de/blog.html', { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
    const cookies = (await ctx.cookies()).map(c => c.name).filter(n => n.startsWith('_ga'));
    check('Na weigeren: geen Google-tag, geen meetverzoeken, geen _ga-cookies', tags.length === 0 && hits.length === 0 && cookies.length === 0,
      `tag ${tags.length}, hits ${hits.length}, cookies ${cookies.join(',') || '-'}`);
    await ctx.close();

    const c2 = await newContext(browser, 'granted');
    const p2 = await c2.ctx.newPage();
    await p2.goto(BASE + '/', { waitUntil: 'load' });
    await waitFor(async () => (await c2.ctx.cookies()).some(c => c.name.startsWith('_ga')));
    const before = (await c2.ctx.cookies()).filter(c => c.name.startsWith('_ga')).length;
    await p2.click('footer [data-cookie-settings]');
    await p2.click('.cookie-decline'); await p2.waitForTimeout(800);
    const after = (await c2.ctx.cookies()).filter(c => c.name.startsWith('_ga')).length;
    check('Intrekken via Cookie-instellingen verwijdert de _ga-cookies', before > 0 && after === 0, `voor ${before}, na ${after}`);
    await c2.ctx.close();
  }

  await browser.close();
  check('Geen JavaScript-fouten', errors.length === 0, errors.slice(0, 3).join(' | '));
  for (const r of results) console.log(`${r.ok ? 'OK  ' : 'FOUT'} ${r.name}${r.detail ? '  [' + r.detail + ']' : ''}`);
  const failed = results.filter(r => !r.ok).length;
  console.log(`${results.length} Analytics-controles op ${BASE}: ${failed} mislukt. (Er is niets naar Google verstuurd.)`);
  process.exit(failed ? 1 : 0);
})();
