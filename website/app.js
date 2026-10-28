(() => {
  const menuButton = document.querySelector('#menuToggle');
  const menu = document.querySelector('#mobileMenu');
  if (menuButton && menu) {
    const closeMenu = () => {
      menu.hidden = true;
      menuButton.setAttribute('aria-expanded', 'false');
      menuButton.setAttribute('aria-label', 'Открыть меню');
    };
    menuButton.addEventListener('click', () => {
      const opening = menu.hidden;
      menu.hidden = !opening;
      menuButton.setAttribute('aria-expanded', String(opening));
      menuButton.setAttribute('aria-label', opening ? 'Закрыть меню' : 'Открыть меню');
    });
    menu.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !menu.hidden) {
        closeMenu();
        menuButton.focus();
      }
    });
    document.addEventListener('click', event => {
      if (!menu.hidden && !menu.contains(event.target) && !menuButton.contains(event.target)) closeMenu();
    });
  }
  document.querySelector('#year').textContent = new Date().getFullYear();
})();