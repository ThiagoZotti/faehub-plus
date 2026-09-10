(() => {
  const root = document.getElementById('dashboard');
  if (!root) return;
  const status = document.getElementById('dashboardStatus');
  const focus = document.getElementById('focusLobby');
  focus.addEventListener('click', () => {
    const on = root.classList.toggle('is-focused');
    focus.setAttribute('aria-pressed', String(on));
    root.querySelector('.focus-caption').hidden = !on;
    root.querySelector('.lobby-options')?.removeAttribute('open');
  });
  const fullscreen = document.getElementById('fullscreenLobby');
  fullscreen.hidden = !document.fullscreenEnabled;
  fullscreen.addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch { status.textContent = 'Tela cheia indisponível neste navegador. O modo foco continua disponível.'; }
  });
  document.addEventListener('fullscreenchange', () => {
    fullscreen.setAttribute('aria-pressed', String(!!document.fullscreenElement));
    fullscreen.querySelector('span').textContent = document.fullscreenElement ? 'Sair da tela cheia' : 'Tela cheia';
  });
  document.getElementById('refreshLobby').addEventListener('click', () => location.reload());
  const agenda = document.getElementById('agendaDialog');
  document.getElementById('openAgenda').addEventListener('click', () => agenda.showModal());
  document.getElementById('closeAgenda').addEventListener('click', () => agenda.close());
  agenda.addEventListener('click', event => {
    const box = agenda.getBoundingClientRect();
    if (event.target === agenda && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) agenda.close();
  });
  function updateClock() {
    const lesson = root.querySelector('[data-lesson-at]');
    if (lesson) {
      const minutes = Math.ceil((Date.parse(lesson.dataset.lessonAt) - Date.now()) / 60000);
      lesson.textContent = minutes <= 0 ? 'Horário alcançado. Atualize para ver a próxima aula.' :
        minutes < 60 ? `Começa em ${minutes} min` : minutes < 1440 ? `Começa em ${Math.floor(minutes / 60)}h ${minutes % 60}min` : `Começa em ${Math.floor(minutes / 1440)}d ${Math.floor(minutes % 1440 / 60)}h`;
    }
    const updated = root.querySelector('[data-updated]');
    updated.textContent = 'Atualizado às ' + new Intl.DateTimeFormat('pt-BR', {timeZone:'America/Sao_Paulo',hour:'2-digit',minute:'2-digit'}).format(new Date(updated.dataset.updated));
  }
  updateClock();
  const clock = setInterval(updateClock, 30000);
  addEventListener('pagehide', () => clearInterval(clock), {once:true});
})();
