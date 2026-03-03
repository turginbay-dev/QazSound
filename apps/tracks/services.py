import json
import os
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

from django.conf import settings

from .downloader import AudioDownloadDependencyError, AudioDownloadError, download_youtube_audio_to_mp3
from .models import Artist, Track
from .utils import extract_youtube_id, is_youtube_domain, normalize_youtube_url

if TYPE_CHECKING:
    from .forms import TrackForm


class TrackProcessingError(Exception):
    """Raised when track business logic fails during create/update."""


def is_valid_youtube_url(url: str) -> bool:
    return is_youtube_domain(url) and extract_youtube_id(url) is not None


def build_youtube_embed_url(video_id: str) -> str:
    if not video_id:
        return ""
    return f"https://www.youtube.com/embed/{video_id}"


def fetch_youtube_metadata(youtube_url: str) -> dict:
    normalized_url = normalize_youtube_url(youtube_url)
    video_id = extract_youtube_id(normalized_url)
    if not video_id:
        return {}

    metadata = _fetch_metadata_from_data_api(video_id=video_id)
    if not metadata:
        metadata = _fetch_metadata_from_oembed(normalized_url=normalized_url)

    if not metadata:
        return {}

    metadata["video_id"] = video_id
    metadata["normalized_url"] = normalized_url
    metadata["embed_url"] = build_youtube_embed_url(video_id)
    return metadata


def _fetch_json(url: str) -> dict:
    try:
        with urlopen(url, timeout=8) as response:
            payload = response.read().decode("utf-8")
    except (URLError, TimeoutError, OSError):
        return {}

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return {}

    if isinstance(parsed, dict):
        return parsed
    return {}


def _fetch_metadata_from_data_api(video_id: str) -> dict:
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        return {}

    api_url = (
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet&id={quote(video_id)}&key={quote(api_key)}"
    )
    payload = _fetch_json(api_url)
    items = payload.get("items") or []
    if not items:
        return {}

    snippet = items[0].get("snippet") or {}
    thumbs = snippet.get("thumbnails") or {}

    thumb_url = ""
    for key in ("maxres", "high", "medium", "default"):
        candidate = (thumbs.get(key) or {}).get("url")
        if candidate:
            thumb_url = candidate
            break

    return {
        "title": snippet.get("title", "").strip(),
        "author_name": snippet.get("channelTitle", "").strip(),
        "thumbnail_url": thumb_url,
    }


def _fetch_metadata_from_oembed(normalized_url: str) -> dict:
    oembed_url = (
        "https://www.youtube.com/oembed"
        f"?url={quote(normalized_url, safe='')}&format=json"
    )
    payload = _fetch_json(oembed_url)
    if not payload:
        return {}

    return {
        "title": str(payload.get("title", "")).strip(),
        "author_name": str(payload.get("author_name", "")).strip(),
        "thumbnail_url": str(payload.get("thumbnail_url", "")).strip(),
    }


def _resolve_artist(artist_name: str) -> Artist:
    cleaned = (artist_name or "").strip()
    artist = Artist.objects.filter(name__iexact=cleaned).first()
    if artist:
        return artist
    return Artist.objects.create(name=cleaned)


def _assign_imported_audio_file(track: Track, youtube_url: str) -> None:
    if not youtube_url:
        raise TrackProcessingError("YouTube URL is required for import.")

    if not getattr(settings, "ENABLE_YTDLP_YOUTUBE_IMPORT", True):
        raise TrackProcessingError("YouTube import is disabled in this environment.")

    download_dir = Path(getattr(settings, "YTDLP_IMPORT_AUDIO_DIR", settings.MEDIA_ROOT / "audio"))
    max_name_length = getattr(settings, "YTDLP_MAX_FILENAME_LENGTH", 120)

    try:
        result = download_youtube_audio_to_mp3(
            youtube_url=youtube_url,
            download_dir=download_dir,
            max_filename_length=max_name_length,
        )
    except (AudioDownloadDependencyError, AudioDownloadError) as exc:
        raise TrackProcessingError(str(exc)) from exc

    try:
        relative_path = result.absolute_path.relative_to(settings.MEDIA_ROOT)
    except ValueError as exc:
        raise TrackProcessingError("Imported audio file path is outside MEDIA_ROOT.") from exc

    track.audio_file.name = str(relative_path).replace("\\", "/")


def _apply_track_source_logic(track: Track, form: "TrackForm", previous_state: dict | None = None) -> Track:
    track.artist = _resolve_artist(form.cleaned_data["artist_name"])

    if track.source_type == Track.SourceType.YOUTUBE:
        normalized_url = normalize_youtube_url(form.cleaned_data.get("youtube_url", ""))
        if not normalized_url:
            raise TrackProcessingError("YouTube URL is required for import.")

        track.youtube_url = normalized_url or None
        track.youtube_id = form.youtube_id or extract_youtube_id(normalized_url)
        track.audio_file = None

        metadata = form.youtube_metadata or fetch_youtube_metadata(normalized_url)

        if not track.title:
            track.title = (metadata.get("title") or "").strip()

        if not track.external_cover_url:
            track.external_cover_url = (metadata.get("thumbnail_url") or "").strip()

        previous_url = normalize_youtube_url((previous_state or {}).get("youtube_url", "") or "")
        previous_audio_name = ((previous_state or {}).get("audio_file_name") or "").strip()
        previous_source_type = (previous_state or {}).get("source_type")

        can_reuse_existing_audio = (
            previous_source_type == Track.SourceType.YOUTUBE
            and previous_audio_name
            and previous_url
            and previous_url == normalized_url
        )
        has_audio_now = bool(track.audio_file and getattr(track.audio_file, "name", "").strip())

        if not has_audio_now and can_reuse_existing_audio:
            track.audio_file.name = previous_audio_name
            has_audio_now = True

        if not has_audio_now:
            _assign_imported_audio_file(track=track, youtube_url=normalized_url)
    else:
        track.youtube_url = None
        track.youtube_id = None
        track.external_cover_url = ""

    return track


def create_track(owner, form: "TrackForm") -> Track:
    track = form.save(commit=False)
    track.owner = owner
    track = _apply_track_source_logic(track, form, previous_state=None)
    track.save()
    form.save_m2m()
    return track


def update_track(track: Track, form: "TrackForm") -> Track:
    previous_state = {
        "source_type": track.source_type,
        "youtube_url": track.youtube_url,
        "audio_file_name": track.audio_file.name if track.audio_file else "",
    }

    updated_track = form.save(commit=False)
    updated_track.owner = track.owner
    updated_track = _apply_track_source_logic(updated_track, form, previous_state=previous_state)
    updated_track.save()
    form.save_m2m()
    return updated_track


def delete_track(track: Track) -> None:
    track.delete()
