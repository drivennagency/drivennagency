/* Drivenn Agency — formulierverwerking via Web3Forms (mail naar info@drivennagency.nl) */
(function () {
  'use strict';
  var WEB3_KEY = '80de7e47-edf9-4dc7-b00d-68016edca9ff';
  var ENDPOINT = 'https://api.web3forms.com/submit';

  function subjectFor(form) {
    // Herkenbare naam voor in de mail: kop van het formulier, anders de paginatitel.
    var card = form.closest('.form-card');
    var h = card ? card.querySelector('.form-card__head h3, h3, h2') : null;
    var label = (h && h.textContent.trim()) || document.title.split(' | ')[0].trim();
    return 'Drivenn website — ' + label;
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[data-form]').forEach(function (form) {
      // Onzichtbaar honeypot-veld tegen spambots.
      var hp = document.createElement('input');
      hp.type = 'checkbox';
      hp.name = 'botcheck';
      hp.tabIndex = -1;
      hp.setAttribute('autocomplete', 'off');
      hp.style.cssText = 'position:absolute!important;left:-9999px;width:0;height:0;opacity:0';
      form.appendChild(hp);

      form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (hp.checked) { return; }                       // bot: negeren
        if (!form.checkValidity()) { form.reportValidity(); return; }

        var success = form.parentElement.querySelector('.form-success');
        var btn = form.querySelector('[type="submit"]');
        var btnLabel = btn ? btn.textContent : '';

        function done() {
          if (success) {
            form.style.display = 'none';
            success.classList.add('show');
            success.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
          form.reset();
        }
        function fail() {
          if (btn) { btn.disabled = false; btn.textContent = btnLabel; }
          alert('Er ging iets mis bij het verzenden. Probeer het later opnieuw of mail ons direct op info@drivennagency.nl.');
        }

        var fd = new FormData(form);
        fd.delete('botcheck');
        fd.append('access_key', WEB3_KEY);
        fd.append('subject', subjectFor(form));
        fd.append('from_name', 'Drivenn Agency website');
        fd.append('page', location.href);

        if (btn) { btn.disabled = true; btn.textContent = '…'; }

        fetch(ENDPOINT, { method: 'POST', headers: { Accept: 'application/json' }, body: fd })
          .then(function (r) { return r.json(); })
          .then(function (data) { if (data && data.success) { done(); } else { fail(); } })
          .catch(fail);
      });
    });
  });
})();
