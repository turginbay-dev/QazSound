(function () {
  const STORAGE_KEY = "qazsound.player.state.v2";
  const HISTORY_KEY = "qazsound.player.history.v2";
  const SOURCE_UPLOAD = "UPLOAD";
  const SOURCE_YOUTUBE = "YOUTUBE";
  const SAVE_THROTTLE_MS = 500;
  const HISTORY_LIMIT = 40;

  const playerBar = document.querySelector("[data-playerbar]");
  const audio = document.getElementById("global-audio");

  if (!playerBar || !audio) return;

  const refs = {
    cover: document.getElementById("player-cover"),
    title: document.getElementById("player-title"),
    status: document.getElementById("player-status"),
    playPause: document.getElementById("player-playpause"),
    prev: document.getElementById("player-prev"),
    next: document.getElementById("player-next"),
    like: document.getElementById("player-like"),
  };

  const placeholderCover = refs.cover ? refs.cover.src : "";

  let saveTimer = null;
  let history = {
    items: [],
    index: -1,
  };

  let playbackState = {
    trackId: "",
    title: "Nothing playing",
    artist: "",
    coverUrl: placeholderCover,
    audioUrl: "",
    sourceType: SOURCE_UPLOAD,
    trackUrl: "/",
    isLiked: false,
  };

  function clamp(value, min, max, fallback = min) {
    if (!Number.isFinite(value)) {
      return fallback;
    }
    return Math.min(Math.max(value, min), max);
  }

  function toAbsoluteUrl(url) {
    if (!url) return "";

    try {
      return new URL(url, window.location.origin).href;
    } catch (error) {
      return url;
    }
  }

  function parseJson(value) {
    try {
      return JSON.parse(value);
    } catch (error) {
      return null;
    }
  }

  function asBoolean(value) {
    if (typeof value === "boolean") return value;
    if (typeof value === "number") return value > 0;
    if (typeof value !== "string") return false;
    const normalized = value.trim().toLowerCase();
    return normalized === "1" || normalized === "true" || normalized === "yes" || normalized === "on";
  }

  function normalizeTrack(raw = {}) {
    const trackId = String(raw.trackId || raw.track_id || "").trim();
    const sourceRaw = String(raw.sourceType || raw.source_type || SOURCE_UPLOAD).toUpperCase();
    const sourceType = sourceRaw === SOURCE_YOUTUBE ? SOURCE_YOUTUBE : SOURCE_UPLOAD;

    return {
      trackId,
      title: String(raw.title || "Untitled track").trim() || "Untitled track",
      artist: String(raw.artist || "Unknown artist").trim() || "Unknown artist",
      coverUrl: String(raw.coverUrl || raw.cover_url || placeholderCover || "").trim() || placeholderCover,
      audioUrl: String(raw.audioUrl || raw.audio_url || "").trim(),
      sourceType,
      trackUrl: String(raw.trackUrl || raw.track_url || (trackId ? `/tracks/${trackId}/` : "/")).trim() || "/",
      isLiked: asBoolean(raw.isLiked ?? raw.is_liked ?? raw.liked ?? false),
    };
  }

  function getCookie(name) {
    const cookie = document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(`${name}=`));
    return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
  }

  function setPlayerBarVisible(isVisible) {
    playerBar.classList.toggle("is-visible", isVisible);
    document.body.classList.toggle("has-playerbar", isVisible);
  }

  function sameTrack(first, second) {
    return (
      first.trackId === second.trackId &&
      first.sourceType === second.sourceType &&
      toAbsoluteUrl(first.audioUrl) === toAbsoluteUrl(second.audioUrl)
    );
  }

  function ensureButtonDefaults(button) {
    if (!button || button.dataset.defaultLabel) return;
    const isIconButton = button.classList.contains("icon-btn");
    const fallbackLabel = isIconButton ? "▶" : "Play";
    button.dataset.defaultLabel = (button.textContent || "").trim() || fallbackLabel;
  }

  function applyPlayButtonState(button, state) {
    ensureButtonDefaults(button);
    if (!button) return;

    const isIconButton = button.classList.contains("icon-btn");
    const defaultLabel = button.dataset.defaultLabel;

    let nextLabel = defaultLabel;
    if (isIconButton) {
      nextLabel = state === "playing" ? "⏸" : "▶";
    } else if (state === "playing") {
      nextLabel = "Pause";
    } else if (state === "paused") {
      nextLabel = "Resume";
    }

    button.textContent = nextLabel;
    button.classList.toggle("is-current", state === "paused" || state === "playing");
    button.classList.toggle("is-playing", state === "playing");
    button.setAttribute("aria-pressed", state === "playing" ? "true" : "false");
  }

  function refreshPlayTriggers() {
    const isPlaying = Boolean(playbackState.audioUrl) && !audio.paused && !audio.ended;

    document.querySelectorAll(".js-player-play").forEach((button) => {
      const buttonTrack = trackFromTrigger(button);
      const matchesCurrent = sameTrack(playbackState, buttonTrack);

      if (!matchesCurrent) {
        applyPlayButtonState(button, "idle");
        return;
      }

      applyPlayButtonState(button, isPlaying ? "playing" : "paused");
    });
  }

  function readSavedState() {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const parsed = parseJson(raw);
    if (!parsed) return null;

    const track = normalizeTrack(parsed);
    if (!track.trackId) return null;

    return {
      ...track,
      currentTime: Math.max(0, Number(parsed.currentTime) || 0),
      isPlaying: Boolean(parsed.isPlaying),
      volume: clamp(Number(parsed.volume), 0, 1, 1),
    };
  }

  function readHistory() {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    if (!raw) return;

    const parsed = parseJson(raw);
    if (!parsed || !Array.isArray(parsed.items)) return;

    const items = parsed.items.map((item) => normalizeTrack(item)).filter((item) => item.trackId);
    if (!items.length) return;

    const parsedIndex = Number.parseInt(parsed.index, 10);
    const index = Number.isInteger(parsedIndex) ? clamp(parsedIndex, 0, items.length - 1, items.length - 1) : items.length - 1;

    history = {
      items,
      index,
    };
  }

  function persistHistory() {
    window.localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify({
        items: history.items,
        index: history.index,
      })
    );
    updateHistoryButtons();
  }

  function getRuntimeState() {
    return {
      ...playbackState,
      currentTime: audio.currentTime || 0,
      isPlaying: Boolean(playbackState.audioUrl) && !audio.paused && !audio.ended,
      volume: audio.volume,
    };
  }

  function persistStateNow() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(getRuntimeState()));
    } catch (error) {
      // Ignore storage write errors.
    }
  }

  function schedulePersist() {
    if (saveTimer) {
      window.clearTimeout(saveTimer);
    }

    saveTimer = window.setTimeout(() => {
      persistStateNow();
      saveTimer = null;
    }, SAVE_THROTTLE_MS);
  }

  function updateStatus(message) {
    if (!refs.status) return;
    refs.status.textContent = message || "";
  }

  function updateTrackMeta() {
    if (refs.cover) {
      refs.cover.src = playbackState.coverUrl || placeholderCover;
      refs.cover.alt = `${playbackState.title} cover`;
    }

    if (refs.title) {
      const artistSuffix = playbackState.artist ? ` · ${playbackState.artist}` : "";
      refs.title.textContent = `${playbackState.title || "Nothing playing"}${artistSuffix}`;
    }
  }

  function setPlaybackControlsEnabled(enabled) {
    if (refs.playPause) refs.playPause.disabled = !enabled;
    if (refs.prev) refs.prev.disabled = history.index <= 0;
    if (refs.next) refs.next.disabled = !(history.index >= 0 && history.index < history.items.length - 1);
  }

  function updateHistoryButtons() {
    const hasPrev = history.index > 0;
    const hasNext = history.index >= 0 && history.index < history.items.length - 1;

    if (refs.prev) refs.prev.disabled = !hasPrev;
    if (refs.next) refs.next.disabled = !hasNext;
  }

  function updatePlayPauseButton() {
    if (!refs.playPause) return;

    const isPlaying = Boolean(playbackState.audioUrl) && !audio.paused && !audio.ended;
    refs.playPause.textContent = isPlaying ? "⏸" : "▶";
    refs.playPause.setAttribute("aria-label", isPlaying ? "Pause" : "Play");
    refreshPlayTriggers();
  }

  function updateLikeButton() {
    if (!refs.like) return;

    const hasTrack = Boolean(playbackState.trackId);
    refs.like.disabled = !hasTrack;
    refs.like.classList.toggle("is-liked", hasTrack && playbackState.isLiked);
    refs.like.setAttribute("aria-pressed", hasTrack && playbackState.isLiked ? "true" : "false");
    refs.like.dataset.liked = hasTrack && playbackState.isLiked ? "1" : "0";

    const icon = refs.like.querySelector(".icon-heart");
    if (icon) {
      icon.textContent = hasTrack && playbackState.isLiked ? "♥" : "♡";
    }
  }

  function applyLikeStateToPage(trackId, liked, likesCount) {
    if (typeof window.qazsoundApplyLikeState === "function") {
      window.qazsoundApplyLikeState(trackId, liked, likesCount);
      return;
    }

    document
      .querySelectorAll(`[data-like-count][data-track-id="${trackId}"]`)
      .forEach((counter) => {
        const hasPrefix = counter.textContent.trim().startsWith("♥");
        counter.textContent = hasPrefix ? `♥ ${likesCount}` : String(likesCount);
      });
  }

  async function toggleCurrentTrackLike() {
    if (!refs.like || !playbackState.trackId) return;

    const trackId = playbackState.trackId;
    const csrfToken = getCookie("csrftoken");

    refs.like.disabled = true;

    try {
      const response = await fetch(`/tracks/${trackId}/like/`, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
          "X-CSRFToken": csrfToken || "",
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
        body: new URLSearchParams({
          next: window.location.pathname + window.location.search,
        }),
      });

      if (response.status === 401 || response.status === 403) {
        window.location.assign(`/auth/login/?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
        return;
      }

      if (!response.ok) {
        throw new Error("Could not toggle like");
      }

      const payload = await response.json();
      const liked = Boolean(payload.liked);
      const likesCount = Number(payload.likes_count) || 0;

      playbackState.isLiked = liked;
      updateLikeButton();
      applyLikeStateToPage(trackId, liked, likesCount);
      updateStatus(liked ? "Added to favorites." : "Removed from favorites.");
      schedulePersist();
    } catch (error) {
      updateStatus("Could not update favorite.");
    } finally {
      refs.like.disabled = false;
    }
  }

  function pushHistory(track) {
    const normalized = normalizeTrack(track);
    if (!normalized.trackId) return;

    const currentItem = history.items[history.index];
    if (currentItem && sameTrack(currentItem, normalized)) {
      return;
    }

    if (history.index >= 0 && history.index < history.items.length - 1) {
      history.items = history.items.slice(0, history.index + 1);
    }

    history.items.push(normalized);
    if (history.items.length > HISTORY_LIMIT) {
      history.items = history.items.slice(history.items.length - HISTORY_LIMIT);
    }

    history.index = history.items.length - 1;
    persistHistory();
  }

  function attemptPlay() {
    const playPromise = audio.play();

    if (playPromise && typeof playPromise.then === "function") {
      playPromise
        .then(() => {
          updatePlayPauseButton();
          updateStatus("Playing.");
          schedulePersist();
        })
        .catch(() => {
          updatePlayPauseButton();
          updateStatus("Tap play to resume.");
          schedulePersist();
        });
      return;
    }

    updatePlayPauseButton();
    updateStatus("Playing.");
    schedulePersist();
  }

  function clearAudio(message) {
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    setPlaybackControlsEnabled(false);
    updatePlayPauseButton();
    updateStatus(message);
    schedulePersist();
  }

  function applyTrack(track, options = {}) {
    const normalized = normalizeTrack(track);
    if (!normalized.trackId) return;

    const autoplay = Boolean(options.autoplay);
    const rememberHistory = options.rememberHistory !== false;
    const restoreTime = Math.max(0, Number(options.restoreTime) || 0);

    playbackState = normalized;
    setPlayerBarVisible(true);
    updateTrackMeta();
    updateLikeButton();

    if (rememberHistory) {
      pushHistory(normalized);
    } else {
      updateHistoryButtons();
    }

    if (!normalized.audioUrl) {
      clearAudio("Audio source is not available for this track.");
      return;
    }

    setPlaybackControlsEnabled(true);

    const nextSrcAbs = toAbsoluteUrl(normalized.audioUrl);
    const currentSrcAbs = toAbsoluteUrl(audio.src);
    const sourceChanged = nextSrcAbs !== currentSrcAbs;

    const finalizePlaybackStart = () => {
      if (restoreTime > 0) {
        const duration = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : restoreTime;
        audio.currentTime = clamp(restoreTime, 0, duration, 0);
      }

      if (autoplay) {
        attemptPlay();
      } else {
        audio.pause();
        updatePlayPauseButton();
        updateStatus("Ready.");
        schedulePersist();
      }
    };

    if (sourceChanged) {
      audio.src = normalized.audioUrl;
      audio.load();
    }

    if (audio.readyState >= 1) {
      finalizePlaybackStart();
    } else {
      audio.addEventListener("loadedmetadata", finalizePlaybackStart, { once: true });
    }
  }

  function pauseDetailAudios(except) {
    document.querySelectorAll(".js-detail-audio").forEach((detailAudio) => {
      if (!(detailAudio instanceof HTMLAudioElement)) return;
      if (detailAudio === except) return;
      if (!detailAudio.paused) {
        detailAudio.pause();
      }
    });
  }

  function trackFromTrigger(trigger) {
    return normalizeTrack({
      trackId: trigger.dataset.trackId,
      title: trigger.dataset.title,
      artist: trigger.dataset.artist,
      coverUrl: trigger.dataset.coverUrl,
      audioUrl: trigger.dataset.audioUrl,
      sourceType: trigger.dataset.sourceType,
      trackUrl: trigger.dataset.trackUrl,
      isLiked: trigger.dataset.isLiked,
    });
  }

  function moveHistory(step) {
    const targetIndex = history.index + step;
    if (targetIndex < 0 || targetIndex >= history.items.length) {
      return;
    }

    history.index = targetIndex;
    persistHistory();

    const targetTrack = history.items[targetIndex];
    applyTrack(targetTrack, { autoplay: true, rememberHistory: false });
  }

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".js-player-play");
    if (!trigger) return;

    event.preventDefault();
    const track = trackFromTrigger(trigger);

    if (sameTrack(playbackState, track) && track.audioUrl) {
      if (audio.paused) {
        attemptPlay();
      } else {
        audio.pause();
      }
      return;
    }

    applyTrack(track, { autoplay: true, rememberHistory: true });
  });

  if (refs.playPause) {
    refs.playPause.addEventListener("click", () => {
      if (!playbackState.audioUrl) {
        updateStatus("Select a track to play first.");
        return;
      }

      if (audio.paused) {
        attemptPlay();
      } else {
        audio.pause();
      }
    });
  }

  if (refs.prev) {
    refs.prev.addEventListener("click", () => moveHistory(-1));
  }

  if (refs.next) {
    refs.next.addEventListener("click", () => moveHistory(1));
  }

  if (refs.like) {
    refs.like.addEventListener("click", () => {
      toggleCurrentTrackLike();
    });
  }

  audio.addEventListener("timeupdate", schedulePersist);

  audio.addEventListener("play", () => {
    pauseDetailAudios(null);
    updatePlayPauseButton();
    updateStatus("Playing.");
    schedulePersist();
  });

  audio.addEventListener("pause", () => {
    updatePlayPauseButton();
    if (!audio.ended) {
      updateStatus("Paused.");
    }
    schedulePersist();
  });

  audio.addEventListener("ended", () => {
    updatePlayPauseButton();
    updateStatus("Playback ended.");
    schedulePersist();
  });

  audio.addEventListener("error", () => {
    updatePlayPauseButton();
    updateStatus("Could not play this file.");
    schedulePersist();
  });

  document.addEventListener(
    "play",
    (event) => {
      const target = event.target;
      if (!(target instanceof HTMLAudioElement) || !target.classList.contains("js-detail-audio")) {
        return;
      }
      if (!audio.paused) {
        audio.pause();
      }
      pauseDetailAudios(target);
    },
    true
  );

  window.addEventListener("pagehide", persistStateNow);
  window.addEventListener("beforeunload", persistStateNow);

  window.addEventListener("qazsound:navigation:render", () => {
    refreshPlayTriggers();
    updateLikeButton();
    if (playbackState.trackId) {
      updateTrackMeta();
    }
  });

  readHistory();
  updateHistoryButtons();

  const savedState = readSavedState();
  if (savedState) {
    audio.volume = savedState.volume;
    setPlayerBarVisible(true);
    applyTrack(savedState, {
      autoplay: false,
      rememberHistory: false,
      restoreTime: savedState.currentTime,
    });

    if (savedState.isPlaying && savedState.audioUrl) {
      const resume = () => {
        if (savedState.currentTime > 0) {
          const duration = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : savedState.currentTime;
          audio.currentTime = clamp(savedState.currentTime, 0, duration, 0);
        }
        attemptPlay();
      };

      if (audio.readyState >= 1) {
        resume();
      } else {
        audio.addEventListener("loadedmetadata", resume, { once: true });
      }
    }
  } else {
    setPlayerBarVisible(false);
    setPlaybackControlsEnabled(false);
    updatePlayPauseButton();
    updateLikeButton();
    updateStatus("Choose any track to start playback.");
    persistStateNow();
  }

  refreshPlayTriggers();
})();
