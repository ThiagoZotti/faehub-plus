(() => {
  const body=document.body, scene=document.querySelector('.arrival-scene'), intro=document.getElementById('arrivalIntro'), terminal=document.getElementById('arrivalTerminal');
  const form=document.getElementById('arrivalForm'), error=document.getElementById('arrivalError');
  const credential=document.getElementById('credential');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let pending=false, audioContext, master, soundOn=false;
  function openGate(direct=false) {
    body.classList.add('gate-open'); intro.hidden=true;terminal.hidden=false;
    body.classList.toggle('direct-entry',direct);
    document.getElementById('usuario').focus({preventScroll:true});
  }
  document.getElementById('enterCampus').addEventListener('click',()=>openGate());
  document.getElementById('skipArrival').addEventListener('click',()=>openGate(true));
  document.getElementById('backArrival').addEventListener('click',()=>{
    if(pending)return;
    body.classList.remove('gate-open','direct-entry');terminal.hidden=true;intro.hidden=false;
    document.getElementById('enterCampus').focus();
  });
  try {
    if(localStorage.getItem('campus-light')==='1'){body.classList.add('light-mode');document.getElementById('lightToggle').setAttribute('aria-pressed','true');}
  }catch(_){}
  if(error.textContent.trim())openGate(true);
  const roles={aluno:['Estudante','01','#a7ecdc'],professor:['Professor','02','#afcaff'],diretor:['Diretor','03','#e6d5a9']};
  function roleChange(role){
    const data=roles[role];
    document.getElementById('credentialRole').textContent=data[0];
    document.getElementById('roleNumber').textContent=data[1];
    body.style.setProperty('--accent',data[2]);
    document.querySelectorAll('[data-role]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.role===role)));
  }
  document.querySelectorAll('[data-role]').forEach(b=>b.addEventListener('click',()=>roleChange(b.dataset.role)));
  const roleButtons=[...document.querySelectorAll('.credential-tabs [data-role]')];
  function syncRoleTabs(){roleButtons.forEach(button=>button.tabIndex=button.getAttribute('aria-pressed')==='true'?0:-1);}
  document.querySelector('.credential-tabs').addEventListener('click',()=>queueMicrotask(syncRoleTabs));
  document.querySelector('.credential-tabs').addEventListener('keydown',event=>{
    const current=event.target.closest('[data-role]');
    if(!current||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key))return;
    event.preventDefault();const index=roleButtons.indexOf(current);
    const next=event.key==='Home'?0:event.key==='End'?roleButtons.length-1:
      (index+(event.key==='ArrowLeft'||event.key==='ArrowUp'?-1:1)+roleButtons.length)%roleButtons.length;
    roleButtons[next].focus();roleButtons[next].click();
  });
  syncRoleTabs();
  document.querySelectorAll('[data-demo-user]').forEach(b=>b.addEventListener('click',()=>{
    document.getElementById('usuario').value=b.dataset.demoUser;
    document.getElementById('senha').value=b.dataset.demoPassword;
    roleChange(b.dataset.demoUser==='gilberto'?'diretor':b.dataset.demoUser==='aline'?'professor':'aluno');
    syncRoleTabs();
    document.getElementById('senha').focus();
  }));
  document.getElementById('revealPassword').addEventListener('click',function(){
    const input=document.getElementById('senha'), show=input.type==='password';
    input.type=show?'text':'password';this.textContent=show?'Ocultar':'Mostrar';this.setAttribute('aria-label',show?'Ocultar senha':'Mostrar senha');
  });
  document.getElementById('lightToggle').addEventListener('click',function(){
    const active=body.classList.toggle('light-mode');this.setAttribute('aria-pressed',String(active));
    try{localStorage.setItem('campus-light',active?'1':'0');}catch(_){}
  });
  let frame;
  window.addEventListener('pointermove',e=>{
    if(reduced.matches||body.classList.contains('light-mode')||e.pointerType!=='mouse')return;
    cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{
      const x=e.clientX/innerWidth-.5,y=e.clientY/innerHeight-.5;
      scene.style.setProperty('--mx',(x*14)+'px');
      scene.style.setProperty('--my',(y*10)+'px');
      scene.style.setProperty('--cloud-x',(x*-8)+'px');
      scene.style.setProperty('--cloud-y',(y*-5)+'px');
      scene.style.setProperty('--beam-x',(x*9)+'px');
      credential.style.setProperty('--tilt',(x*3)+'deg');
      credential.style.setProperty('--glint-x',(x*18)+'px');
    });
  },{passive:true});
  function clock(){
    const now=new Date();
    const hour=Number(new Intl.DateTimeFormat('en-US',{timeZone:'America/Sao_Paulo',hour:'numeric',hourCycle:'h23'}).format(now));
    body.classList.toggle('daylight',hour>=6&&hour<18);
    document.getElementById('campusClock').textContent='SANTA CRUZ / '+new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',hour:'2-digit',minute:'2-digit'}).format(now)+' · '+(hour>=6&&hour<18?'LUZ DIURNA':'LUZ NOTURNA');
  }
  clock();const clockTimer=setInterval(clock,60000);
  document.getElementById('soundToggle').addEventListener('click',async function(){
    try{
      if(!audioContext){
        audioContext=new (window.AudioContext||window.webkitAudioContext)();
        master=audioContext.createGain();master.gain.value=0;master.connect(audioContext.destination);
        [130.81,196,261.63].forEach(frequency=>{const osc=audioContext.createOscillator();osc.type='sine';osc.frequency.value=frequency;osc.connect(master);osc.start();});
      }
      await audioContext.resume();soundOn=!soundOn;
      master.gain.setTargetAtTime(soundOn?.012:0,audioContext.currentTime,.3);
      this.textContent=soundOn?'Som: ligado':'Som: desligado';this.setAttribute('aria-pressed',String(soundOn));
    }catch(_){this.textContent='Som indisponível';this.disabled=true;}
  });
  document.addEventListener('visibilitychange',()=>{if(audioContext){if(document.hidden)audioContext.suspend();else if(soundOn)audioContext.resume();}});
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(pending)return;
    if(!document.getElementById('usuario').value.trim()){error.textContent='Preencha o usuário.';return;}
    pending=true;error.textContent='';const button=document.getElementById('authenticate');
    button.disabled=true;button.querySelector('span').textContent='Verificando sua conta…';form.setAttribute('aria-busy','true');
    try{
      const response=await fetch(form.action,{method:'POST',body:new FormData(form),headers:{'X-Campus-Login':'1'},credentials:'same-origin'});
      const result=await response.json();
      if(!response.ok){error.textContent=result.error||'Não foi possível entrar.';document.getElementById('senha').focus();return;}
      document.getElementById('senha').value='';
      form.hidden=true;document.querySelector('.credential-tabs').hidden=true;document.querySelector('.arrival-demo').hidden=true;
      document.getElementById('confirmedName').textContent=result.name;
      document.getElementById('confirmedRole').textContent={aluno:'Aluno',professor:'Professor',diretor:'Diretor'}[result.role]||'';
      document.getElementById('credentialConfirmed').hidden=false;
      const enter = document.querySelector('#credentialConfirmed a');
      enter.href = result.destination;
      enter.focus({preventScroll:true});
    }catch(_){error.textContent='Não foi possível confirmar o acesso. Confira a conexão e tente novamente.';}
    finally{pending=false;button.disabled=false;button.querySelector('span').textContent='Identificar e entrar';form.removeAttribute('aria-busy');}
  });
  // The final approach starts only after the user explicitly enters the campus.
  const campusLink=document.querySelector('#credentialConfirmed a');
  let departureTimer=null;
  campusLink.addEventListener('click',event=>{
    if(event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||reduced.matches||body.classList.contains('light-mode'))return;
    event.preventDefault();
    if(departureTimer!==null)return;
    body.classList.add('departing');
    campusLink.setAttribute('aria-busy','true');
    departureTimer=setTimeout(()=>location.assign(campusLink.href),850);
  });
  window.addEventListener('pageshow',()=>{
    clearTimeout(departureTimer);departureTimer=null;
    body.classList.remove('departing');campusLink.removeAttribute('aria-busy');
  });
  window.addEventListener('pagehide',()=>{clearTimeout(departureTimer);clearInterval(clockTimer);cancelAnimationFrame(frame);audioContext?.close();});
})();
