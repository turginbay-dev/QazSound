(function () {
  function applyLikeState(trackId, liked, likesCount) {
    const resolvedTrackId = String(trackId || "").trim();
    if (!resolvedTrackId) return;

    document
      .querySelectorAll(`.js-like-form[data-track-id="${resolvedTrackId}"] .js-like-button`)
      .forEach((button) => {
        button.classList.toggle("is-liked", liked);
        button.setAttribute("aria-pressed", liked ? "true" : "false");
        button.dataset.liked = liked ? "1" : "0";

        const icon = button.querySelector(".icon-heart");
        if (icon) {
          icon.textContent = liked ? "♥" : "♡";
        }

        if (button.classList.contains("like-pill")) {
          const textSpan = button.querySelector("span:last-child");
          if (textSpan) {
            textSpan.textContent = liked ? "In favorites" : "Add to favorites";
          }
        }
      });

    document
      .querySelectorAll(`[data-like-count][data-track-id="${resolvedTrackId}"]`)
      .forEach((counter) => {
        const hasPrefix = counter.textContent.trim().startsWith("♥");
        counter.textContent = hasPrefix ? `♥ ${likesCount}` : String(likesCount);
      });
  }

  window.qazsoundApplyLikeState = applyLikeState;

  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.classList.contains("js-like-form")) {
      return;
    }

    if (!window.fetch) return;

    event.preventDefault();

    const csrfToken = form.querySelector("input[name='csrfmiddlewaretoken']")?.value;
    const formData = new FormData(form);
    const trackId = form.dataset.trackId;

    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
          "X-CSRFToken": csrfToken || "",
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Like toggle failed");
      }

      const payload = await response.json();
      applyLikeState(trackId || payload.track_id, payload.liked, payload.likes_count);
    } catch (error) {
      form.submit();
    }
  });
})();
