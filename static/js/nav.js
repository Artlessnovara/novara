document.addEventListener('DOMContentLoaded', () => {
  const navToggle = document.querySelector('.nav-toggle');
  const mainNav = document.querySelector('.main-nav');
  const backdrop = document.querySelector('.nav-backdrop');
  const body = document.body;

  function closeNav() {
    mainNav.classList.remove('is-open');
    backdrop.classList.remove('is-visible');
    body.classList.remove('nav-open');
    navToggle.setAttribute('aria-expanded', 'false');
  }

  if (navToggle && mainNav && backdrop) {
    navToggle.addEventListener('click', (event) => {
      // Stop the click from bubbling up to other elements
      event.stopPropagation();

      // Toggle all the necessary classes and attributes
      const isOpen = mainNav.classList.toggle('is-open');
      backdrop.classList.toggle('is-visible', isOpen);
      body.classList.toggle('nav-open', isOpen);
      navToggle.setAttribute('aria-expanded', isOpen);
    });

    backdrop.addEventListener('click', () => {
      // Only close if it's currently open
      if (mainNav.classList.contains('is-open')) {
        closeNav();
      }
    });
  }
});