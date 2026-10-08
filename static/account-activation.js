(() => {
  const openForm = document.getElementById("openInvitation");
  if (openForm) {
    const fragment = new URLSearchParams(location.hash.slice(1));
    const token = fragment.get("convite");
    // The bearer never enters the HTTP URL, referrer, analytics or localStorage.
    if (location.hash) history.replaceState(null, "", location.pathname);
    if (token && token.length >= 40 && token.length <= 100) {
      document.getElementById("invitationValue").value = token;
      document.getElementById("invitationReady").hidden = false;
      document.getElementById("openInvitationButton").disabled = false;
    }
  }
  document.querySelectorAll("[data-reveal]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.reveal);
      const reveal = input.type === "password";
      input.type = reveal ? "text" : "password";
      button.textContent = reveal ? "Ocultar" : "Mostrar";
      button.setAttribute("aria-pressed", String(reveal));
      button.setAttribute(
        "aria-label",
        `${reveal ? "Ocultar" : "Mostrar"} ${input.name === "confirmation" ? "confirmação de senha" : "senha"}`,
      );
    });
  });
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (form.dataset.busy) {
        event.preventDefault();
        return;
      }
      if (form.matches("[data-activation-form]")) {
        const password = form.elements.password;
        const confirmation = form.elements.confirmation;
        const error = document.getElementById("activationClientError");
        password.removeAttribute("aria-invalid");
        confirmation.removeAttribute("aria-invalid");
        const invalid =
          password.value.length < 15 || password.value.length > 128;
        const mismatch = password.value !== confirmation.value;
        if (invalid || mismatch) {
          event.preventDefault();
          error.hidden = false;
          error.textContent = invalid
            ? "Use uma senha entre 15 e 128 caracteres."
            : "As senhas não coincidem.";
          const target = invalid ? password : confirmation;
          target.setAttribute("aria-invalid", "true");
          target.focus();
          return;
        }
        error.hidden = true;
      }
      form.dataset.busy = "1";
      form.setAttribute("aria-busy", "true");
      form.querySelectorAll('button[type="submit"]').forEach((button) => {
        button.disabled = true;
      });
    });
  });
  window.addEventListener("pageshow", () => {
    document.querySelectorAll("form[data-busy]").forEach((form) => {
      delete form.dataset.busy;
      form.removeAttribute("aria-busy");
      form.querySelectorAll('button[type="submit"]').forEach((button) => {
        button.disabled = false;
      });
    });
  });
  document.getElementById("activationError")?.focus();
})();
