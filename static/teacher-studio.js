(() => {
 const root=document.querySelector('.studio-world');if(!root)return;
 root.querySelectorAll('[data-studio-open]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.studioOpen).showModal()));
 root.querySelectorAll('[data-studio-close]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
 root.querySelectorAll('[data-confirm]').forEach(f=>f.addEventListener('submit',e=>{if(!confirm(f.dataset.confirm))e.preventDefault();}));
 let filter='active';const search=document.getElementById('studioSearch'),cards=[...root.querySelectorAll('[data-studio-state]')];
 const norm=s=>s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
 function update(){cards.forEach(c=>c.hidden=(filter!=='all'&&c.dataset.studioState!==filter)||!norm(c.dataset.studioSearch).includes(norm(search.value)));document.getElementById('studioEmpty').hidden=cards.some(c=>!c.hidden);}
 root.querySelectorAll('[data-studio-filter]').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.studioFilter;root.querySelectorAll('[data-studio-filter]').forEach(o=>o.setAttribute('aria-pressed',String(o===b)));update();}));search.addEventListener('input',update);update();
 const cls=document.getElementById('studioClass'),discipline=document.getElementById('studioDiscipline');
 function subjects(){if(!discipline)return;[...discipline.options].forEach(o=>o.disabled=o.hidden=o.dataset.class!==cls.value);if(discipline.selectedOptions[0]?.disabled)discipline.value=[...discipline.options].find(o=>!o.disabled)?.value||'';}
 cls.addEventListener('change',subjects);subjects();
 if(discipline){root.querySelectorAll('dialog form').forEach(form=>{if(!form.elements.description)return;form.enctype='multipart/form-data';const label=document.createElement('label');label.textContent='Anexo opcional';const input=document.createElement('input');input.type='file';input.name='attachment';input.accept='.pdf,.png,.jpg,.jpeg,.txt,.zip';label.append(input);const submit=form.querySelector('button[type="submit"],button:not([type])');form.insertBefore(label,submit);});}
 const failed=document.getElementById('studioFailed');if(failed){const data=JSON.parse(failed.content.textContent);const dialog=document.getElementById(data.action==='edit'?'edit'+data.id:data.action==='review'?'deliveries'+data.id:'studioNew');if(dialog){const form=data.action==='review'?[...dialog.querySelectorAll('form')].find(f=>f.elements.submission_id.value===data.submission_id):dialog.querySelector('form');if(form){Object.entries(data).forEach(([k,v])=>{if(k!=='token'&&k!=='answer_snapshot'&&form.elements[k])form.elements[k].value=v;});form.closest('details')?.setAttribute('open','');}dialog.showModal();}}
 root.querySelectorAll('dialog form').forEach(form=>{const key='faehub-draft:'+root.dataset.owner+':'+location.pathname+':'+form.closest('dialog').id+':'+(form.elements.submission_id?.value||'');if(!failed){try{const data=JSON.parse(sessionStorage.getItem(key)||'null');if(data)Object.entries(data).forEach(([k,v])=>{if(form.elements[k])form.elements[k].value=v;});}catch{}}
 form.addEventListener('input',()=>{const data={};['title','body','description','due_date','feedback','score'].forEach(k=>{if(form.elements[k])data[k]=form.elements[k].value;});try{sessionStorage.setItem(key,JSON.stringify(data));}catch{}});
 form.addEventListener('submit',()=>{try{sessionStorage.removeItem(key);}catch{}});});
})();
