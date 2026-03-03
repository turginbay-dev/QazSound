from __future__ import annotations

import importlib
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INVALID_FILENAME_PATTERN = re.compile(r"[<>:\"/\\|?*\x00-\x1F]")
SPACE_PATTERN = re.compile(r"\s+")


class AudioDownloadError(Exception):
    """Base exception for local YouTube download flow."""


class AudioDownloadDependencyError(AudioDownloadError):
    """Raised when yt-dlp or ffmpeg is not available."""


@dataclass(frozen=True)
class DownloadedAudioResult:
    title: str
    artist_label: str
    filename: str
    absolute_path: Path
    file_size_bytes: int



def _normalize_filename_part(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = INVALID_FILENAME_PATTERN.sub(" ", normalized)
    normalized = SPACE_PATTERN.sub(" ", normalized).strip()
    return normalized.strip(".-_")



def build_readable_filename(info: dict[str, Any], max_length: int = 120) -> str:
    artist = _normalize_filename_part(str(info.get("artist") or ""))
    track = _normalize_filename_part(str(info.get("track") or ""))
    uploader = _normalize_filename_part(str(info.get("uploader") or ""))
    title = _normalize_filename_part(str(info.get("title") or ""))

    if artist and track:
        base = f"{artist} - {track}"
    elif uploader and title:
        base = f"{uploader} - {title}"
    elif title:
        base = title
    else:
        base = "youtube-audio"

    base = base[:max_length].strip().strip(".-_")
    return base or "youtube-audio"



def _ensure_unique_target(download_dir: Path, stem: str) -> Path:
    candidate = download_dir / f"{stem}.mp3"
    if not candidate.exists():
        return candidate

    for index in range(2, 10_000):
        variant = download_dir / f"{stem} ({index}).mp3"
        if not variant.exists():
            return variant

    raise AudioDownloadError("Unable to generate a unique output filename.")



def _resolve_yt_dlp():
    try:
        module = importlib.import_module("yt_dlp")
        utils = importlib.import_module("yt_dlp.utils")
        return module.YoutubeDL, utils.DownloadError
    except Exception as exc:  # pragma: no cover - env dependent
        raise AudioDownloadDependencyError(
            "yt-dlp is not installed. Run: pip install yt-dlp"
        ) from exc



def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg"):
        return
    raise AudioDownloadDependencyError(
        "ffmpeg was not found in PATH. Install ffmpeg (macOS: brew install ffmpeg)."
    )



def download_youtube_audio_to_mp3(
    youtube_url: str,
    download_dir: Path,
    max_filename_length: int = 120,
    quality: str = "192",
) -> DownloadedAudioResult:
    """
    Local development test flow:
    - read YouTube metadata
    - build a safe, readable output filename
    - download audio via yt-dlp
    - convert to MP3 via ffmpeg postprocessor
    """

    YoutubeDL, DownloadError = _resolve_yt_dlp()
    _require_ffmpeg()

    download_dir.mkdir(parents=True, exist_ok=True)

    probe_options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }

    try:
        with YoutubeDL(probe_options) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
    except DownloadError as exc:
        raise AudioDownloadError(f"Could not read video metadata: {exc}") from exc

    if not isinstance(info, dict):
        raise AudioDownloadError("Unexpected metadata format returned by yt-dlp.")

    if info.get("_type") == "playlist":
        entries = info.get("entries") or []
        if not entries:
            raise AudioDownloadError("Playlist URL did not contain downloadable entries.")
        info = entries[0] or {}

    stem = build_readable_filename(info=info, max_length=max_filename_length)
    target_path = _ensure_unique_target(download_dir=download_dir, stem=stem)
    target_stem = target_path.stem

    download_options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "outtmpl": str(download_dir / f"{target_stem}.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }
        ],
    }

    try:
        with YoutubeDL(download_options) as ydl:
            ydl.extract_info(youtube_url, download=True)
    except DownloadError as exc:
        raise AudioDownloadError(f"Download/conversion failed: {exc}") from exc

    final_path = download_dir / f"{target_stem}.mp3"
    if not final_path.exists():
        candidates = sorted(
            download_dir.glob(f"{target_stem}*.mp3"),
            key=lambda file_path: file_path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise AudioDownloadError("MP3 file was not created after conversion.")
        final_path = candidates[0]

    file_size = final_path.stat().st_size
    title = _normalize_filename_part(str(info.get("title") or final_path.stem)) or final_path.stem
    artist_label = (
        _normalize_filename_part(str(info.get("artist") or ""))
        or _normalize_filename_part(str(info.get("uploader") or ""))
        or "Unknown artist"
    )

    return DownloadedAudioResult(
        title=title,
        artist_label=artist_label,
        filename=final_path.name,
        absolute_path=final_path,
        file_size_bytes=file_size,
    )
