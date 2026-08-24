/* Drivenn Agency — form handling (Formspree-ready, always shows confirmation) */
(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[data-form]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var success = form.parentElement.querySelector('.form-success');
        var endpoint = form.getAttribute('action');
        function done() {
          if (success) { form.style.display = 'none'; success.classList.add('show'); success.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
          form.reset();
        }
        // If a real Formspree endpoint is configured, submit to it; otherwise just confirm.
        if (endpoint && endpoint.indexOf('formspree.io') !== -1) {
          fetch(endpoint, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } })
            .then(function () { done(); })
            .catch(function () { done(); });
        } else {
          done();
        }
      });
    });
  });
})();
