/* Cookie-toestemming + Google Analytics (laadt pas na akkoord) — NL/EN/DE */
(function () {
  var cfg = window.DRIVENN_GA || {};
  var KEY = 'drivenn-consent';
  var lang = (document.documentElement.lang || 'nl').slice(0, 2);

  function loadGA() {
    if (!cfg.id) return;
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + cfg.id;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    gtag('js', new Date());
    gtag('config', cfg.id, { page_title: cfg.page, site_language: cfg.lang });
  }

  var state = null;
  try { state = localStorage.getItem(KEY); } catch (e) {}
  if (state === 'granted') { loadGA(); return; }
  if (state === 'denied') { return; }

  var T = {
    nl: { t: 'We gebruiken cookies om websitebezoek te meten met Google Analytics. Ga je akkoord?', a: 'Accepteren', d: 'Weigeren', p: 'Privacyverklaring', pl: '/privacy.html' },
    en: { t: 'We use cookies to measure website visits with Google Analytics. Do you agree?', a: 'Accept', d: 'Decline', p: 'Privacy policy', pl: '/eng/privacy.html' },
    de: { t: 'Wir verwenden Cookies, um Website-Besuche mit Google Analytics zu messen. Bist du einverstanden?', a: 'Akzeptieren', d: 'Ablehnen', p: 'Datenschutz', pl: '/de/privacy.html' }
  };
  var x = T[lang] || T.nl;

  function set(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  function close(b) {
    b.classList.remove('show');
    setTimeout(function () { if (b.parentNode) b.parentNode.removeChild(b); }, 320);
  }

  function build() {
    var b = document.createElement('div');
    b.className = 'cookie-banner';
    b.setAttribute('role', 'dialog');
    b.setAttribute('aria-label', 'Cookies');
    b.innerHTML =
      '<p class="cookie-banner__txt">' + x.t + ' <a href="' + x.pl + '">' + x.p + '</a></p>' +
      '<div class="cookie-banner__btns">' +
        '<button type="button" class="btn btn--outline cookie-decline">' + x.d + '</button>' +
        '<button type="button" class="btn btn--gold cookie-accept">' + x.a + '</button>' +
      '</div>';
    document.body.appendChild(b);
    requestAnimationFrame(function () { b.classList.add('show'); });
    b.querySelector('.cookie-accept').addEventListener('click', function () { set('granted'); loadGA(); close(b); });
    b.querySelector('.cookie-decline').addEventListener('click', function () { set('denied'); close(b); });
  }

  if (document.body) build();
  else document.addEventListener('DOMContentLoaded', build);
})();
