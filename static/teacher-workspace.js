(() => {
  const root=document.querySelector('.teacher-workspace'); if(!root)return;
  const rows=[...root.querySelectorAll('[data-student]')], search=root.querySelector('[data-roster-search]');
  const normalize=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  function filter(){const q=normalize(search?.value||'');let count=0;rows.forEach(r=>{r.hidden=!normalize(r.dataset.student).includes(q);if(!r.hidden)count++;});const c=root.querySelector('[data-roster-counter]');if(c)c.textContent=`${count} de ${rows.length} alunos`;const e=root.querySelector('[data-roster-empty]');if(e)e.hidden=count!==0;}
  search?.addEventListener('input',filter);filter();
  let dirty=false;
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  const attendance=root.querySelector('#attendanceForm');
  if(attendance){
    const roll=[...attendance.querySelectorAll('.tw-roll-row')];
    function counts(){let p=0,a=0;roll.forEach(r=>{const v=r.querySelector('input:checked')?.value;if(v==='presente')p++;if(v==='ausente')a++;});document.getElementById('presentCount').textContent=p;document.getElementById('absentCount').textContent=a;document.getElementById('unmarkedCount').textContent=roll.length-p-a;}
    attendance.addEventListener('change',()=>{dirty=true;counts();});
    attendance.addEventListener('reset',()=>{dirty=false;setTimeout(counts,0);});
    document.getElementById('allPresent').addEventListener('click',()=>{if(!confirm(`Marcar todos os ${roll.length} alunos como presentes, inclusive os ocultos pela busca?`))return;roll.forEach(r=>r.querySelector('[value=presente]').checked=true);dirty=true;counts();});
    attendance.addEventListener('submit',e=>{const missing=roll.find(r=>!r.querySelector('input:checked'));if(missing){e.preventDefault();search.value='';filter();alert('Marque a presença de todos os alunos antes de salvar.');missing.querySelector('input').focus();return;}if(Number(attendance.dataset.existing)>0&&!confirm('Substituir os registros já salvos nesta data pela seleção atual?')){e.preventDefault();return;}dirty=false;});counts();
  }
  root.querySelectorAll('.tw-grade-row').forEach(form=>{
    form.addEventListener('input',()=>{form.dataset.dirty='true';dirty=true;const a=form.elements.n1,b=form.elements.n2;form.querySelector('output').textContent=a.value!==''&&b.value!==''&&a.validity.valid&&b.validity.valid?((Number(a.value)+Number(b.value))/2).toFixed(2):'—';});
    form.addEventListener('submit',e=>{const others=[...root.querySelectorAll('[data-dirty=true]')].some(f=>f!==form);if(others&&!confirm('Salvar esta linha recarrega a página. As alterações não salvas dos outros alunos serão perdidas. Continuar?')){e.preventDefault();return;}if(form.dataset.hasGrade==='yes'&&!confirm('Atualizar as notas já salvas deste aluno nesta disciplina?')){e.preventDefault();return;}dirty=false;});
  });
})();
