(function () {
  const SOURCE_UPLOAD = "UPLOAD";
  const SOURCE_YOUTUBE = "YOUTUBE";

  function setYoutubeStatus(form, message, isError) {
    const status = form.querySelector(".js-youtube-status");
    if (!status) return;
    status.textContent = message || "";
    status.style.color = isError ? "#ffb2bc" : "";
  }

  function toggleSourceSections(form) {
    const sourceField = form.querySelector('select[name="source_type"]');
    if (!sourceField) return;

    const sourceType = sourceField.value;
    form.querySelectorAll(".js-upload-only").forEach((el) => {
      el.classList.toggle("is-hidden", sourceType !== SOURCE_UPLOAD);
    });
    form.querySelectorAll(".js-youtube-only").forEach((el) => {
      el.classList.toggle("is-hidden", sourceType !== SOURCE_YOUTUBE);
    });
  }

  async function fetchYoutubeMetadata(form) {
    const endpoint = form.dataset.youtubeMetadataUrl;
    const urlInput = form.querySelector('input[name="youtube_url"]');
    const titleField = form.querySelector('input[name="title"]');
    const artistField = form.querySelector('input[name="artist_name"]');
    const durationField = form.querySelector('input[name="duration_seconds"]');
    const coverUrlField = form.querySelector('input[name="external_cover_url"]');

    if (!endpoint || !urlInput) return;

    const youtubeUrl = (urlInput.value || "").trim();
    if (!youtubeUrl) {
      setYoutubeStatus(form, "Paste a YouTube URL first.", true);
      return;
    }

    setYoutubeStatus(form, "Fetching metadata...", false);

    try {
      const response = await fetch(`${endpoint}?url=${encodeURIComponent(youtubeUrl)}`, {
        headers: {
          Accept: "application/json",
        },
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to fetch metadata.");
      }

      if (titleField && !titleField.value.trim() && data.title) {
        titleField.value = data.title;
      }
      if (artistField && !artistField.value.trim() && data.author_name) {
        artistField.value = data.author_name;
      }
      if (coverUrlField && !coverUrlField.value.trim() && data.thumbnail_url) {
        coverUrlField.value = data.thumbnail_url;
      }
      if (durationField && !durationField.value.trim() && Number.isFinite(Number(data.duration_seconds))) {
        durationField.value = String(Math.max(0, Number(data.duration_seconds)));
      }
      if (urlInput && data.normalized_url) {
        urlInput.value = data.normalized_url;
      }

      setYoutubeStatus(form, "Metadata loaded.", false);
    } catch (error) {
      setYoutubeStatus(form, error.message || "Could not fetch metadata.", true);
    }
  }

  function validateTrackForm(form, event) {
    const errors = [];
    const sourceField = form.querySelector('select[name="source_type"]');
    const titleField = form.querySelector('input[name="title"]');
    const artistField = form.querySelector('input[name="artist_name"]');
    const audioField = form.querySelector('input[name="audio_file"]');
    const youtubeField = form.querySelector('input[name="youtube_url"]');
    const sourceType = sourceField ? sourceField.value : SOURCE_UPLOAD;
    const requireAudio = form.dataset.requireAudio === "true";

    if (titleField && !titleField.value.trim()) {
      errors.push("Title is required.");
    }

    if (artistField && !artistField.value.trim()) {
      errors.push("Artist name is required.");
    }

    if (sourceType === SOURCE_UPLOAD && requireAudio && audioField && !audioField.value) {
      errors.push("Audio file is required for upload source.");
    }

    if (sourceType === SOURCE_YOUTUBE && youtubeField && !youtubeField.value.trim()) {
      errors.push("YouTube URL is required for YouTube source.");
    }

    const errorBox = form.querySelector("#client-form-errors") || document.getElementById("client-form-errors");
    if (errorBox) {
      errorBox.innerHTML = "";
    }

    if (!errors.length) {
      return;
    }

    event.preventDefault();
    if (errorBox) {
      const wrapper = document.createElement("div");
      wrapper.className = "form-error";
      wrapper.textContent = errors.join(" ");
      errorBox.appendChild(wrapper);
    }
  }

  function initTrackForms(root) {
    (root || document).querySelectorAll(".js-track-form").forEach((form) => {
      toggleSourceSections(form);
    });
  }

  document.addEventListener("change", (event) => {
    const sourceField = event.target.closest('.js-track-form select[name="source_type"]');
    if (!sourceField) return;
    const form = sourceField.closest(".js-track-form");
    if (!form) return;
    toggleSourceSections(form);
  });

  document.addEventListener("click", (event) => {
    const fetchButton = event.target.closest(".js-youtube-fetch");
    if (!fetchButton) return;
    const form = fetchButton.closest(".js-track-form");
    if (!form) return;
    event.preventDefault();
    fetchYoutubeMetadata(form);
  });

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.classList.contains("js-track-form")) {
      return;
    }
    validateTrackForm(form, event);
  });

  initTrackForms(document);
  window.addEventListener("qazsound:navigation:render", () => initTrackForms(document));
})();
