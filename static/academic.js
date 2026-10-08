(() => {
  const root = document.querySelector('.academic');
  if (!root) return;
  const entries = [...root.querySelectorAll('.grade-entry')];
  root.querySelectorAll('[data-grade-filter]').forEach(button => button.addEventListener('click', () => {
    root.querySelectorAll('[data-grade-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    entries.forEach(entry => { entry.hidden = button.dataset.gradeFilter !== 'all' && entry.dataset.gradeState !== button.dataset.gradeFilter; });
    const count = entries.filter(e => !e.hidden).length;
    document.getElementById('gradeCount').textContent = `${count} disciplina${count === 1 ? '' : 's'}`;
    document.getElementById('gradeEmpty').hidden = count !== 0;
  }));
  const first = document.getElementById('simN1'), second = document.getElementById('simN2');
  function simulate() {
    const mean = (Number(first.value) + Number(second.value)) / 2;
    const format = value => Number(value).toLocaleString('pt-BR', {minimumFractionDigits:1, maximumFractionDigits:1});
    document.getElementById('simOut1').textContent = format(first.value);
    document.getElementById('simOut2').textContent = format(second.value);
    document.getElementById('simMean').textContent = format(mean);
    document.getElementById('simStatus').textContent = mean >= 6 ? 'Dentro da referência de 6,0.' : 'Abaixo da referência de 6,0.';
  }
  if (first) [first, second].forEach(input => input.addEventListener('input', simulate));
  let beforePrint;
  window.addEventListener('beforeprint', () => { beforePrint = entries.map(e => [e.open, e.hidden]); entries.forEach(e => {if (e.tagName === 'DETAILS') e.open = true; e.hidden = false;}); });
  window.addEventListener('afterprint', () => { if (beforePrint) entries.forEach((e,i) => { if (e.tagName === 'DETAILS') e.open = beforePrint[i][0]; e.hidden = beforePrint[i][1]; }); });
  root.querySelector('.print-report')?.addEventListener('click', () => window.print());
  root.querySelectorAll('[data-record-date]').forEach(button => button.addEventListener('click', () => {
    root.querySelectorAll('[data-record-date]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    const [year, month, day] = button.dataset.recordDate.split('-');
    const dateOutput = document.getElementById('recordDate');
    if (dateOutput) dateOutput.textContent = `${day}/${month}/${year}`;
    const statusOutput = document.getElementById('recordStatus');
    if (statusOutput) statusOutput.textContent = {presente:'Presença confirmada na chamada deste dia.', ausente:'Falta registrada na chamada deste dia.', unrecorded:'Nenhuma chamada salva para este dia. Isso não indica ausência.'}[button.dataset.recordStatus];
  }));
})();
