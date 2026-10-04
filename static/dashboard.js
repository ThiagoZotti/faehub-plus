(() => {
  const root = document.getElementById('dashboard');
  if (!root) return;
  function updateClock() {
    const lesson = root.querySelector('[data-lesson-at]');
    if (lesson) {
      const minutes = Math.ceil((Date.parse(lesson.dataset.lessonAt) - Date.now()) / 60000);
      lesson.textContent = minutes <= 0 ? 'Horário alcançado. Atualize para ver a próxima aula.' :
        minutes < 60 ? `Começa em ${minutes} min` : minutes < 1440 ? `Começa em ${Math.floor(minutes / 60)}h ${minutes % 60}min` : `Começa em ${Math.floor(minutes / 1440)}d ${Math.floor(minutes % 1440 / 60)}h`;
    }
  }
  updateClock();
  const clock = setInterval(updateClock, 30000);
  addEventListener('pagehide', () => clearInterval(clock), {once:true});
})();
