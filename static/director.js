(() => {
  const root = document.querySelector(".director-world");
  if (!root) return;
  const openers = new WeakMap();
  root.querySelectorAll("[data-open-director]").forEach((b) =>
    b.addEventListener("click", () => {
      const d = document.getElementById(b.dataset.openDirector);
      openers.set(d, b);
      d.showModal();
    }),
  );
  root
    .querySelectorAll("[data-close-director]")
    .forEach((b) =>
      b.addEventListener("click", () => b.closest("dialog").close()),
    );
  root
    .querySelectorAll("dialog")
    .forEach((d) => d.addEventListener("close", () => openers.get(d)?.focus()));
  const confirmation = document.getElementById("directorConfirmation");
  let awaiting = null;
  confirmation
    ?.querySelector("[data-confirm-cancel]")
    .addEventListener("click", () => confirmation.close());
  confirmation?.addEventListener("close", () => {
    awaiting?.submitter?.focus();
    awaiting = null;
  });
  confirmation
    ?.querySelector("[data-confirm-accept]")
    .addEventListener("click", () => {
      const target = awaiting;
      confirmation.close();
      if (target) {
        target.form.dataset.confirmed = "1";
        target.form.requestSubmit(target.submitter);
      }
    });
  root.querySelectorAll("form").forEach((form) => {
    form.noValidate = true;
    form.addEventListener("submit", (event) => {
      if (form.dataset.busy) {
        event.preventDefault();
        return;
      }
      const fields = [
        ...form.querySelectorAll('input:not([type="hidden"]),select'),
      ];
      fields.forEach((i) => i.removeAttribute("aria-invalid"));
      const invalid = fields.find(
        (i) => !i.disabled && !i.closest("[hidden]") && !i.validity.valid,
      );
      if (invalid) {
        event.preventDefault();
        let e = form.querySelector("[data-form-error]");
        if (!e) {
          e = document.createElement("p");
          e.className = "director-error";
          e.dataset.formError = "1";
          e.setAttribute("role", "alert");
          e.id = "formError" + [...root.querySelectorAll("form")].indexOf(form);
          form.prepend(e);
        }
        e.textContent =
          invalid.type === "email"
            ? "Informe um e-mail válido."
            : "Confira o campo indicado e preencha os dados solicitados.";
        invalid.setAttribute("aria-invalid", "true");
        invalid.setAttribute("aria-describedby", e.id);
        invalid.focus();
        return;
      }
      if (form.dataset.directorConfirm && !form.dataset.confirmed) {
        event.preventDefault();
        if (!confirmation) return;
        awaiting = { form, submitter: event.submitter };
        document.getElementById("directorConfirmationText").textContent =
          form.dataset.directorConfirm;
        confirmation.showModal();
        confirmation.querySelector("[data-confirm-cancel]").focus();
        return;
      }
      delete form.dataset.confirmed;
      form.dataset.busy = "1";
      form.setAttribute("aria-busy", "true");
      form
        .querySelectorAll('button[type="submit"],button:not([type])')
        .forEach((b) => {
          b.disabled = true;
        });
    });
    form.querySelectorAll('input[type="password"]').forEach((input) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "director-secondary";
      b.textContent = "Mostrar senha";
      b.setAttribute("aria-label", b.textContent);
      b.setAttribute("aria-pressed", "false");
      input.closest("label")?.insertAdjacentElement("afterend", b);
      b.addEventListener("click", () => {
        const show = input.type === "password";
        input.type = show ? "text" : "password";
        b.textContent = show ? "Ocultar senha" : "Mostrar senha";
        b.setAttribute("aria-label", b.textContent);
        b.setAttribute("aria-pressed", String(show));
      });
    });
  });
  window.addEventListener("pageshow", () =>
    root.querySelectorAll("form[data-busy]").forEach((f) => {
      delete f.dataset.busy;
      f.removeAttribute("aria-busy");
      f.querySelectorAll('button[type="submit"],button:not([type])').forEach(
        (b) => {
          b.disabled = false;
        },
      );
    }),
  );
  const search = root.querySelector("[data-directory-search]"),
    role = root.querySelector("[data-directory-role]"),
    clear = root.querySelector("[data-directory-clear]");
  if (search) {
    const rows = [...root.querySelectorAll("[data-directory-item]")];
    const norm = (s) =>
      s
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase();
    function filter() {
      let count = 0;
      rows.forEach((r) => {
        r.hidden =
          !norm(r.dataset.directoryItem).includes(norm(search.value)) ||
          (!!role.value && r.dataset.role !== role.value);
        if (!r.hidden) count++;
      });
      root.querySelector("[data-directory-count]").textContent =
        count + " de " + rows.length + " contas";
      root.querySelector("[data-directory-empty]").hidden = count > 0;
      if (clear) clear.hidden = !search.value;
    }
    search.addEventListener("input", filter);
    role.addEventListener("change", filter);
    clear?.addEventListener("click", () => {
      search.value = "";
      filter();
      search.focus();
    });
    filter();
  }
  const retry = document.getElementById("directorRetry");
  if (retry) {
    const data = JSON.parse(retry.content.textContent);
    const forms = [...root.querySelectorAll("form")].filter(
      (f) => f.elements.namedItem("action")?.value === data.action,
    );
    const form =
      forms.find(
        (f) =>
          (data.username && f.elements.username?.value === data.username) ||
          (data.invitation_id &&
            f.elements.invitation_id?.value === data.invitation_id) ||
          (data.class_name && f.elements.class_name?.value === data.class_name),
      ) || forms.find((f) => !f.elements.username?.value);
    if (form) {
      Object.entries(data).forEach(([k, v]) => {
        const input = form.elements.namedItem(k);
        if (input) input.value = v;
      });
      form.closest("details")?.setAttribute("open", "");
      const dialog = form.closest("dialog");
      if (dialog) {
        const note = document.createElement("p");
        note.className = "director-error";
        note.setAttribute("role", "alert");
        note.tabIndex = -1;
        note.textContent =
          root.querySelector("[role=alert]").textContent +
          " Digite novamente sua senha para confirmar.";
        form.prepend(note);
        dialog.showModal();
        note.focus();
      }
    }
  }
  const identity = document.getElementById("identityRole");
  if (identity) {
    function student() {
      const field = document.getElementById("studentLink");
      field.hidden = !["aluno", "responsavel"].includes(identity.value);
      field.querySelector("select").required = !field.hidden;
    }
    identity.addEventListener("change", student);
    student();
  }
})();
