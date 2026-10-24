/* Enhance Material's native section-index arrows; keep its links and checkbox navigation. */
(() => {
  function enhanceNavigation() {
    document.querySelectorAll('.md-nav__container > label[for]').forEach(control => {
      const toggle = document.getElementById(control.htmlFor);
      const link = control.parentElement.querySelector('a');
      const panel = control.parentElement.nextElementSibling;
      if (!toggle || !link || !panel || panel.tagName !== 'NAV') return;
      const title = link.textContent.trim();
      if (!panel.id) panel.id = `${toggle.id}_children`;
      if (!link.id) link.id = `${toggle.id}_index`;
      panel.setAttribute('aria-labelledby', link.id);
      control.setAttribute('role', 'button');
      control.setAttribute('aria-controls', panel.id);
      function synchronise() {
        const expanded = String(toggle.checked);
        control.setAttribute('aria-expanded', expanded);
        control.setAttribute('aria-label', `${toggle.checked ? 'Collapse' : 'Expand'} ${title}`);
        panel.setAttribute('aria-expanded', expanded);
      }
      // Handle both button keys once, before Material's label keyboard handlers.
      function buttonKey(event) {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        event.stopImmediatePropagation();
        if (event.type === 'keydown' && !event.repeat) control.click();
      }
      control.addEventListener('keydown', buttonKey, true);
      control.addEventListener('keyup', buttonKey, true);
      toggle.addEventListener('change', synchronise);
      synchronise();
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceNavigation, { once: true });
  } else {
    enhanceNavigation();
  }
})();
