/* Drivenn Agency — front-end behaviors */
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    /* year */
    var y = document.getElementById('year');
    if (y) y.textContent = new Date().getFullYear();

    /* sticky header state */
    var header = document.getElementById('site-header');
    function onScroll() {
      if (!header) return;
      header.classList.toggle('scrolled', window.scrollY > 40);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    /* active nav highlight */
    var page = document.body.getAttribute('data-page');
    if (page) {
      document.querySelectorAll('.nav__links a[data-page]').forEach(function (a) {
        if (a.getAttribute('data-page') === page) { a.classList.add('active'); a.setAttribute('aria-current', 'page'); }
      });
    }

    /* mobile menu */
    var burger = document.querySelector('.nav__burger');
    var overlay = document.querySelector('.mobile-overlay');
    var closeBtn = document.querySelector('.mobile-overlay__close');
    function openMenu() { overlay.classList.add('open'); burger.setAttribute('aria-expanded', 'true'); document.body.style.overflow = 'hidden'; }
    function closeMenu() { overlay.classList.remove('open'); burger.setAttribute('aria-expanded', 'false'); document.body.style.overflow = ''; }
    if (burger && overlay) {
      burger.addEventListener('click', openMenu);
      if (closeBtn) closeBtn.addEventListener('click', closeMenu);
      overlay.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', closeMenu); });
      document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenu(); });
    }

    /* language dropdown */
    var lang = document.querySelector('.lang-switch');
    if (lang) {
      var btn = lang.querySelector('.lang-switch__current');
      btn.addEventListener('click', function (e) { e.stopPropagation(); lang.classList.toggle('open'); });
      document.addEventListener('click', function () { lang.classList.remove('open'); });
    }

    /* reveal on scroll (safe pattern: content visible without JS) */
    if (!reduce && 'IntersectionObserver' in window) {
      document.body.classList.add('js-motion');
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
      }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
      document.querySelectorAll('.reveal').forEach(function (el) { io.observe(el); });
    }

    /* hero video: load after window load so it never competes with LCP */
    function initHeroVideo() {
      var v = document.querySelector('.hero__bg-video');
      if (!v) return;
      var sources = v.querySelectorAll('source[data-src]');
      if (sources.length) {
        sources.forEach(function (s) { s.src = s.dataset.src; });
      } else if (v.dataset.src) {
        v.src = v.dataset.src;
      } else { return; }
      v.load();
      var p = v.play();
      if (p && p.catch) p.catch(function () {});
    }
    window.addEventListener('load', initHeroVideo);

    /* hero stats: count up when they scroll into view */
    (function () {
      var nums = document.querySelectorAll('.hero__stat .n[data-count]');
      if (!nums.length) return;
      function fmt(n) { return n.toLocaleString('nl-NL'); }
      function setFinal(el) {
        var pre = el.getAttribute('data-prefix') || '', suf = el.getAttribute('data-suffix') || '';
        el.textContent = pre + fmt(parseFloat(el.getAttribute('data-count'))) + suf;
      }
      function run(el) {
        var target = parseFloat(el.getAttribute('data-count'));
        var startVal = parseFloat(el.getAttribute('data-start') || '0');
        var pre = el.getAttribute('data-prefix') || '', suf = el.getAttribute('data-suffix') || '';
        var dur = 1600, start = null;
        function step(ts) {
          if (!start) start = ts;
          var p = Math.min((ts - start) / dur, 1);
          var eased = 1 - Math.pow(1 - p, 3);
          el.textContent = pre + fmt(Math.round(startVal + (target - startVal) * eased)) + suf;
          if (p < 1) requestAnimationFrame(step); else setFinal(el);
        }
        requestAnimationFrame(step);
      }
      if (reduce || !('IntersectionObserver' in window)) { nums.forEach(setFinal); return; }
      var io2 = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) { run(en.target); io2.unobserve(en.target); } });
      }, { threshold: 0.6 });
      nums.forEach(function (el) { io2.observe(el); });
    })();

    /* marquee: duplicate track for seamless loop */
    document.querySelectorAll('.marquee').forEach(function (m) {
      var track = m.querySelector('.marquee__track');
      if (track) m.appendChild(track.cloneNode(true));
    });

    /* FAQ accordion */
    document.querySelectorAll('.faq__q').forEach(function (q) {
      q.addEventListener('click', function () {
        var item = q.closest('.faq__item');
        var a = item.querySelector('.faq__a');
        var open = item.classList.toggle('open');
        a.style.maxHeight = open ? a.scrollHeight + 'px' : '0';
      });
    });

    /* blog search */
    var blogSearch = document.getElementById('blog-search');
    if (blogSearch) {
      var blogCards = document.querySelectorAll('[data-blog-card]');
      var blogEmpty = document.getElementById('blog-empty');
      blogSearch.addEventListener('input', function () {
        var q = this.value.toLowerCase().trim();
        var shown = 0;
        blogCards.forEach(function (c) {
          var hit = c.getAttribute('data-search').indexOf(q) !== -1;
          c.style.display = hit ? '' : 'none';
          if (hit) shown++;
        });
        if (blogEmpty) blogEmpty.style.display = shown ? 'none' : 'block';
      });
    }

    /* AI catalog: search + category/app filter */
    var aiSearch = document.getElementById('ai-search');
    var aiCards = document.querySelectorAll('[data-ai-card]');
    var aiChips = document.querySelectorAll('.ai-chip');
    var aiEmpty = document.getElementById('ai-empty');
    if (aiCards.length) {
      var activeCat = 'all';
      function filterAI() {
        var q = aiSearch ? aiSearch.value.toLowerCase().trim() : '';
        var shown = 0;
        aiCards.forEach(function (c) {
          var text = c.getAttribute('data-search');
          var cat = c.getAttribute('data-cat');
          var matchText = !q || text.indexOf(q) !== -1;
          var matchCat = activeCat === 'all' || cat === activeCat;
          var ok = matchText && matchCat;
          c.style.display = ok ? '' : 'none';
          if (ok) shown++;
        });
        if (aiEmpty) aiEmpty.style.display = shown ? 'none' : 'block';
      }
      if (aiSearch) aiSearch.addEventListener('input', filterAI);
      aiChips.forEach(function (chip) {
        chip.addEventListener('click', function () {
          aiChips.forEach(function (c) { c.classList.remove('active'); });
          chip.classList.add('active');
          activeCat = chip.getAttribute('data-cat');
          filterAI();
        });
      });
    }
  });
})();
