(function () {
  const AUTO_DISMISS_MS = 3800;
  const initializedToasts = new WeakSet();

  function closeToast(toast) {
    if (!toast) return;
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-6px)";
    setTimeout(() => toast.remove(), 180);
  }

  function initToasts(root) {
    (root || document).querySelectorAll("[data-toast]").forEach((toast) => {
      if (initializedToasts.has(toast)) return;
      initializedToasts.add(toast);
      window.setTimeout(() => closeToast(toast), AUTO_DISMISS_MS);
    });
  }

  document.addEventListener("click", (event) => {
    const closeBtn = event.target.closest("[data-toast-close]");
    if (!closeBtn) return;
    const toast = closeBtn.closest("[data-toast]");
    closeToast(toast);
  });

  initToasts(document);
  window.addEventListener("qazsound:navigation:render", () => initToasts(document));
})();
