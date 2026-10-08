(() => {
  const directionKey = 'faehub:navigation-direction';
  const destinationKey = 'faehub:navigation-destination';
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');

  const storageRead = key => {
    try {
      const value = sessionStorage.getItem(key);
      sessionStorage.removeItem(key);
      return value;
    } catch (_) { return null; }
  };

  const incomingDirection = storageRead(directionKey);
  const incomingDestination = storageRead(destinationKey);
  if (incomingDirection === 'previous' || incomingDirection === 'next') {
    document.documentElement.dataset.campusDirection = incomingDirection;
  }

  document.addEventListener('DOMContentLoaded', () => {
    const overflowMenus = [...document.querySelectorAll('.campus-more, .campus-mobile-more, .campus-account-menu')];
    document.addEventListener('click', event => overflowMenus.forEach(menu => {
      if (!menu.contains(event.target) || event.target.closest('a[href]')) menu.open = false;
    }));
    document.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      overflowMenus.filter(menu => menu.open).forEach(menu => { menu.open = false; menu.querySelector('summary').focus(); });
    });
    const tabs = [...document.querySelectorAll('.campus-tabs a')];
    const active = tabs.findIndex(link => link.hasAttribute('aria-current'));
    const destinations = new Map(tabs.map((link, index) => {
      const url = new URL(link.href, location.href);
      return [url.pathname, {index, label: link.textContent.trim()}];
    }));

    tabs[active]?.scrollIntoView({block: 'nearest', inline: 'nearest'});

    if (incomingDirection && !reduceMotion.matches) {
      const hud = document.querySelector('.campus-transition-hud');
      const label = incomingDestination || destinations.get(location.pathname)?.label;
      if (hud && label) hud.querySelector('strong').textContent = label;
      document.body.classList.add('campus-route-arrival');
      if (!('CSSViewTransitionRule' in window)) {
        document.body.classList.add('campus-fallback-arrival');
      }
    }

    const directionFor = link => {
      const explicit = link.closest('[data-direction]')?.dataset.direction;
      if (explicit === 'previous' || explicit === 'next') return explicit;
      const destination = destinations.get(new URL(link.href, location.href).pathname);
      return destination && active !== -1 && destination.index < active ? 'previous' : 'next';
    };

    document.addEventListener('click', event => {
      const link = event.target.closest('a[href]');
      if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey ||
          event.shiftKey || event.altKey || link.target || link.download) return;

      const target = new URL(link.href, location.href);
      if (target.origin !== location.origin || target.pathname === location.pathname ||
          target.pathname === '/sair' || target.hash) return;

      const direction = directionFor(link);
      const destination = destinations.get(target.pathname)?.label || link.textContent.trim();
      document.documentElement.dataset.campusDirection = direction;
      try {
        sessionStorage.setItem(directionKey, direction);
        sessionStorage.setItem(destinationKey, destination);
      } catch (_) {}
      // Preserve native navigation so unsaved forms can warn without locking the UI.
    });

    document.addEventListener('keydown', event => {
      if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey ||
          event.target.closest('input,textarea,select,[contenteditable]') || document.querySelector('dialog[open]')) return;
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      document.querySelector(`[data-direction="${event.key === 'ArrowLeft' ? 'previous' : 'next'}"]`)?.click();
    });
  });

  addEventListener('pageshow', () => {
    document.body?.classList.remove('leaving');
    setTimeout(() => document.body?.classList.remove('campus-route-arrival', 'campus-fallback-arrival'), 720);
  });
})();
