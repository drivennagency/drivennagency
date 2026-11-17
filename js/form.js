/* Drivenn Agency: formulieren versturen via Web3Forms (mail naar info@drivennagency.nl).
   Werkt voor elk <form data-form>. Meldingen staan in de taal van de pagina en
   verschijnen in de pagina zelf (geen pop-up), zodat ook schermlezers ze voorlezen. */
(function () {
  'use strict';

  var WEB3_KEY = '80de7e47-edf9-4dc7-b00d-68016edca9ff';   // publieke formuliersleutel (geen geheim)
  var ENDPOINT = 'https://api.web3forms.com/submit';
  var lang = (document.documentElement.lang || 'nl').slice(0, 2);

  var TEXT = {
    nl: {
      sending: 'Bezig met verzenden…',
      error: 'Er ging iets mis bij het verzenden. Probeer het later opnieuw of mail ons direct op info@drivennagency.nl.',
      offline: 'Geen internetverbinding. Controleer je verbinding en probeer het opnieuw.'
    },
    en: {
      sending: 'Sending…',
      error: 'Something went wrong while sending. Please try again later or email us directly at info@drivennagency.nl.',
      offline: 'No internet connection. Please check your connection and try again.'
    },
    de: {
      sending: 'Wird gesendet…',
      error: 'Beim Senden ist etwas schiefgelaufen. Versuche es später erneut oder schreib uns direkt an info@drivennagency.nl.',
      offline: 'Keine Internetverbindung. Bitte prüfe deine Verbindung und versuche es erneut.'
    }
  };
  var t = TEXT[lang] || TEXT.nl;

  /* Herkenbaar onderwerp voor in de mail: kop van het formulier, anders de paginatitel. */
  function subjectFor(form) {
    var card = form.closest('.form-card');
    var h = card ? card.querySelector('.form-card__head h3, h3, h2') : null;
    var label = (h && h.textContent.trim()) || document.title.split(' | ')[0].trim();
    return 'Drivenn website: ' + label;
  }

  function statusBox(form) {
    var box = form.querySelector('.form-status');
    if (!box) {
      box = document.createElement('p');
      box.className = 'form-status';
      box.setAttribute('role', 'alert');
      box.hidden = true;
      form.appendChild(box);
    }
    return box;
  }

  function init(form) {
    /* Onzichtbaar lokveld tegen spambots */
    var hp = document.createElement('input');
    hp.type = 'checkbox';
    hp.name = 'botcheck';
    hp.tabIndex = -1;
    hp.setAttribute('autocomplete', 'off');
    hp.setAttribute('aria-hidden', 'true');
    hp.style.cssText = 'position:absolute!important;left:-9999px;width:0;height:0;opacity:0';
    form.appendChild(hp);

    var busy = false;

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (busy || hp.checked) return;
      if (!form.checkValidity()) { form.reportValidity(); return; }

      var success = form.parentElement.querySelector('.form-success');
      var btn = form.querySelector('[type="submit"]');
      var btnHtml = btn ? btn.innerHTML : '';
      var status = statusBox(form);

      function restore() {
        busy = false;
        if (btn) { btn.disabled = false; btn.innerHTML = btnHtml; }
      }
      function done() {
        restore();
        form.reset();
        if (typeof window.gtag === 'function') {
          window.gtag('event', 'generate_lead', { form_name: subjectFor(form) });
        }
        if (success) {
          form.style.display = 'none';
          success.classList.add('show');
          success.setAttribute('role', 'status');
          success.setAttribute('tabindex', '-1');
          success.focus({ preventScroll: true });
          success.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
      function fail(message) {
        restore();
        status.textContent = message;
        status.hidden = false;
      }

      var fd = new FormData(form);
      fd.delete('botcheck');
      fd.append('access_key', WEB3_KEY);
      fd.append('subject', subjectFor(form));
      fd.append('from_name', 'Drivenn Agency website');
      fd.append('page', location.href);

      busy = true;
      status.hidden = true;
      if (btn) { btn.disabled = true; btn.textContent = t.sending; }

      fetch(ENDPOINT, { method: 'POST', headers: { Accept: 'application/json' }, body: fd })
        .then(function (r) { return r.json(); })
        .then(function (data) { if (data && data.success) done(); else fail(t.error); })
        .catch(function () { fail(navigator.onLine === false ? t.offline : t.error); });
    });
  }

  function start() {
    Array.prototype.forEach.call(document.querySelectorAll('form[data-form]'), init);
  }
  if (document.readyState !== 'loading') start();
  else document.addEventListener('DOMContentLoaded', start);
})();
