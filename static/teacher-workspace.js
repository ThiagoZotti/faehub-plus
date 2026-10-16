(() => {
 const root=document.querySelector('.teacher-workspace'),ui=window.CampusActions;if(!root||!ui)return;
 const rows=[...root.querySelectorAll('[data-student]')],search=root.querySelector('[data-roster-search]');
 const normalize=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 function filter(){const q=normalize(search?.value||'');let count=0;rows.forEach(r=>{r.hidden=!normalize(r.dataset.student).includes(q);if(!r.hidden)count++});const c=root.querySelector('[data-roster-counter]');if(c)c.textContent=`${count} de ${rows.length} alunos`;const e=root.querySelector('[data-roster-empty]');if(e)e.hidden=count!==0}
 search?.addEventListener('input',filter);ui.clearSearch(search,'Limpar busca de alunos');filter();
 let dirty=false;window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue=''}});
 const attendance=root.querySelector('#attendanceForm');
 root.querySelectorAll('form:not(#attendanceForm):not(.tw-grade-row)').forEach(form=>ui.bindSubmit(form,{label:'Consultando…'}));
 if(attendance){
  const roll=[...attendance.querySelectorAll('.tw-roll-row')];
  function counts(){let p=0,a=0;roll.forEach(r=>{const v=r.querySelector('input:checked')?.value;if(v==='presente')p++;if(v==='ausente')a++});document.getElementById('presentCount').textContent=p;document.getElementById('absentCount').textContent=a;document.getElementById('unmarkedCount').textContent=roll.length-p-a}
  attendance.addEventListener('change',()=>{dirty=true;counts()});attendance.addEventListener('reset',()=>{dirty=false;setTimeout(counts,0)});
  document.getElementById('allPresent').addEventListener('click',async()=>{if(!await ui.ask(`Marcar todos os ${roll.length} alunos como presentes, inclusive os ocultos pela busca?`,{title:'Marcar todos como presentes?',action:'Marcar presentes'}))return;roll.forEach(r=>r.querySelector('[value=presente]').checked=true);dirty=true;counts()});
  ui.bindSubmit(attendance,{before:async()=>{const missing=roll.find(r=>!r.querySelector('input:checked'));if(missing){if(search)search.value='';filter();return ui.error(attendance,'Marque a presença de todos os alunos antes de salvar.',missing.querySelector('input'))}if(Number(attendance.dataset.existing)>0&&!await ui.ask('Substituir os registros já salvos nesta aula pela seleção atual?',{title:'Atualizar a chamada?',action:'Salvar chamada',warning:true}))return false;return true},afterAllowed:()=>{dirty=false}});counts();
 }
 root.querySelectorAll('.tw-grade-row').forEach(form=>{
  form.addEventListener('input',()=>{form.dataset.dirty='true';dirty=true;const a=form.elements.n1,b=form.elements.n2;form.querySelector('output').textContent=a.value!==''&&b.value!==''&&a.validity.valid&&b.validity.valid?((Number(a.value)+Number(b.value))/2).toFixed(2).replace('.',','):'—'});
  ui.bindSubmit(form,{before:async()=>{const others=[...root.querySelectorAll('[data-dirty=true]')].some(f=>f!==form);if(others&&!await ui.ask('Salvar esta linha recarrega a página. As alterações não salvas dos outros alunos serão perdidas. Continuar?',{title:'Salvar notas desta linha?',action:'Salvar esta linha',warning:true}))return false;if(form.dataset.hasGrade==='yes'&&!await ui.ask('Atualizar as notas já salvas deste aluno nesta disciplina?',{title:'Atualizar notas?',action:'Salvar notas',warning:true}))return false;return true},afterAllowed:()=>{dirty=false}});
 });
})();
