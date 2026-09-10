(() => {
  const social = document.querySelector('.social-world');
  if (social) {
    const compose = document.getElementById('socialCompose');
    social.querySelectorAll('[data-compose]').forEach(b=>b.addEventListener('click',()=>compose.showModal()));
    social.querySelectorAll('[data-close-social]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
    social.querySelectorAll('[data-mail-id]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.mailId).showModal()));
    social.querySelectorAll('[data-reply-to]').forEach(b=>b.addEventListener('click',()=>{
      b.closest('dialog').close();
      compose.querySelector('select').value = b.dataset.replyTo;
      compose.querySelector('#mailSubject').value = ('Re: ' + b.dataset.replySubject).slice(0,160);
      compose.showModal();
      compose.querySelector('textarea').focus();
    }));
    let folder = 'inbox';
    const rows = [...social.querySelectorAll('.mail-row')], search = document.getElementById('mailSearch');
    const normalize = s => s.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
    function filter() {
      rows.forEach(row => {
        const matches = folder === 'all' || (folder === 'unread' ? row.dataset.mailUnread === 'yes' : row.dataset.mailKind === folder);
        row.hidden = !matches || !normalize(row.dataset.mailSearch).includes(normalize(search.value));
      });
      document.getElementById('mailEmpty').hidden = rows.some(row=>!row.hidden);
    }
    social.querySelectorAll('[data-mail-filter]').forEach(b=>b.addEventListener('click',()=>{
      folder=b.dataset.mailFilter;
      social.querySelectorAll('[data-mail-filter]').forEach(other=>other.setAttribute('aria-pressed',String(b===other)));
      filter();
    }));
    search.addEventListener('input',filter); filter();
    compose.querySelector('form').addEventListener('submit', event=>{
      for (const input of compose.querySelectorAll('input[name=subject],textarea')) {
        if (!input.value.trim()) { event.preventDefault(); input.setCustomValidity('Preencha este campo.'); input.reportValidity(); break; }
      }
    });
    compose.querySelectorAll('input,textarea').forEach(input=>input.addEventListener('input',()=>input.setCustomValidity('')));
  }
  const studio = document.getElementById('identityWorld');
  if (studio) {
    const form=document.getElementById('identityForm'), avatar=document.getElementById('liveAvatar');
    const saved=Object.fromEntries(new FormData(form));
    let dirty=false, submitting=false;
    function preview() {
      const data=Object.fromEntries(new FormData(form));
      ['skin','hair','shirt'].forEach(key=>studio.style.setProperty('--'+key,data[key]));
      ['appearance','hairstyle','outfit','bottom','shoes','accessory'].forEach(key=>avatar.dataset[key]=data[key]);
      dirty=Object.keys(saved).some(key=>data[key]!==saved[key]);
      document.getElementById('identityStatus').textContent=dirty?'Prévia alterada. Salve para aplicar ao Lobby.':'Esta é sua identidade salva.';
    }
    form.addEventListener('change',preview);
    form.addEventListener('reset',()=>setTimeout(preview,0));
    form.addEventListener('submit',()=>{submitting=true;});
    document.getElementById('avatarRandom').addEventListener('click',()=>{
      ['skin','hair','shirt','accessory','appearance','hairstyle','outfit','bottom','shoes'].forEach(key=>{
        const choices=[...form.querySelectorAll('input[name='+key+']')];
        choices[Math.floor(Math.random()*choices.length)].checked=true;
      }); preview();
    });
    function category(value) {
      form.querySelectorAll('[data-atelier-group]').forEach(field=>field.hidden=field.dataset.atelierGroup!==value);
      form.querySelectorAll('[data-atelier]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.atelier===value)));
    }
    form.querySelectorAll('[data-atelier]').forEach(button=>button.addEventListener('click',()=>category(button.dataset.atelier)));
    category('appearance');
    document.getElementById('avatarZoom').addEventListener('click',function(){
      const active=studio.classList.toggle('identity-zoom');
      this.setAttribute('aria-pressed',String(active)); this.textContent=active?'− Afastar':'＋ Aproximar';
    });
    document.getElementById('avatarMotion').addEventListener('click',function(){
      const paused=studio.classList.toggle('identity-paused');
      this.setAttribute('aria-pressed',String(paused));this.textContent=paused?'Retomar animação':'Pausar animação';
    });
    const syncVisibility=()=>studio.classList.toggle('identity-page-hidden',document.hidden);
    document.addEventListener('visibilitychange',syncVisibility);
    syncVisibility();
    window.addEventListener('beforeunload',event=>{if(dirty&&!submitting){event.preventDefault();event.returnValue='';}});
  }
})();
