/* Drivenn Agency: gedrag van de website (menu, taalwissel, animaties, zoeken en filters).
   Elk onderdeel staat in een eigen functie en doet niets als de bijbehorende
   elementen niet op de pagina staan. Zonder JavaScript blijft alle inhoud leesbaar. */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var locale = { nl: 'nl-NL', en: 'en-GB', de: 'de-DE' }[(document.documentElement.lang || 'nl').slice(0, 2)] || 'nl-NL';

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  /* Jaartal in de footer */
  function initYear() {
    var y = document.getElementById('year');
    if (y) y.textContent = new Date().getFullYear();
  }

  /* Header krijgt een achtergrond zodra er gescrold is */
  function initStickyHeader() {
    var header = document.getElementById('site-header');
    if (!header) return;
    function onScroll() { header.classList.toggle('scrolled', window.scrollY > 40); }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* Mobiel menu: focus blijft binnen het menu, Escape sluit, focus gaat terug naar de knop */
  function initMobileMenu() {
    var burger = $('.nav__burger');
    var overlay = $('.mobile-overlay');
    if (!burger || !overlay) return;
    var closeBtn = $('.mobile-overlay__close', overlay);

    function isOpen() { return overlay.classList.contains('open'); }
    function open() {
      overlay.classList.add('open');
      burger.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
      if (closeBtn) closeBtn.focus();
    }
    function close(restoreFocus) {
      if (!isOpen()) return;
      overlay.classList.remove('open');
      burger.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
      if (restoreFocus) burger.focus();
    }

    burger.addEventListener('click', open);
    if (closeBtn) closeBtn.addEventListener('click', function () { close(true); });
    $$('a', overlay).forEach(function (a) { a.addEventListener('click', function () { close(false); }); });

    document.addEventListener('keydown', function (e) {
      if (!isOpen()) return;
      if (e.key === 'Escape') { close(true); return; }
      if (e.key !== 'Tab') return;
      var items = $$('a[href], button:not([disabled])', overlay);
      if (!items.length) return;
      var first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });

    /* Wordt het scherm breder dan het mobiele menu, dan mag de pagina weer scrollen */
    window.addEventListener('resize', function () {
      if (isOpen() && window.getComputedStyle(burger).display === 'none') close(false);
    });
  }

  /* Taalwisselaar */
  function initLanguageSwitch() {
    var wrap = $('.lang-switch');
    if (!wrap) return;
    var btn = $('.lang-switch__current', wrap);
    if (!btn) return;

    function set(open) {
      wrap.classList.toggle('open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      set(!wrap.classList.contains('open'));
    });
    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) set(false);
    });
    wrap.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && wrap.classList.contains('open')) { set(false); btn.focus(); }
    });
    wrap.addEventListener('focusout', function (e) {
      if (e.relatedTarget && !wrap.contains(e.relatedTarget)) set(false);
    });
  }

  /* Inhoud rustig laten verschijnen bij scrollen (zonder JS is alles gewoon zichtbaar) */
  function initReveal() {
    if (reduceMotion || !('IntersectionObserver' in window)) return;
    var items = $$('.reveal');
    if (!items.length) return;
    document.body.classList.add('js-motion');
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    items.forEach(function (el) { io.observe(el); });
  }

  /* Hero-video pas laden na 'load', zodat hij nooit concurreert met de grootste afbeelding (LCP) */
  function initHeroVideo() {
    var v = $('.hero__bg-video');
    if (!v) return;
    var conn = navigator.connection;
    if (reduceMotion || (conn && conn.saveData)) return;   // poster blijft staan
    function start() {
      var sources = $$('source[data-src]', v);
      if (sources.length) sources.forEach(function (s) { s.src = s.dataset.src; });
      else if (v.dataset.src) v.src = v.dataset.src;
      else return;
      v.load();
      var p = v.play();
      if (p && p.catch) p.catch(function () {});
    }
    if (document.readyState === 'complete') start();
    else window.addEventListener('load', start);
  }

  /* Cijfers in de hero tellen op zodra ze in beeld komen */
  function initCounters() {
    var nums = $$('.hero__stat .n[data-count]');
    if (!nums.length) return;

    function text(el, value) {
      return (el.getAttribute('data-prefix') || '') + value.toLocaleString(locale) + (el.getAttribute('data-suffix') || '');
    }
    function finish(el) { el.textContent = text(el, parseFloat(el.getAttribute('data-count'))); }
    function run(el) {
      var target = parseFloat(el.getAttribute('data-count'));
      var from = parseFloat(el.getAttribute('data-start') || '0');
      var duration = 2000, t0 = null;
      function step(ts) {
        if (t0 === null) t0 = ts;
        var p = Math.min((ts - t0) / duration, 1);
        var eased = 1 - Math.pow(1 - p, 3);
        el.textContent = text(el, Math.round(from + (target - from) * eased));
        if (p < 1) requestAnimationFrame(step); else finish(el);
      }
      requestAnimationFrame(step);
    }

    if (reduceMotion || !('IntersectionObserver' in window)) { nums.forEach(finish); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { run(en.target); io.unobserve(en.target); }
      });
    }, { threshold: 0.3 });
    nums.forEach(function (el) { io.observe(el); });
  }

  /* Lopende band met logo's: tweede kopie voor een naadloze lus (verborgen voor schermlezers) */
  function initMarquee() {
    $$('.marquee').forEach(function (m) {
      var track = $('.marquee__track', m);
      if (!track) return;
      var copy = track.cloneNode(true);
      copy.setAttribute('aria-hidden', 'true');
      m.appendChild(copy);
    });
  }

  /* Veelgestelde vragen */
  function initFaq() {
    $$('.faq__q').forEach(function (q, i) {
      var item = q.closest('.faq__item');
      var a = item && $('.faq__a', item);
      if (!a) return;
      if (!a.id) a.id = 'faq-a-' + (i + 1);
      q.setAttribute('aria-controls', a.id);
      q.setAttribute('aria-expanded', item.classList.contains('open') ? 'true' : 'false');
      q.addEventListener('click', function () {
        var open = item.classList.toggle('open');
        q.setAttribute('aria-expanded', open ? 'true' : 'false');
        a.style.maxHeight = open ? a.scrollHeight + 'px' : '0';
      });
    });
    window.addEventListener('resize', function () {
      $$('.faq__item.open .faq__a').forEach(function (a) { a.style.maxHeight = a.scrollHeight + 'px'; });
    });
  }

  /* Zoeken in de blogs */
  function initBlogSearch() {
    var input = document.getElementById('blog-search');
    if (!input) return;
    var cards = $$('[data-blog-card]');
    var empty = document.getElementById('blog-empty');
    input.addEventListener('input', function () {
      var q = input.value.toLowerCase().trim();
      var shown = 0;
      cards.forEach(function (c) {
        var hit = (c.getAttribute('data-search') || '').indexOf(q) !== -1;
        c.style.display = hit ? '' : 'none';
        if (hit) shown++;
      });
      if (empty) empty.style.display = shown ? 'none' : 'block';
    });
  }

  /* AI-catalogus: zoeken + filteren op categorie */
  function initAiCatalog() {
    var cards = $$('[data-ai-card]');
    if (!cards.length) return;
    var input = document.getElementById('ai-search');
    var chips = $$('.ai-chip');
    var empty = document.getElementById('ai-empty');
    var category = 'all';

    function filter() {
      var q = input ? input.value.toLowerCase().trim() : '';
      var shown = 0;
      cards.forEach(function (c) {
        var ok = (!q || (c.getAttribute('data-search') || '').indexOf(q) !== -1) &&
                 (category === 'all' || c.getAttribute('data-cat') === category);
        c.style.display = ok ? '' : 'none';
        if (ok) shown++;
      });
      if (empty) empty.style.display = shown ? 'none' : 'block';
    }

    if (input) input.addEventListener('input', filter);
    chips.forEach(function (chip) {
      chip.setAttribute('aria-pressed', chip.classList.contains('active') ? 'true' : 'false');
      chip.addEventListener('click', function () {
        chips.forEach(function (c) { c.classList.remove('active'); c.setAttribute('aria-pressed', 'false'); });
        chip.classList.add('active');
        chip.setAttribute('aria-pressed', 'true');
        category = chip.getAttribute('data-cat');
        filter();
      });
    });
  }

  ready(function () {
    [initYear, initStickyHeader, initMobileMenu, initLanguageSwitch, initReveal, initHeroVideo,
     initCounters, initMarquee, initFaq, initBlogSearch, initAiCatalog].forEach(function (init) {
      /* Eén onderdeel dat faalt mag de rest van de pagina niet breken */
      try { init(); } catch (err) { if (window.console) console.error(err); }
    });
  });
})();
