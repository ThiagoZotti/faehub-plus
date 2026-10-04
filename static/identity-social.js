(() => {
  const root = document.querySelector('.dm-world');
  if (!root) return;

  const dialog = document.getElementById('socialCompose');
  const search = document.getElementById('threadSearch');
  const clearSearch = root.querySelector('[data-clear-search]');
  const threadForms = [...root.querySelectorAll('[data-thread-search]')];
  const searchEmpty = document.getElementById('threadEmpty');
  const stream = document.getElementById('dmStream');
  const normalize = value => value.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g, '');

  const openDialog = () => {
    if (!dialog) return;
    dialog.showModal();
    dialog.querySelector('select')?.focus();
  };

  root.querySelectorAll('[data-compose]').forEach(button => button.addEventListener('click', openDialog));
  root.querySelectorAll('[data-close-social]').forEach(button => button.addEventListener('click', () => dialog?.close()));
  dialog?.addEventListener('click', event => {
    if (event.target === dialog) dialog.close();
  });

  const filterThreads = () => {
    if (!search) return;
    const query = normalize(search.value.trim());
    let visible = 0;
    threadForms.forEach(form => {
      const matches = normalize(form.dataset.threadSearch || '').includes(query);
      form.hidden = !matches;
      if (matches) visible += 1;
    });
    if (clearSearch) clearSearch.hidden = !query;
    if (searchEmpty) searchEmpty.hidden = visible > 0 || !query;
  };

  search?.addEventListener('input', filterThreads);
  clearSearch?.addEventListener('click', () => {
    search.value = '';
    filterThreads();
    search.focus();
  });

  const removeErrors = form => {
    form.querySelectorAll('.compose-error').forEach(error => error.remove());
    form.querySelectorAll('[aria-invalid="true"]').forEach(field => {
      field.removeAttribute('aria-invalid');
      field.removeAttribute('aria-describedby');
    });
  };

  const showError = (field, message) => {
    const error = document.createElement('small');
    const errorId = `${field.id || field.name}-error`;
    error.id = errorId;
    error.className = 'compose-error';
    error.textContent = message;
    field.setAttribute('aria-invalid', 'true');
    field.setAttribute('aria-describedby', errorId);
    field.insertAdjacentElement('afterend', error);
  };

  root.querySelectorAll('form[novalidate]').forEach(form => form.addEventListener('submit', event => {
    if (form.matches('[data-thread-search]')) return;
    removeErrors(form);
    const required = [...form.querySelectorAll('[required]')];
    const invalid = required.filter(field => !field.value.trim());
    const body = form.querySelector('textarea[name="body"]');
    const attachment = form.querySelector('input[type="file"]');
    if (body && !body.value.trim() && !attachment?.files?.length) invalid.push(body);
    if (!invalid.length) return;
    event.preventDefault();
    invalid.forEach(field => showError(field, field.tagName === 'SELECT' ? 'Escolha uma pessoa.' : 'Escreva uma mensagem ou adicione um arquivo.'));
    invalid[0].focus();
  }));

  const autoGrow = textarea => {
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 140)}px`;
  };
  root.querySelectorAll('textarea').forEach(textarea => {
    autoGrow(textarea);
    textarea.addEventListener('input', () => autoGrow(textarea));
  });

  const formatSize = bytes => bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

  const optimizeImage = async file => {
    if (!/^image\/(jpeg|png)$/.test(file.type) || file.size < 700 * 1024) return file;
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    canvas.getContext('2d', { alpha: file.type === 'image/png' }).drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise(resolve => canvas.toBlob(resolve, file.type, file.type === 'image/jpeg' ? .82 : undefined));
    if (!blob || blob.size >= file.size) return file;
    return new File([blob], file.name, { type: file.type, lastModified: file.lastModified });
  };

  root.querySelectorAll('[data-attachment-trigger]').forEach(button => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.getAttribute('aria-controls'));
      input?.click();
    });
  });

  root.querySelectorAll('input[type="file"]').forEach(input => {
    const preview = input.closest('form')?.querySelector('[data-file-preview]');
    const image = preview?.querySelector('[data-file-preview-image]');
    const name = preview?.querySelector('[data-file-name]');
    const meta = preview?.querySelector('[data-file-meta]');
    let objectUrl = '';
    const clearPreview = () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = '';
      if (image) image.removeAttribute('src');
      if (preview) preview.hidden = true;
    };
    input.addEventListener('change', async () => {
      clearPreview();
      let file = input.files?.[0];
      if (!file || !preview) return;
      try {
        const optimized = await optimizeImage(file);
        if (optimized !== file && typeof DataTransfer !== 'undefined') {
          const transfer = new DataTransfer();
          transfer.items.add(optimized);
          input.files = transfer.files;
          file = optimized;
        }
      } catch (_) {
        // Keep the original image when browser-side optimization is unavailable.
      }
      if (name) name.textContent = file.name;
      if (meta) meta.textContent = `${file.type || 'Arquivo'} · ${formatSize(file.size)}`;
      if (image && file.type.startsWith('image/')) {
        objectUrl = URL.createObjectURL(file);
        image.src = objectUrl;
      }
      preview.hidden = false;
    });
    preview?.querySelector('[data-remove-file]')?.addEventListener('click', () => {
      input.value = '';
      clearPreview();
      input.focus();
    });
  });

  const deleteDialog = document.getElementById('deleteMessageDialog');
  let deleteTrigger = null;
  root.querySelectorAll('[data-delete-message]').forEach(button => button.addEventListener('click', () => {
    deleteTrigger = button;
    const field = deleteDialog?.querySelector('[name="message_id"]');
    if (field) field.value = button.dataset.deleteMessage;
    deleteDialog?.showModal();
    deleteDialog?.querySelector('[data-cancel-delete]')?.focus();
  }));
  deleteDialog?.querySelector('[data-cancel-delete]')?.addEventListener('click', () => deleteDialog.close());
  deleteDialog?.addEventListener('click', event => {
    if (event.target === deleteDialog) deleteDialog.close();
  });
  deleteDialog?.addEventListener('close', () => deleteTrigger?.focus());

  const closeMessageMenus = except => {
    root.querySelectorAll('[data-message-menu]').forEach(trigger => {
      if (trigger === except) return;
      trigger.setAttribute('aria-expanded', 'false');
      const popover = trigger.nextElementSibling;
      if (popover) {
        popover.hidden = true;
        popover.classList.remove('opens-up');
      }
    });
  };
  root.querySelectorAll('[data-message-menu]').forEach(trigger => trigger.addEventListener('click', event => {
    event.stopPropagation();
    const opening = trigger.getAttribute('aria-expanded') !== 'true';
    closeMessageMenus(trigger);
    trigger.setAttribute('aria-expanded', String(opening));
    const popover = trigger.nextElementSibling;
    if (popover) {
      popover.hidden = !opening;
      popover.classList.remove('opens-up');
      if (opening) {
        const stream = trigger.closest('.dm-stream');
        const boundary = stream?.getBoundingClientRect() || document.documentElement.getBoundingClientRect();
        const triggerBox = trigger.getBoundingClientRect();
        const popoverBox = popover.getBoundingClientRect();
        const roomBelow = boundary.bottom - triggerBox.bottom;
        const roomAbove = triggerBox.top - boundary.top;
        if (roomBelow < popoverBox.height + 12 && roomAbove > roomBelow) {
          popover.classList.add('opens-up');
        }
      }
    }
  }));
  document.addEventListener('click', event => {
    if (!event.target.closest('.dm-message-menu')) closeMessageMenus();
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const openTrigger = root.querySelector('[data-message-menu][aria-expanded="true"]');
    if (!openTrigger) return;
    closeMessageMenus();
    openTrigger.focus();
  });
  root.querySelector('.dm-stream')?.addEventListener('scroll', () => closeMessageMenus(), { passive: true });

  const replyField = root.querySelector('.dm-composer [name="reply_to_id"]');
  const replyPreview = root.querySelector('[data-reply-preview]');
  const composerBody = document.getElementById('threadBody');
  root.querySelectorAll('[data-reply-message]').forEach(button => button.addEventListener('click', () => {
    const bubble = button.closest('[data-message-id]');
    if (!replyField || !replyPreview || !bubble) return;
    replyField.value = button.dataset.replyMessage;
    replyPreview.querySelector('strong').textContent = `Respondendo a ${button.dataset.replyAuthor}`;
    replyPreview.querySelector('small').textContent = bubble.dataset.messageBody || 'Imagem ou arquivo';
    replyPreview.hidden = false;
    composerBody?.focus();
    closeMessageMenus();
  }));
  replyPreview?.querySelector('[data-cancel-reply]')?.addEventListener('click', () => {
    replyField.value = '';
    replyPreview.hidden = true;
    composerBody?.focus();
  });

  const editDialog = document.getElementById('editMessageDialog');
  root.querySelectorAll('[data-edit-message]').forEach(button => button.addEventListener('click', () => {
    const bubble = button.closest('[data-message-id]');
    if (!editDialog || !bubble) return;
    editDialog.querySelector('[name="message_id"]').value = button.dataset.editMessage;
    editDialog.querySelector('[name="body"]').value = bubble.dataset.messageBody || '';
    editDialog.showModal();
    editDialog.querySelector('[name="body"]').focus();
    closeMessageMenus();
  }));
  editDialog?.querySelector('[data-cancel-edit]')?.addEventListener('click', () => editDialog.close());
  editDialog?.addEventListener('click', event => {
    if (event.target === editDialog) editDialog.close();
  });

  const liveNotice = root.querySelector('[data-live-notice]');
  liveNotice?.addEventListener('click', () => location.reload());
  if ('EventSource' in window) {
    const source = new EventSource('/api/mensagens/eventos');
    source.addEventListener('messages', event => {
      const isWriting = Boolean(composerBody?.value.trim()) || Boolean(replyField?.value);
      if (document.visibilityState === 'visible' && !isWriting) location.reload();
      else if (liveNotice) liveNotice.hidden = false;
    });
    window.addEventListener('pagehide', () => source.close(), { once: true });
  }

  filterThreads();
  if (stream) stream.scrollTop = stream.scrollHeight;
})();
