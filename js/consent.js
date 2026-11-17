/* Drivenn Agency: cookie-toestemming + Google Analytics (NL/EN/DE).
   - Google Consent Mode v2: alles staat standaard op 'geweigerd'.
   - Google Analytics wordt pas geladen nadat de bezoeker akkoord geeft.
   - De keuze is altijd te wijzigen via een element met [data-cookie-settings]
     (de link "Cookie-instellingen" in de footer). */
(function () {
  'use strict';

  var cfg = window.DRIVENN_GA || {};
  var KEY = 'drivenn-consent';
  var lang = (document.documentElement.lang || 'nl').slice(0, 2);
  var gaLoaded = false;
  var banner = null;

  var TEXT = {
    nl: { label: 'Cookievoorkeuren', t: 'We gebruiken cookies om websitebezoek te meten met Google Analytics. Ga je akkoord?', a: 'Accepteren', d: 'Weigeren', p: 'Privacyverklaring', pl: '/privacy.html' },
    en: { label: 'Cookie preferences', t: 'We use cookies to measure website visits with Google Analytics. Do you agree?', a: 'Accept', d: 'Decline', p: 'Privacy policy', pl: '/eng/privacy.html' },
    de: { label: 'Cookie-Einstellungen', t: 'Wir verwenden Cookies, um Website-Besuche mit Google Analytics zu messen. Bist du einverstanden?', a: 'Akzeptieren', d: 'Ablehnen', p: 'Datenschutz', pl: '/de/privacy.html' }
  };
  var x = TEXT[lang] || TEXT.nl;

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = window.gtag || gtag;

  /* Standaard: niets toegestaan tot de bezoeker kiest */
  window.gtag('consent', 'default', {
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
    analytics_storage: 'denied'
  });

  function read() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function write(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  function loadGA() {
    if (gaLoaded || !cfg.id) return;
    gaLoaded = true;
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(cfg.id);
    document.head.appendChild(s);
    window.gtag('js', new Date());
    window.gtag('config', cfg.id, { page_title: cfg.page, site_language: cfg.lang });
  }

  /* Analytics-cookies opruimen wanneer iemand zijn toestemming intrekt */
  function clearGaCookies() {
    var host = location.hostname;
    var domains = ['', host, '.' + host, '.' + host.replace(/^www\./, '')];
    document.cookie.split(';').forEach(function (c) {
      var name = c.split('=')[0].trim();
      if (name.indexOf('_ga') !== 0 && name !== '_gid') return;
      domains.forEach(function (d) {
        document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/' + (d ? '; domain=' + d : '');
      });
    });
  }

  function grant() {
    write('granted');
    window.gtag('consent', 'update', { analytics_storage: 'granted' });
    loadGA();
  }
  function deny() {
    write('denied');
    window.gtag('consent', 'update', { analytics_storage: 'denied' });
    clearGaCookies();
  }

  function closeBanner() {
    var b = banner;
    if (!b) return;
    banner = null;
    b.classList.remove('show');
    setTimeout(function () { if (b.parentNode) b.parentNode.removeChild(b); }, 320);
  }

  function openBanner(focus) {
    if (banner || !document.body) return;
    var b = document.createElement('div');
    b.className = 'cookie-banner';
    b.setAttribute('role', 'region');
    b.setAttribute('aria-label', x.label);
    b.innerHTML =
      '<p class="cookie-banner__txt">' + x.t + ' <a href="' + x.pl + '">' + x.p + '</a></p>' +
      '<div class="cookie-banner__btns">' +
        '<button type="button" class="btn btn--outline cookie-decline">' + x.d + '</button>' +
        '<button type="button" class="btn btn--gold cookie-accept">' + x.a + '</button>' +
      '</div>';
    document.body.appendChild(b);
    banner = b;
    requestAnimationFrame(function () { b.classList.add('show'); });
    b.querySelector('.cookie-accept').addEventListener('click', function () { grant(); closeBanner(); });
    b.querySelector('.cookie-decline').addEventListener('click', function () { deny(); closeBanner(); });
    if (focus) b.querySelector('.cookie-accept').focus();
  }

  /* Keuze opnieuw openen via de footer */
  document.addEventListener('click', function (e) {
    var trigger = e.target && e.target.closest ? e.target.closest('[data-cookie-settings]') : null;
    if (!trigger) return;
    e.preventDefault();
    openBanner(true);
  });

  var state = read();
  if (state === 'granted') { grant(); return; }
  if (state === 'denied') { return; }

  if (document.body) openBanner(false);
  else document.addEventListener('DOMContentLoaded', function () { openBanner(false); });
})();
