(function () {
  const SHELL_SELECTOR = "main.page-shell";

  if (!window.fetch || !window.history || !document.querySelector(SHELL_SELECTOR)) {
    return;
  }

  let activeController = null;

  function dispatchRender(url) {
    window.dispatchEvent(
      new CustomEvent("qazsound:navigation:render", {
        detail: { url: String(url || window.location.href) },
      })
    );
  }

  function isEligibleLink(link, event) {
    if (!link || event.defaultPrevented) return false;
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
    if (link.target && link.target !== "_self") return false;
    if (link.hasAttribute("download")) return false;

    const rawHref = link.getAttribute("href") || "";
    if (!rawHref || rawHref.startsWith("#") || rawHref.startsWith("mailto:") || rawHref.startsWith("tel:")) {
      return false;
    }

    const targetUrl = new URL(rawHref, window.location.href);
    if (targetUrl.origin !== window.location.origin) return false;

    if (targetUrl.pathname.startsWith("/admin/") || targetUrl.pathname.startsWith("/static/") || targetUrl.pathname.startsWith("/media/")) {
      return false;
    }

    if (
      targetUrl.pathname === window.location.pathname &&
      targetUrl.search === window.location.search &&
      targetUrl.hash
    ) {
      return false;
    }

    return true;
  }

  function isEligibleGetForm(form) {
    if (!(form instanceof HTMLFormElement)) return false;
    if ((form.method || "GET").toUpperCase() !== "GET") return false;
    if (form.enctype && form.enctype.toLowerCase() !== "application/x-www-form-urlencoded") return false;

    const action = form.getAttribute("action") || window.location.href;
    const targetUrl = new URL(action, window.location.href);
    if (targetUrl.origin !== window.location.origin) return false;
    if (targetUrl.pathname.startsWith("/admin/")) return false;
    return true;
  }

  async function navigate(url, options = {}) {
    const shell = document.querySelector(SHELL_SELECTOR);
    if (!shell) {
      window.location.assign(String(url));
      return;
    }

    if (activeController) {
      activeController.abort();
    }

    const controller = new AbortController();
    activeController = controller;

    try {
      document.body.classList.add("is-nav-loading");

      const response = await fetch(String(url), {
        method: "GET",
        signal: controller.signal,
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-QazSound-Navigation": "1",
        },
      });

      if (!response.ok) {
        throw new Error(`Navigation failed: ${response.status}`);
      }

      const html = await response.text();
      const nextDoc = new DOMParser().parseFromString(html, "text/html");
      const nextShell = nextDoc.querySelector(SHELL_SELECTOR);

      if (!nextShell) {
        window.location.assign(response.url || String(url));
        return;
      }

      shell.innerHTML = nextShell.innerHTML;

      const nextTitle = nextDoc.querySelector("title");
      if (nextTitle) {
        document.title = nextTitle.textContent || document.title;
      }

      const finalUrl = response.url || String(url);
      if (options.replace) {
        window.history.replaceState({ qazsoundNav: true }, "", finalUrl);
      } else {
        window.history.pushState({ qazsoundNav: true }, "", finalUrl);
      }

      if (!options.keepScroll) {
        window.scrollTo(0, 0);
      }

      dispatchRender(finalUrl);
    } catch (error) {
      if (error && error.name === "AbortError") {
        return;
      }
      window.location.assign(String(url));
    } finally {
      if (activeController === controller) {
        activeController = null;
      }
      document.body.classList.remove("is-nav-loading");
    }
  }

  document.addEventListener(
    "click",
    (event) => {
      const link = event.target.closest("a[href]");
      if (!isEligibleLink(link, event)) {
        return;
      }

      event.preventDefault();
      navigate(link.href);
    },
    true
  );

  document.addEventListener(
    "submit",
    (event) => {
      const form = event.target;
      if (!isEligibleGetForm(form)) {
        return;
      }

      event.preventDefault();
      const targetUrl = new URL(form.getAttribute("action") || window.location.href, window.location.href);
      const params = new URLSearchParams(new FormData(form));
      targetUrl.search = params.toString();
      navigate(targetUrl);
    },
    true
  );

  window.addEventListener("popstate", () => {
    navigate(window.location.href, { replace: true, keepScroll: true });
  });

  window.history.replaceState({ qazsoundNav: true }, "", window.location.href);
  dispatchRender(window.location.href);
})();
