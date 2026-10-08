(() => {
  const dialog = document.getElementById("profilePhotoDialog");
  const removeDialog = document.getElementById("profilePhotoRemoveDialog");
  if (!dialog || !removeDialog) return;
  const form = document.getElementById("profilePhotoForm");
  const input = document.getElementById("profilePhotoInput");
  const saveButton = form.querySelector("[type=submit]");
  const status = document.getElementById("profilePhotoStatus");
  const preview = document.getElementById("profilePhotoPreview");
  const initials = document.getElementById("profilePhotoPreviewInitials");
  let currentUrl =
    document.querySelector("[data-profile-photo]")?.getAttribute("src") || "";
  let prepared = null,
    previewUrl = null,
    pending = false,
    selection = 0,
    opener = null;

  function showPhoto(image, fallback, url) {
    image.hidden = !url;
    fallback.hidden = !!url;
    if (url) image.src = url;
    else image.removeAttribute("src");
  }
  function updatePhotos(url) {
    currentUrl = url;
    document.querySelectorAll(".campus-account-photo").forEach((slot) => {
      showPhoto(
        slot.querySelector("[data-profile-photo]"),
        slot.querySelector("[data-profile-initials]"),
        url,
      );
    });
    document.querySelectorAll("[data-remove-profile]").forEach((button) => {
      button.hidden = !url;
    });
  }
  function message(text, error = false) {
    status.textContent = text;
    status.classList.toggle("is-error", error);
  }
  document.querySelectorAll("[data-profile-photo]").forEach((image) =>
    image.addEventListener("error", () => {
      image.hidden = true;
      image.parentElement.querySelector("[data-profile-initials]").hidden =
        false;
    }),
  );
  document.querySelectorAll("[data-open-profile]").forEach((button) =>
    button.addEventListener("click", () => {
      opener = document.querySelector(".campus-account-menu > summary");
      button.closest("details").open = false;
      prepared = null;
      input.value = "";
      saveButton.disabled = true;
      message("");
      document.getElementById("profilePhotoFilename").textContent =
        "JPG ou PNG · até 5 MB";
      showPhoto(preview, initials, currentUrl);
      dialog.showModal();
      input.focus();
    }),
  );
  document
    .querySelectorAll("[data-close-profile]")
    .forEach((button) =>
      button.addEventListener("click", () => dialog.close()),
    );
  document.querySelectorAll("[data-remove-profile]").forEach((button) =>
    button.addEventListener("click", () => {
      opener = document.querySelector(".campus-account-menu > summary");
      button.closest("details").open = false;
      removeDialog.querySelector(".profile-photo-status").textContent = "";
      removeDialog.showModal();
      removeDialog.querySelector("[data-cancel-profile-remove]").focus();
    }),
  );
  document
    .querySelector("[data-cancel-profile-remove]")
    .addEventListener("click", () => removeDialog.close());
  [dialog, removeDialog].forEach((modal) => {
    modal.addEventListener("cancel", (event) => {
      if (pending) event.preventDefault();
    });
    modal.addEventListener("close", () => {
      selection++;
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = null;
      prepared = null;
      opener?.focus();
    });
  });

  input.addEventListener("change", async () => {
    const activeSelection = ++selection;
    const file = input.files?.[0];
    prepared = null;
    saveButton.disabled = true;
    if (!file) return;
    try {
      if (!["image/jpeg", "image/png"].includes(file.type))
        throw new Error("Escolha uma foto em JPG ou PNG.");
      if (!file.size || file.size > 5 * 1024 * 1024)
        throw new Error("Escolha uma foto de até 5 MB.");
      message("Preparando a prévia…");
      const bitmap = await createImageBitmap(file, {
        imageOrientation: "from-image",
      });
      let blob;
      try {
        if (bitmap.width * bitmap.height > 16_000_000)
          throw new Error(
            "Esta imagem é muito grande. Escolha uma versão menor.",
          );
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = 320;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, 320, 320);
        const side = Math.min(bitmap.width, bitmap.height);
        ctx.drawImage(
          bitmap,
          (bitmap.width - side) / 2,
          (bitmap.height - side) / 2,
          side,
          side,
          0,
          0,
          320,
          320,
        );
        blob = await new Promise((resolve) =>
          canvas.toBlob(resolve, "image/jpeg", 0.86),
        );
      } finally {
        bitmap.close();
      }
      if (activeSelection !== selection || !dialog.open) return;
      if (!blob)
        throw new Error(
          "Não foi possível preparar esta foto. Escolha outra imagem.",
        );
      prepared = new File([blob], "perfil.jpg", { type: "image/jpeg" });
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = URL.createObjectURL(blob);
      showPhoto(preview, initials, previewUrl);
      document.getElementById("profilePhotoFilename").textContent = file.name;
      message("Confira a prévia e salve sua foto.");
      saveButton.disabled = false;
    } catch (error) {
      if (activeSelection === selection)
        message(
          error.name === "Error"
            ? error.message
            : "Não foi possível abrir esta foto. Escolha um JPG ou PNG válido.",
          true,
        );
    }
  });

  async function submitPhoto(event) {
    event.preventDefault();
    if (pending) return;
    const activeForm = event.currentTarget;
    if (activeForm === form && !prepared) return;
    const activeDialog = activeForm.closest("dialog");
    const feedback = activeForm.querySelector(".profile-photo-status");
    const body = new FormData(activeForm);
    if (activeForm === form) body.set("photo", prepared, "perfil.jpg");
    pending = true;
    activeForm.setAttribute("aria-busy", "true");
    const controls = [
      ...activeForm.querySelectorAll("button,input[type=file]"),
    ];
    controls.forEach((control) => {
      control.disabled = true;
    });
    feedback.classList.remove("is-error");
    feedback.textContent = "Salvando…";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(activeForm.getAttribute("action"), {
        method: "POST",
        body,
        credentials: "same-origin",
        signal: controller.signal,
      });
      if (response.redirected)
        throw new Error(
          "Sua sessão expirou. Atualize a página e tente novamente.",
        );
      if (!response.headers.get("Content-Type")?.includes("application/json")) {
        throw new Error(
          "Não foi possível salvar sua foto. Confira a conexão e tente novamente.",
        );
      }
      const result = await response.json();
      if (!response.ok)
        throw new Error(result.error || "Não foi possível salvar sua foto.");
      updatePhotos(result.url || "");
      activeDialog.close();
    } catch (error) {
      feedback.textContent =
        error.name === "AbortError"
          ? "Não foi possível confirmar o envio. Atualize a página ou tente salvar novamente."
          : error.name === "Error"
            ? error.message
            : "Não foi possível salvar. Confira a conexão e tente novamente.";
      feedback.classList.add("is-error");
    } finally {
      clearTimeout(timeout);
      pending = false;
      activeForm.removeAttribute("aria-busy");
      controls.forEach((control) => {
        control.disabled = false;
      });
      saveButton.disabled = !prepared;
    }
  }
  form.addEventListener("submit", submitPhoto);
  document
    .getElementById("profilePhotoRemoveForm")
    .addEventListener("submit", submitPhoto);
})();
