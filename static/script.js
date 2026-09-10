// FaeHub+ — apenas comportamento de interface (a lógica de negócio vive no Flask)

document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  const menuBtn = document.getElementById("mobileMenuBtn");
  const themeToggle = document.getElementById("themeToggle");
  const todayLabel = document.getElementById("todayLabel");
  const cursorAura = document.getElementById("cursorAura");

  if (todayLabel) todayLabel.textContent = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "2-digit", month: "short" }).format(new Date());
  if (localStorage.getItem("faehub-theme") === "dark") document.body.classList.add("dark-mode");
  themeToggle?.addEventListener("click", () => {
    document.body.classList.toggle("dark-mode");
    localStorage.setItem("faehub-theme", document.body.classList.contains("dark-mode") ? "dark" : "light");
  });

  // Entrada em cascata dos componentes e brilho que acompanha o cursor.
  document.querySelectorAll(".view > *").forEach((item, index) => {
    item.style.setProperty("--stagger", index);
    item.classList.add("reveal-item");
  });
  const decorativePointer=!document.body.classList.contains('campus-shell') &&
    !matchMedia('(pointer: coarse), (prefers-reduced-motion: reduce)').matches;
  if(cursorAura && decorativePointer){
    let pending=false,x=0,y=0;
    document.addEventListener('pointermove',event=>{
      x=event.clientX;y=event.clientY;
      if(pending)return;
      pending=true;requestAnimationFrame(()=>{pending=false;
        cursorAura.style.setProperty('--x',x+'px');cursorAura.style.setProperty('--y',y+'px');
      });
    },{passive:true});
  }

  // Profundidade sutil nos cards sem comprometer a leitura.
  if(decorativePointer)document.querySelectorAll(".card, .pulse__item").forEach(card => {
    card.addEventListener("pointermove", event => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty("--mx", ((event.clientX - rect.left) / rect.width * 100) + "%");
      card.style.setProperty("--my", ((event.clientY - rect.top) / rect.height * 100) + "%");
    });
  });

  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      document.querySelector(".search input, input[type='search']")?.focus();
    }
  });

  function openMenu() {
    sidebar?.classList.add("is-open");
    backdrop?.classList.add("is-open");
    menuBtn?.setAttribute("aria-expanded", "true");
  }
  function closeMenu() {
    sidebar?.classList.remove("is-open");
    backdrop?.classList.remove("is-open");
    menuBtn?.setAttribute("aria-expanded", "false");
  }

  menuBtn?.addEventListener("click", () => {
    sidebar?.classList.contains("is-open") ? closeMenu() : openMenu();
  });
  backdrop?.addEventListener("click", closeMenu);

  // Evita envios repetidos sem interferir na validação ou nas confirmações
  // específicas de cada módulo.
  const pendingForms = new Map();
  function restoreForm(form) {
    const state = pendingForms.get(form);
    if (!state) return;
    form.removeAttribute("aria-busy");
    state.forEach(({ control, html, value, disabled }) => {
      if (control.tagName === "INPUT") control.value = value;
      else control.innerHTML = html;
      control.disabled = disabled;
    });
    pendingForms.delete(form);
  }
  function markFormPending(form) {
    if (pendingForms.has(form)) return;
    const controls = [...form.querySelectorAll('button[type="submit"], button:not([type]), input[type="submit"]')]
      .filter(control => !control.closest('dialog:not([open])'));
    pendingForms.set(form, controls.map(control => ({
      control,
      html: control.innerHTML,
      value: control.value,
      disabled: control.disabled
    })));
    form.setAttribute("aria-busy", "true");
    controls.forEach(control => {
      control.disabled = true;
      if (control.tagName === "INPUT") control.value = "Salvando…";
      else control.textContent = "Salvando…";
    });
  }
  document.querySelectorAll('form[method="post" i]').forEach(form => {
    form.addEventListener("submit", event => {
      queueMicrotask(() => {
        if (!event.defaultPrevented && form.checkValidity()) markFormPending(form);
      });
    });
    form.addEventListener("invalid", () => restoreForm(form), true);
  });
  addEventListener("pageshow", () => pendingForms.forEach((_, form) => restoreForm(form)));

  // Grupos exclusivos de filtros aceitam setas, Home e End, como abas.
  const pressedGroups = [...document.querySelectorAll('[role="group"], .atelier-tabs')].filter(group => {
    const buttons = [...group.querySelectorAll(':scope > button[aria-pressed]')];
    return buttons.length > 1 && buttons.filter(button => button.getAttribute('aria-pressed') === 'true').length === 1;
  });
  pressedGroups.forEach(group => {
    const buttons = [...group.querySelectorAll(':scope > button[aria-pressed]')];
    const syncTabs = () => buttons.forEach(button => {
      button.tabIndex = button.getAttribute('aria-pressed') === 'true' ? 0 : -1;
    });
    group.addEventListener('click', event => {
      if (event.target.closest('button[aria-pressed]')) queueMicrotask(syncTabs);
    });
    group.addEventListener('keydown', event => {
      const current = event.target.closest('button[aria-pressed]');
      if (!current || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const index = buttons.indexOf(current);
      const nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 :
        (index + (event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? -1 : 1) + buttons.length) % buttons.length;
      buttons[nextIndex].focus();
      buttons[nextIndex].click();
    });
    syncTabs();
  });

  // Remove o conjunto de mensagens após a saída visual; o timeout também
  // cobre navegadores sem animações ou usuários com movimento reduzido.
  const flash = document.getElementById("flashToast");
  if (flash) {
    flash.addEventListener("animationend", (e) => {
      if (e.animationName === "toast-out" && e.target.classList.contains("flash-toast")) flash.remove();
    });
    setTimeout(() => flash.remove(), matchMedia('(prefers-reduced-motion: reduce)').matches ? 7000 : 9000);
  }
});
