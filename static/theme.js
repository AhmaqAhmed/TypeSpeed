(function () {
  const KEY = 'ts-theme';

  // inject styles once
  const style = document.createElement('style');
  style.textContent = `
    .theme-toggle {
      position: fixed;
      bottom: 1.4rem;
      right: 1.4rem;
      z-index: 9999;
      width: 44px;
      height: 44px;
      border-radius: 50%;
      border: none;
      cursor: pointer;
      font-size: 1.3rem;
      line-height: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 14px rgba(0,0,0,0.35);
      transition: background .2s, transform .15s, box-shadow .2s;
      /* light mode: dark pill so it's visible on light bg */
      background: #1a1a2e;
      color: #f0e68c;
    }
    [data-theme="dark"] .theme-toggle {
      /* dark mode: bright pill so it's visible on dark bg */
      background: #f0e68c;
      color: #1a1a2e;
    }
    .theme-toggle:hover {
      transform: scale(1.12);
      box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }
  `;
  document.head.appendChild(style);

  function apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.querySelectorAll('.theme-toggle').forEach(btn => {
      btn.innerHTML = theme === 'dark' ? '&#9728;' : '&#9790;';
      btn.title = theme === 'dark' ? 'Light mode' : 'Dark mode';
    });
    // hide old inline theme-btn topbar buttons if present
    document.querySelectorAll('.theme-btn').forEach(b => b.style.display = 'none');
  }

  function toggle() {
    const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    localStorage.setItem(KEY, next);
    apply(next);
  }

  // apply immediately before paint
  apply(localStorage.getItem(KEY) || 'light');

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.createElement('button');
    btn.className = 'theme-toggle';
    btn.addEventListener('click', toggle);
    document.body.appendChild(btn);
    apply(localStorage.getItem(KEY) || 'light');
  });
})();