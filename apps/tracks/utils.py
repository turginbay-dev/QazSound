import re
from urllib.parse import parse_qs, urlparse


YOUTUBE_ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
}
YOUTUBE_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_PATH_PATTERN = re.compile(
    r"^/(?:embed|shorts|live|v)/(?P<id>[A-Za-z0-9_-]{11})(?:/|$)"
)


def _coerce_url(raw_url: str) -> str:
    candidate = (raw_url or "").strip()
    if not candidate:
        return ""

    parsed = urlparse(candidate)
    if not parsed.scheme:
        candidate = f"https://{candidate}"

    return candidate


def _is_valid_video_id(candidate: str | None) -> bool:
    if not candidate:
        return False
    return bool(YOUTUBE_ID_PATTERN.fullmatch(candidate))


def is_youtube_domain(url: str) -> bool:
    candidate = _coerce_url(url)
    if not candidate:
        return False

    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False

    host = (parsed.hostname or "").lower()
    return host in YOUTUBE_ALLOWED_HOSTS


def extract_youtube_id(url: str) -> str | None:
    candidate = _coerce_url(url)
    if not candidate:
        return None

    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None

    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_ALLOWED_HOSTS:
        return None

    video_id = None

    if host in YOUTUBE_SHORT_HOSTS:
        video_id = parsed.path.strip("/").split("/")[0]
    else:
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if _is_valid_video_id(query_id):
            video_id = query_id

        if not video_id:
            path_match = YOUTUBE_PATH_PATTERN.match(parsed.path or "")
            if path_match:
                video_id = path_match.group("id")

    if not _is_valid_video_id(video_id):
        return None
    return video_id


def normalize_youtube_url(url: str) -> str:
    video_id = extract_youtube_id(url)
    if not video_id:
        return (url or "").strip()
    return f"https://www.youtube.com/watch?v={video_id}"

