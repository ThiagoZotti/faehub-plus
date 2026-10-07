(() => {
  const root = document.querySelector('.module-world');
  if (!root) return;
  root.querySelectorAll('[data-day-filter]').forEach(button => button.addEventListener('click', () => {
    root.querySelectorAll('[data-day-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    root.querySelectorAll('[data-week-day]').forEach(card => card.hidden = button.dataset.dayFilter !== 'all' && card.dataset.weekDay !== button.dataset.dayFilter);
    root.querySelector('.week-cards').classList.toggle('focused', button.dataset.dayFilter !== 'all');
  }));
  function searchable(kind, selector, searchId, emptyId) {
    let filter = kind === 'exercise' ? (root.dataset.initialExerciseFilter || 'all') : 'all';
    const cards = [...root.querySelectorAll(selector)], search = document.getElementById(searchId);
    const update = () => {
      const query = (search?.value || '').toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
      cards.forEach(c => {
        const state = kind === 'notice' ? (c.classList.contains('is-read') ? 'read' : 'unread') : c.dataset.exerciseState;
        const haystack = c.dataset.search.normalize('NFD').replace(/[\u0300-\u036f]/g,'');
        c.hidden = !(filter === 'all' || filter === state) || !haystack.includes(query);
      });
      const empty = document.getElementById(emptyId);
      if (empty) empty.hidden = cards.some(c => !c.hidden);
    };
    search?.addEventListener('input', update);
    root.querySelectorAll('[data-' + kind + '-filter]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset[kind + 'Filter'] === filter));
      button.addEventListener('click', () => {
        filter = button.dataset[kind + 'Filter'];
        root.querySelectorAll('[data-' + kind + '-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
        update();
      });
    });
    return update;
  }
  const noticeUpdate = searchable('notice','.notice-entry','noticeSearch','noticeEmpty');
  const exerciseUpdate = searchable('exercise','.mission-card','exerciseSearch','exerciseEmpty');
  exerciseUpdate();
  const notices = [...root.querySelectorAll('.notice-entry')];
  const storageKey = 'faehub-notices:' + root.dataset.noticeUser;
  let read = [];
  try { const saved = JSON.parse(localStorage.getItem(storageKey) || '[]'); if (Array.isArray(saved)) read = saved; } catch (_) {}
  function renderRead() {
    notices.forEach(card => {
      const done = read.includes(card.dataset.noticeKey);
      card.classList.toggle('is-read',done);
      card.querySelector('[data-read-label]').textContent = done ? 'Lido' : 'Não lido';
      const button = card.querySelector('[data-read-toggle]');
      button.textContent = done ? 'Marcar como não lido' : 'Marcar como lido';
      button.setAttribute('aria-pressed',String(done));
    });
    const count = document.getElementById('unreadCount');
    if (count) count.textContent = notices.filter(c=>!read.includes(c.dataset.noticeKey)).length;
    noticeUpdate();
  }
  notices.forEach(card => card.querySelector('[data-read-toggle]').addEventListener('click', () => {
    const key = card.dataset.noticeKey;
    read = read.includes(key) ? read.filter(k=>k!==key) : [...read,key];
    try { localStorage.setItem(storageKey,JSON.stringify(read)); } catch (_) { document.getElementById('moduleStatus').textContent = 'Não foi possível salvar a leitura neste navegador.'; }
    renderRead();
  }));
  renderRead();
  root.querySelectorAll('[data-open-answer]').forEach(button=>button.addEventListener('click',()=>document.getElementById(button.dataset.openAnswer).showModal()));
  root.querySelectorAll('[data-close-dialog]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
  root.querySelectorAll('.mission-dialog form').forEach(form=>form.addEventListener('submit', event=>{
    form.querySelectorAll('.module-field-error').forEach(error=>error.remove());
    const text = form.querySelector('textarea');
    const file = form.querySelector('input[type=file]');
    if (!text.value.trim() && !file?.files.length) {
      event.preventDefault();
      const error=document.createElement('small');
      error.className='module-field-error';
      error.textContent='Escreva uma resposta ou selecione um anexo antes de enviar.';
      text.setAttribute('aria-invalid','true');
      text.insertAdjacentElement('afterend',error);
      text.focus();
    }
  }));
  root.querySelectorAll('.mission-dialog textarea').forEach(text=>text.addEventListener('input',()=>text.removeAttribute('aria-invalid')));
})();
