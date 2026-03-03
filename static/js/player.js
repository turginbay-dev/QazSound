(function () {
  const STORAGE_KEY = "qazsound.player.state.v1";
  const HISTORY_KEY = "qazsound.player.history.v1";
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
    artist: document.getElementById("player-artist"),
    status: document.getElementById("player-status"),
    playPause: document.getElementById("player-playpause"),
    prev: document.getElementById("player-prev"),
    next: document.getElementById("player-next"),
    progress: document.getElementById("player-progress"),
    currentTime: document.getElementById("player-current-time"),
    duration: document.getElementById("player-duration"),
    volume: document.getElementById("player-volume"),
    openTrack: document.getElementById("player-open-track"),
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
  };

  function setPlayerBarVisible(isVisible) {
    playerBar.classList.toggle("is-visible", isVisible);
    document.body.classList.toggle("has-playerbar", isVisible);
  }

  function clamp(value, min, max, fallback = min) {
    if (!Number.isFinite(value)) {
      return fallback;
    }
    return Math.min(Math.max(value, min), max);
  }

  function formatTime(totalSeconds) {
    const seconds = clamp(totalSeconds, 0, 24 * 60 * 60, 0);
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min}:${String(sec).padStart(2, "0")}`;
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
    };
  }

  function ensureButtonDefaults(button) {
    if (button.dataset.defaultLabel) return;
    const isIconButton = button.classList.contains("icon-btn");
    const fallbackLabel = isIconButton ? "▶" : "Play";
    button.dataset.defaultLabel = (button.textContent || "").trim() || fallbackLabel;
  }

  function applyPlayButtonState(button, state) {
    ensureButtonDefaults(button);
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
    const isPlaying =
      Boolean(playbackState.audioUrl) &&
      !audio.paused &&
      !audio.ended;

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
      isPlaying:
        Boolean(playbackState.audioUrl) &&
        !audio.paused &&
        !audio.ended,
      volume: audio.volume,
    };
  }

  function persistStateNow() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(getRuntimeState()));
    } catch (error) {
      // Ignore storage write errors and keep playback functional.
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

  function updateStatus(message, options = {}) {
    if (!refs.status) return;

    refs.status.textContent = message || "";
    refs.status.classList.toggle("has-alert", Boolean(options.error));
    refs.status.classList.toggle("is-active", Boolean(options.active));
  }

  function updateTrackMeta() {
    if (refs.cover) {
      refs.cover.src = playbackState.coverUrl || placeholderCover;
      refs.cover.alt = `${playbackState.title} cover`;
    }

    if (refs.title) {
      refs.title.textContent = playbackState.title || "Nothing playing";
    }

    if (refs.artist) {
      refs.artist.textContent = playbackState.artist || "";
    }

    if (refs.openTrack) {
      refs.openTrack.href = playbackState.trackUrl || "/";
    }
  }

  function setPlaybackControlsEnabled(enabled) {
    [refs.playPause, refs.progress, refs.volume].forEach((control) => {
      if (control) {
        control.disabled = !enabled;
      }
    });
  }

  function updateHistoryButtons() {
    const hasPrev = history.index > 0;
    const hasNext = history.index >= 0 && history.index < history.items.length - 1;

    if (refs.prev) refs.prev.disabled = !hasPrev;
    if (refs.next) refs.next.disabled = !hasNext;
  }

  function updatePlayPauseButton() {
    if (!refs.playPause) return;

    const isPlaying =
      Boolean(playbackState.audioUrl) &&
      !audio.paused &&
      !audio.ended;

    refs.playPause.textContent = isPlaying ? "⏸" : "▶";
    refs.playPause.setAttribute("aria-label", isPlaying ? "Pause" : "Play");
    refreshPlayTriggers();
  }

  function updateProgress() {
    if (!refs.progress || !refs.currentTime || !refs.duration) return;

    const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
    const current = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;

    refs.currentTime.textContent = formatTime(current);

    if (duration > 0) {
      refs.progress.value = String(Math.round((current / duration) * 1000));
      refs.duration.textContent = formatTime(duration);
    } else {
      refs.progress.value = "0";
      refs.duration.textContent = "0:00";
    }
  }

  function sameTrack(first, second) {
    return (
      first.trackId === second.trackId &&
      first.sourceType === second.sourceType &&
      toAbsoluteUrl(first.audioUrl) === toAbsoluteUrl(second.audioUrl)
    );
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
          updateStatus("Playing from PlayerBar.", { active: true });
          schedulePersist();
        })
        .catch(() => {
          updatePlayPauseButton();
          updateStatus("Tap play to resume playback.");
          schedulePersist();
        });
      return;
    }

    updatePlayPauseButton();
    updateStatus("Playing from PlayerBar.", { active: true });
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

    if (rememberHistory) {
      pushHistory(normalized);
    } else {
      updateHistoryButtons();
    }

    if (normalized.sourceType === SOURCE_YOUTUBE && !normalized.audioUrl) {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      setPlaybackControlsEnabled(false);
      updateProgress();
      updatePlayPauseButton();
      updateStatus("Open track to play. YouTube track has no imported audio yet.");
      persistStateNow();
      return;
    }

    if (!normalized.audioUrl) {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      setPlaybackControlsEnabled(false);
      updateProgress();
      updatePlayPauseButton();
      updateStatus("Audio source is not available for this track.", { error: true });
      persistStateNow();
      return;
    }

    setPlaybackControlsEnabled(true);

    const nextSrcAbs = toAbsoluteUrl(normalized.audioUrl);
    const currentSrcAbs = toAbsoluteUrl(audio.src);
    if (nextSrcAbs !== currentSrcAbs) {
      audio.src = normalized.audioUrl;
      audio.load();
    }

    const finalizePlaybackStart = () => {
      if (restoreTime > 0) {
        const duration = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : restoreTime;
        audio.currentTime = clamp(restoreTime, 0, duration, 0);
      }

      updateProgress();

      if (autoplay) {
        attemptPlay();
      } else {
        audio.pause();
        updatePlayPauseButton();
        updateStatus("Ready in PlayerBar.");
        schedulePersist();
      }
    };

    if (audio.readyState >= 1) {
      finalizePlaybackStart();
    } else {
      audio.addEventListener("loadedmetadata", finalizePlaybackStart, { once: true });
    }
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

  if (refs.progress) {
    refs.progress.addEventListener("input", () => {
      const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
      if (!duration) return;

      const nextTime = (Number(refs.progress.value) / 1000) * duration;
      audio.currentTime = clamp(nextTime, 0, duration, 0);
      updateProgress();
      schedulePersist();
    });
  }

  if (refs.volume) {
    refs.volume.addEventListener("input", () => {
      audio.volume = clamp(Number(refs.volume.value), 0, 1, 1);
      schedulePersist();
    });
  }

  audio.addEventListener("timeupdate", () => {
    updateProgress();
    schedulePersist();
  });

  audio.addEventListener("play", () => {
    updatePlayPauseButton();
    updateStatus("Playing from PlayerBar.", { active: true });
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

  audio.addEventListener("volumechange", () => {
    if (refs.volume) {
      refs.volume.value = String(audio.volume);
    }
    schedulePersist();
  });

  audio.addEventListener("durationchange", updateProgress);
  audio.addEventListener("loadedmetadata", updateProgress);

  audio.addEventListener("error", () => {
    updatePlayPauseButton();
    updateStatus("Could not play this file.", { error: true });
    schedulePersist();
  });

  window.addEventListener("pagehide", persistStateNow);
  window.addEventListener("beforeunload", persistStateNow);

  readHistory();
  updateHistoryButtons();

  const savedState = readSavedState();
  if (refs.volume) {
    const initialVolume = savedState ? savedState.volume : clamp(Number(refs.volume.value), 0, 1, 1);
    refs.volume.value = String(initialVolume);
    audio.volume = initialVolume;
  }

  if (savedState) {
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
    updateProgress();
    updatePlayPauseButton();
    updateStatus("Choose any track to start playback.");
    persistStateNow();
  }

  refreshPlayTriggers();
})();
