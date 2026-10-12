/* Shared authored actions for teacher row/bulk workflows; never grants permission. */
(() => {
 let activeDialog=null, nextId=0; const bound=new WeakSet(), ids=new WeakMap(),submitTimers=new Set();
 const errorId=form=>{if(!ids.has(form))ids.set(form,'campusFormError'+(++nextId));return ids.get(form)};
 function clear(form){form.querySelectorAll('[data-campus-error]').forEach(e=>e.remove());form.querySelectorAll('[data-campus-invalid]').forEach(e=>{e.removeAttribute('aria-invalid');e.removeAttribute('aria-describedby');delete e.dataset.campusInvalid})}
 function error(form,message,field){clear(form);const p=document.createElement('p');p.className='campus-field-error';p.dataset.campusError='true';p.id=errorId(form);p.setAttribute('role','alert');p.textContent=message;form.prepend(p);if(field){field.setAttribute('aria-invalid','true');field.setAttribute('aria-describedby',p.id);field.dataset.campusInvalid='true';field.focus()}return false}
 function valid(form){clear(form);const invalid=[...form.elements].find(e=>e.willValidate&&!e.validity.valid);return invalid?error(form,invalid.validity.valueMissing?'Preencha o campo indicado antes de salvar.':'Confira o formato e os limites do campo indicado.',invalid):true}
 function ask(message,{title='Confirme a alteração',action='Continuar',warning=false}={}){
  if(activeDialog)return Promise.resolve(false);
  const opener=document.activeElement,d=document.createElement('dialog');activeDialog=d;d.className='campus-action-dialog';d.setAttribute('aria-labelledby','campusActionTitle');d.setAttribute('aria-describedby','campusActionText');
  const h=document.createElement('h2');h.id='campusActionTitle';h.textContent=title;const p=document.createElement('p');p.id='campusActionText';p.textContent=message;
  const footer=document.createElement('footer'),cancel=document.createElement('button'),accept=document.createElement('button');cancel.type=accept.type='button';cancel.textContent='Cancelar';accept.textContent=action;accept.className=warning?'is-warning':'is-primary';footer.append(cancel,accept);d.append(h,p,footer);document.body.append(d);
  return new Promise(resolve=>{d.addEventListener('close',()=>{const accepted=d.returnValue==='accepted';d.remove();activeDialog=null;opener?.focus();resolve(accepted)},{once:true});cancel.addEventListener('click',()=>d.close('cancel'));accept.addEventListener('click',()=>d.close('accepted'));d.addEventListener('click',e=>{if(e.target===d)d.close('cancel')});d.showModal();cancel.focus()});
 }
 function busy(form,submitter,label){form.dataset.uiPending='true';form.setAttribute('aria-busy','true');if(submitter?.name){const input=document.createElement('input');input.type='hidden';input.name=submitter.name;input.value=submitter.value;input.dataset.uiSubmitValue='true';form.append(input)}form.querySelectorAll('button[type=submit],button:not([type])').forEach(b=>{b.style.minWidth=b.getBoundingClientRect().width+'px';b.dataset.uiLabel=b.textContent;b.disabled=true;if(b===submitter)b.textContent=label})}
 function bindSubmit(form,{before=()=>true,label='Salvando…',afterAllowed=()=>{}}={}){
  if(bound.has(form))return;bound.add(form);form.noValidate=true;
  form.addEventListener('input',()=>clear(form));
  form.addEventListener('submit',async event=>{
   if(form.dataset.uiPending){event.preventDefault();return}
   if(form.dataset.uiConfirmed){delete form.dataset.uiConfirmed;afterAllowed();busy(form,event.submitter,label);return}
   event.preventDefault();if(form.dataset.uiConfirming||!valid(form))return;
   form.dataset.uiConfirming='true';try{if(await before(event)){form.dataset.uiConfirmed='true';const submitter=event.submitter;const timer=setTimeout(()=>{submitTimers.delete(timer);if(form.isConnected&&form.dataset.uiConfirmed&&!form.dataset.uiPending)form.requestSubmit(submitter||undefined)},0);submitTimers.add(timer)}}finally{delete form.dataset.uiConfirming}
  });
 }
 function clearSearch(input,label='Limpar busca'){
  if(!input||input.dataset.hasCampusClear)return;input.dataset.hasCampusClear='true';const holder=document.createElement('div'),button=document.createElement('button');holder.className='campus-roster-search';input.before(holder);holder.append(input);button.type='button';button.className='campus-clear-search';button.setAttribute('aria-label',label);button.textContent='×';holder.append(button);const update=()=>button.hidden=!input.value;input.addEventListener('input',update);button.addEventListener('click',()=>{input.value='';input.dispatchEvent(new Event('input',{bubbles:true}));input.focus()});update();
 }
 window.addEventListener('pagehide',()=>{submitTimers.forEach(clearTimeout);submitTimers.clear()});
 window.addEventListener('pageshow',()=>document.querySelectorAll('[data-ui-pending],[data-ui-confirmed],[data-ui-confirming]').forEach(form=>{delete form.dataset.uiPending;delete form.dataset.uiConfirmed;delete form.dataset.uiConfirming;form.removeAttribute('aria-busy');form.querySelectorAll('[data-ui-submit-value]').forEach(e=>e.remove());form.querySelectorAll('[data-ui-label]').forEach(b=>{b.disabled=false;b.textContent=b.dataset.uiLabel})}));
 window.CampusActions={ask,error,valid,bindSubmit,clearSearch};
})();
