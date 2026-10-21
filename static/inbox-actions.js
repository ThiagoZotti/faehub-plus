/* Pessimistic explicit bulk read. The server resolves the authorized scope. */
(() => {
  const forms = document.querySelectorAll('[data-inbox-read-all]');
  forms.forEach(form => form.addEventListener('submit', event => {
    if (form.dataset.pending) { event.preventDefault(); return; }
    form.dataset.pending = 'true';
    form.setAttribute('aria-busy', 'true');
    const button = form.querySelector('button[type="submit"]');
    button.dataset.idleLabel = button.textContent;
    button.style.minWidth = button.getBoundingClientRect().width + 'px';
    button.disabled = true;
    button.textContent = 'Marcando leitura…';
  }));
  window.addEventListener('pageshow', () => forms.forEach(form => {
    if (!form.dataset.pending) return;
    delete form.dataset.pending;
    form.removeAttribute('aria-busy');
    const button = form.querySelector('button[type="submit"]');
    button.disabled = false;
    button.textContent = button.dataset.idleLabel;
  }));
})();
