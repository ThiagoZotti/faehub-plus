(() => {
  const root = document.querySelector('.internship-world');
  if (!root) return;

  const cards = [...root.querySelectorAll('[data-internship-card]')];
  const search = document.getElementById('internshipSearch');
  const clear = document.getElementById('internshipClear');
  const reset = document.getElementById('internshipReset');
  const empty = document.getElementById('internshipEmpty');
  const count = document.getElementById('internshipResultCount');
  let modality = 'all';
  let state = root.dataset.role === 'professor' ? 'active' : 'all';

  const normalize = (value) => value.toLocaleLowerCase('pt-BR')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '');

  function updateResults() {
    const query = normalize(search?.value || '');
    let visible = 0;
    cards.forEach((card) => {
      const matchesSearch = normalize(card.dataset.search || '').includes(query);
      const matchesModality = modality === 'all' || card.dataset.modality === modality;
      const matchesState = state === 'all' || card.dataset.state === state;
      card.hidden = !(matchesSearch && matchesModality && matchesState);
      if (!card.hidden) visible += 1;
    });
    if (clear) clear.hidden = !query;
    if (empty) empty.hidden = visible > 0;
    if (count) count.textContent = `${visible} ${visible === 1 ? 'resultado' : 'resultados'}`;
  }

  root.querySelectorAll('[data-internship-modality]').forEach((button) => {
    button.addEventListener('click', () => {
      modality = button.dataset.internshipModality;
      root.querySelectorAll('[data-internship-modality]').forEach((item) =>
        item.setAttribute('aria-pressed', String(item === button)));
      updateResults();
    });
  });
  root.querySelectorAll('[data-internship-state]').forEach((button) => {
    button.addEventListener('click', () => {
      state = button.dataset.internshipState;
      root.querySelectorAll('[data-internship-state]').forEach((item) =>
        item.setAttribute('aria-pressed', String(item === button)));
      updateResults();
    });
  });
  search?.addEventListener('input', updateResults);
  clear?.addEventListener('click', () => { search.value = ''; search.focus(); updateResults(); });
  reset?.addEventListener('click', () => {
    modality = 'all'; state = root.dataset.role === 'professor' ? 'active' : 'all';
    if (search) search.value = '';
    root.querySelectorAll('[data-internship-modality]').forEach((button) =>
      button.setAttribute('aria-pressed', String(button.dataset.internshipModality === 'all')));
    root.querySelectorAll('[data-internship-state]').forEach((button) =>
      button.setAttribute('aria-pressed', String(button.dataset.internshipState === state)));
    updateResults(); search?.focus();
  });

  root.querySelectorAll('[data-internship-open]').forEach((button) => {
    button.addEventListener('click', () => document.getElementById(button.dataset.internshipOpen)?.showModal());
  });
  root.querySelectorAll('[data-internship-close]').forEach((button) => {
    button.addEventListener('click', () => button.closest('dialog')?.close());
  });
  root.querySelectorAll('dialog').forEach((dialog) => {
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog) dialog.close();
    });
  });

  const confirmDialog = document.getElementById('internshipConfirm');
  root.querySelectorAll('[data-internship-confirm]').forEach((button) => {
    button.addEventListener('click', () => {
      const restoring = button.dataset.action === 'restore';
      confirmDialog.querySelector('[name=id]').value = button.dataset.id;
      confirmDialog.querySelector('[name=action]').value = button.dataset.action;
      document.getElementById('internshipConfirmTitle').textContent = restoring
        ? 'Restaurar publicação?' : 'Arquivar publicação?';
      document.getElementById('internshipConfirmCopy').textContent = restoring
        ? `“${button.dataset.title}” voltará ao radar dos alunos se o prazo ainda estiver aberto.`
        : `“${button.dataset.title}” sairá do radar dos alunos, mas o histórico será preservado.`;
      document.getElementById('internshipConfirmAction').textContent = restoring ? 'Restaurar' : 'Arquivar';
      confirmDialog.showModal();
    });
  });

  const prefix = `faehub-draft:${root.dataset.owner}:internships:`;
  const failedTemplate = document.getElementById('internshipFailed');
  const failed = failedTemplate ? JSON.parse(failedTemplate.content.textContent) : null;
  if (!failed && document.getElementById('flashToast')) {
    Object.keys(sessionStorage).filter((key) => key.startsWith(prefix)).forEach((key) => sessionStorage.removeItem(key));
  }

  root.querySelectorAll('[data-internship-form]').forEach((form) => {
    const key = prefix + form.dataset.draft;
    if (!failed) {
      try {
        const saved = JSON.parse(sessionStorage.getItem(key) || 'null');
        if (saved) Object.entries(saved).forEach(([name, value]) => {
          if (form.elements[name]) form.elements[name].value = value;
        });
      } catch (_) { /* storage may be unavailable */ }
    }
    form.addEventListener('input', () => {
      const draft = {};
      new FormData(form).forEach((value, name) => {
        if (!['token', 'action', 'id'].includes(name)) draft[name] = value;
      });
      try { sessionStorage.setItem(key, JSON.stringify(draft)); } catch (_) { /* non-critical */ }
    });
    form.addEventListener('submit', (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        form.reportValidity();
        form.querySelector(':invalid')?.focus();
        return;
      }
      const submit = form.querySelector('[type=submit]');
      if (submit) { submit.disabled = true; submit.setAttribute('aria-busy', 'true'); submit.dataset.label = submit.textContent; submit.textContent = 'Salvando…'; }
    });
  });

  if (failed) {
    const dialogId = failed.action === 'edit' ? `internshipEdit${failed.id}` : 'internshipNew';
    const dialog = document.getElementById(dialogId);
    const form = dialog?.querySelector('form');
    if (form) {
      Object.entries(failed).forEach(([name, value]) => {
        if (!['token', 'id', 'action'].includes(name) && form.elements[name]) form.elements[name].value = value;
      });
      dialog.showModal();
      requestAnimationFrame(() => form.querySelector('input:not([type=hidden]), select, textarea')?.focus());
    }
  }

  updateResults();
})();
