(function () {
  const likeForms = document.querySelectorAll(".js-like-form");
  if (!likeForms.length) return;

  function applyLikeState(trackId, liked, likesCount) {
    document
      .querySelectorAll(`.js-like-form[data-track-id="${trackId}"] .js-like-button`)
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
      .querySelectorAll(`[data-like-count][data-track-id="${trackId}"]`)
      .forEach((counter) => {
        const hasPrefix = counter.textContent.trim().startsWith("♥");
        counter.textContent = hasPrefix ? `♥ ${likesCount}` : String(likesCount);
      });
  }

  likeForms.forEach((form) => {
    form.addEventListener("submit", async (event) => {
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
  });
})();
