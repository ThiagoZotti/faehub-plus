(() => {
 const ui=window.CampusActions;if(!ui)return;
 document.querySelectorAll('[data-reveal]').forEach(button=>button.addEventListener('click',()=>{const input=document.getElementById(button.dataset.reveal),show=input.type==='password';input.type=show?'text':'password';button.textContent=show?'Ocultar':'Mostrar';button.setAttribute('aria-label',show?'Ocultar valor':'Mostrar valor');button.setAttribute('aria-pressed',String(show));}));
 document.querySelectorAll('[data-security-form]').forEach(form=>ui.bindSubmit(form,{label:'Confirmando…',before:async()=>{
  const action=form.elements.action?.value;
  if(['disable','regenerate'].includes(action))return ui.ask(action==='disable'?'O login deixará de pedir o código do celular. Todas as outras sessões serão encerradas. Desativar?':'Os códigos antigos deixarão de funcionar. Guarde a nova lista após confirmar. Todas as outras sessões serão encerradas.',{title:'Alterar segurança da conta?',action:'Confirmar alteração',warning:true});
  return true;
 }}));
 const error=document.getElementById('securityServerError');error?.focus();
 document.querySelector('[data-download-codes]')?.addEventListener('click',()=>{const codes=[...document.querySelectorAll('#recoveryCodes code')].map(el=>el.textContent).join('\n'),url=URL.createObjectURL(new Blob(['FaeHub+ — códigos de recuperação\nCada código é de uso único, junto com sua senha. Guarde em local privado.\n\n'+codes],{type:'text/plain;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download='faehub-codigos-recuperacao.txt';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
})();
