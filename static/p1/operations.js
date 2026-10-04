(()=>{
  const root=document.querySelector('.ops');if(!root)return;
  root.querySelectorAll('[data-restore-form]').forEach(template=>{
    const form=document.getElementById(template.dataset.restoreForm);const values=JSON.parse(template.content.textContent);
    Object.entries(values).forEach(([name,value])=>{const field=form?.elements.namedItem(name);if(field&&name!=='token'&&name!=='status')field.value=value??''});
  });
  root.querySelectorAll('[data-dialog-open]').forEach(button=>button.addEventListener('click',()=>document.getElementById(button.dataset.dialogOpen)?.showModal()));
  root.querySelectorAll('[data-dialog-close]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog')?.close()));
  root.querySelectorAll('dialog').forEach(dialog=>dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close()}));
  root.querySelectorAll('form').forEach(form=>{
    form.noValidate=true;
    form.addEventListener('submit',event=>{
      form.querySelectorAll('.ops-field-error').forEach(node=>node.remove());
      form.querySelectorAll('[aria-invalid]').forEach(node=>node.removeAttribute('aria-invalid'));
      const invalid=[...form.elements].filter(field=>field.willValidate&&!field.validity.valid);
      if(invalid.length){
        event.preventDefault();
        invalid.forEach((field,index)=>{
          const message=document.createElement('small');message.className='ops-field-error';
          message.id=(field.id||field.name)+'-error-'+index;
          message.textContent=field.validity.valueMissing?'Preencha este campo.':'Confira o formato e os limites deste campo.';
          field.setAttribute('aria-invalid','true');field.setAttribute('aria-describedby',message.id);
          field.after(message);
        });
        invalid[0].focus();return;
      }
      if(form.dataset.pending){event.preventDefault();return}
      form.dataset.pending='true';form.setAttribute('aria-busy','true');
      const submitter=event.submitter;
      if(submitter){
        // Disabled controls are not submitted: preserve the chosen action.
        if(submitter.name){const action=document.createElement('input');action.type='hidden';action.name=submitter.name;action.value=submitter.value;form.append(action)}
        submitter.style.minWidth=submitter.getBoundingClientRect().width+'px';
        submitter.dataset.label=submitter.textContent;submitter.disabled=true;submitter.textContent='Processando…';
      }
    });
  });
  window.addEventListener('pageshow',()=>root.querySelectorAll('form').forEach(form=>{
    delete form.dataset.pending;form.removeAttribute('aria-busy');
    form.querySelectorAll('[data-label]').forEach(button=>{button.disabled=false;button.textContent=button.dataset.label});
  }));
  root.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{
    const value=button.dataset.filter;
    button.parentElement.querySelectorAll('[data-filter]').forEach(item=>item.setAttribute('aria-selected',String(item===button)));
    root.querySelectorAll('[data-status]').forEach(item=>item.hidden=value!=='all'&&item.dataset.status!==value);
  }));
  const search=root.querySelector('[data-search]'),clearSearch=root.querySelector('[data-search-clear]');
  const updateSearch=()=>{if(!search)return;const query=search.value.trim().toLocaleLowerCase('pt-BR');root.querySelectorAll('[data-search-item]').forEach(item=>item.hidden=!item.textContent.toLocaleLowerCase('pt-BR').includes(query));if(clearSearch)clearSearch.hidden=!search.value};
  search?.addEventListener('input',updateSearch);
  clearSearch?.addEventListener('click',()=>{search.value='';updateSearch();search.focus()});
})();
