(()=>{
  document.querySelectorAll('[data-reveal]').forEach(button=>button.addEventListener('click',()=>{
    const input=document.getElementById(button.dataset.reveal),show=input.type==='password';
    input.type=show?'text':'password';button.textContent=show?'Ocultar':'Mostrar';
    const label=button.dataset.reveal==='code'?'código':button.dataset.reveal==='confirm_password'?'confirmação de senha':'senha';
    button.setAttribute('aria-label',(show?'Ocultar ':'Mostrar ')+label);button.setAttribute('aria-pressed',String(show));
  }));
  document.querySelector('[data-recovery-error]')?.focus();
})();
