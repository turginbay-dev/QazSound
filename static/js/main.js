(function () {
  const AUTO_DISMISS_MS = 3800;

  function closeToast(toast) {
    if (!toast) return;
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-6px)";
    setTimeout(() => toast.remove(), 180);
  }

  document.querySelectorAll("[data-toast]").forEach((toast) => {
    const closeBtn = toast.querySelector("[data-toast-close]");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => closeToast(toast));
    }

    window.setTimeout(() => closeToast(toast), AUTO_DISMISS_MS);
  });
})();
