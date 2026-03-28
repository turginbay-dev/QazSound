from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    from mutagen import File as MutagenFile
except ImportError:  # pragma: no cover - optional until dependency install completes
    MutagenFile = None


MAX_COVER_DIMENSION = 1600
JPEG_QUALITY = 84
WEBP_QUALITY = 82


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _first_tag_value(*values) -> str:
    for value in values:
        if isinstance(value, (list, tuple)):
            value = value[0] if value else ""
        cleaned = _collapse_whitespace(str(value or ""))
        if cleaned:
            return cleaned
    return ""


def guess_audio_metadata_from_filename(file_name: str) -> dict:
    stem = _collapse_whitespace(Path(file_name or "").stem.replace("_", " "))
    if not stem:
        return {}

    parts = [part.strip(" -") for part in stem.split(" - ") if part.strip(" -")]
    if len(parts) >= 2:
        return {
            "artist_name": parts[0],
            "title": " - ".join(parts[1:]),
        }
    return {"title": stem}


def extract_audio_upload_metadata(uploaded_file) -> dict:
    metadata = {
        "title": "",
        "artist_name": "",
        "duration_seconds": None,
    }
    metadata.update(guess_audio_metadata_from_filename(getattr(uploaded_file, "name", "")))

    if MutagenFile is None or not uploaded_file:
        return metadata

    original_position = None
    if hasattr(uploaded_file, "tell"):
        try:
            original_position = uploaded_file.tell()
        except Exception:
            original_position = None

    try:
        uploaded_file.seek(0)
    except Exception:
        return metadata

    try:
        audio = MutagenFile(uploaded_file, easy=True)
    except Exception:
        audio = None
    finally:
        if original_position is not None:
            try:
                uploaded_file.seek(original_position)
            except Exception:
                pass

    if not audio:
        return metadata

    tags = getattr(audio, "tags", {}) or {}
    metadata["title"] = _first_tag_value(tags.get("title"), metadata["title"])
    metadata["artist_name"] = _first_tag_value(
        tags.get("artist"),
        tags.get("albumartist"),
        tags.get("composer"),
        metadata["artist_name"],
    )

    duration = getattr(getattr(audio, "info", None), "length", None)
    if isinstance(duration, (int, float)) and duration > 0:
        metadata["duration_seconds"] = max(1, int(round(duration)))

    return metadata


def optimize_cover_upload(uploaded_file):
    if not uploaded_file:
        return uploaded_file

    original_position = None
    if hasattr(uploaded_file, "tell"):
        try:
            original_position = uploaded_file.tell()
        except Exception:
            original_position = None

    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
    except (UnidentifiedImageError, OSError):
        if original_position is not None:
            try:
                uploaded_file.seek(original_position)
            except Exception:
                pass
        return uploaded_file

    if getattr(image, "is_animated", False):
        if original_position is not None:
            try:
                uploaded_file.seek(original_position)
            except Exception:
                pass
        return uploaded_file

    original_size = getattr(uploaded_file, "size", 0) or 0
    image = ImageOps.exif_transpose(image)
    image.load()

    was_resized = max(image.size) > MAX_COVER_DIMENSION
    if was_resized:
        image.thumbnail((MAX_COVER_DIMENSION, MAX_COVER_DIMENSION), Image.Resampling.LANCZOS)

    has_alpha = image.mode in {"RGBA", "LA"} or image.info.get("transparency") is not None
    output = BytesIO()

    if has_alpha:
        converted = image.convert("RGBA")
        target_suffix = ".webp"
        content_type = "image/webp"
        converted.save(output, format="WEBP", quality=WEBP_QUALITY, method=6)
    else:
        converted = image.convert("RGB")
        target_suffix = ".jpg"
        content_type = "image/jpeg"
        converted.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)

    optimized_bytes = output.getvalue()
    if original_size and len(optimized_bytes) >= original_size and not was_resized:
        if original_position is not None:
            try:
                uploaded_file.seek(original_position)
            except Exception:
                pass
        return uploaded_file

    file_name = f"{Path(uploaded_file.name).stem}{target_suffix}"
    return SimpleUploadedFile(file_name, optimized_bytes, content_type=content_type)
