
import importlib.util
import json
import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from dotenv import load_dotenv



try:
    import dj_database_url
except ImportError:  # pragma: no cover - optional for local bootstrap before pip install
    dj_database_url = None

try:
    from google.oauth2 import service_account
except ImportError:  # pragma: no cover - optional until Firebase/GCS media storage is enabled
    service_account = None


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


def _build_firebase_credentials(base_dir: Path):
    credentials_json = _env_str("FIREBASE_CREDENTIALS_JSON")
    credentials_path = _env_str("FIREBASE_CREDENTIALS_PATH")

    if not credentials_json and not credentials_path:
        return None

    if service_account is None:
        raise ImproperlyConfigured(
            "Firebase storage credentials were provided, but google-auth is not installed. "
            "Run `pip install -r requirements.txt`."
        )

    if credentials_json:
        try:
            payload = json.loads(credentials_json)
        except json.JSONDecodeError as exc:
            raise ImproperlyConfigured("FIREBASE_CREDENTIALS_JSON must contain valid JSON.") from exc
        return service_account.Credentials.from_service_account_info(payload)

    credentials_file = Path(credentials_path)
    if not credentials_file.is_absolute():
        credentials_file = base_dir / credentials_file
    if not credentials_file.exists():
        raise ImproperlyConfigured(f"Firebase credentials file was not found: {credentials_file}")
    return service_account.Credentials.from_service_account_file(credentials_file)


SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-secret-key")
DEBUG = _env_bool("DEBUG", default=True)
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
DATABASE_URL = _env_str("DATABASE_URL")
FIREBASE_STORAGE_BUCKET = _env_str("FIREBASE_STORAGE_BUCKET")
ENABLE_STORAGE_STARTUP_LOGS = _env_bool("ENABLE_STORAGE_STARTUP_LOGS", default=not DEBUG)
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.tracks",
    "apps.users",
    "apps.interactions",
]

if FIREBASE_STORAGE_BUCKET:
    raise ImproperlyConfigured(f"BUCKET_SEEN::{FIREBASE_STORAGE_BUCKET}")
    if importlib.util.find_spec("storages") is None:
        raise ImproperlyConfigured(
            "FIREBASE_STORAGE_BUCKET is set, but django-storages is not installed. "
            "Run `pip install -r requirements.txt`."
        )
    INSTALLED_APPS.append("storages")

if importlib.util.find_spec("jazzmin") is not None:
    INSTALLED_APPS.insert(0, "jazzmin")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.template.context_processors.media",
                "django.template.context_processors.tz",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

if DATABASE_URL:
    if dj_database_url is None:
        raise ImproperlyConfigured(
            "DATABASE_URL is set, but dj-database-url is not installed. "
            "Run `pip install -r requirements.txt`."
        )
    DATABASES["default"] = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=_env_int("DB_CONN_MAX_AGE", default=600),
        ssl_require=not DEBUG,
    )

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "kk"
LANGUAGES = [
    ("kk", "Қазақша"),
    ("ru", "Русский"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
    if DEBUG
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": STATICFILES_STORAGE},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
SERVE_LOCAL_MEDIA = True

if FIREBASE_STORAGE_BUCKET:
    firebase_media_location = _env_str("FIREBASE_MEDIA_LOCATION", "media").strip("/")
    firebase_storage_options = {
        "bucket_name": FIREBASE_STORAGE_BUCKET,
        "project_id": _env_str("FIREBASE_PROJECT_ID") or None,
        "credentials": _build_firebase_credentials(BASE_DIR),
        "location": firebase_media_location,
        "default_acl": None,
        "file_overwrite": _env_bool("FIREBASE_FILE_OVERWRITE", default=False),
        "querystring_auth": _env_bool("FIREBASE_QUERYSTRING_AUTH", default=True),
        "expiration": timedelta(seconds=_env_int("FIREBASE_URL_EXPIRATION_SECONDS", default=86400)),
    }
    blob_chunk_size = _env_int("FIREBASE_BLOB_CHUNK_SIZE", default=0)
    if blob_chunk_size > 0:
        firebase_storage_options["blob_chunk_size"] = blob_chunk_size

    STORAGES["default"] = {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {key: value for key, value in firebase_storage_options.items() if value is not None},
    }
    SERVE_LOCAL_MEDIA = False
if _env_bool("DIAG_FIREBASE_BOOT", default=False):
    raise ImproperlyConfigured(
        "QAZ DIAG | "
        f"backend={STORAGES['default']['BACKEND']} | "
        f"bucket={FIREBASE_STORAGE_BUCKET or '-'} | "
        f"serve_local={SERVE_LOCAL_MEDIA} | "
        f"project={_env_str('FIREBASE_PROJECT_ID') or '-'} | "
        f"has_json={'yes' if _env_str('FIREBASE_CREDENTIALS_JSON') else 'no'} | "
        f"has_path={'yes' if _env_str('FIREBASE_CREDENTIALS_PATH') else 'no'} | "
        f"debug={DEBUG}"
    )
if ENABLE_STORAGE_STARTUP_LOGS:
    print(
        "[QazSound storage] "
        f"default_backend={STORAGES['default']['BACKEND']} "
        f"firebase_bucket={FIREBASE_STORAGE_BUCKET or '-'} "
        f"serve_local_media={SERVE_LOCAL_MEDIA} "
        f"debug={DEBUG}"
    )

ENABLE_YTDLP_YOUTUBE_STREAM = _env_bool("ENABLE_YTDLP_YOUTUBE_STREAM", default=True)
YTDLP_STREAM_FORMAT = os.getenv("YTDLP_STREAM_FORMAT", "bestaudio/best")
YTDLP_REQUEST_TIMEOUT_SECONDS = _env_int("YTDLP_REQUEST_TIMEOUT_SECONDS", default=12)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = _env_bool("CSRF_COOKIE_SECURE", default=not DEBUG)

LOGIN_URL = "users:login"
LOGIN_REDIRECT_URL = "tracks:home"
LOGOUT_REDIRECT_URL = "tracks:home"

JAZZMIN_SETTINGS = {
    "site_title": "QazSound Control Panel",
    "site_header": "QazSound Admin",
    "site_brand": "QazSound",
    "site_logo": "img/placeholders/avatar.svg",
    "site_icon": "img/placeholders/avatar.svg",
    "login_logo": "img/placeholders/avatar.svg",
    "welcome_sign": "Welcome to QazSound Control Panel",
    "copyright": "QazSound",
    "search_model": ["tracks.Track", "tracks.Artist", "auth.User", "interactions.Like"],
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"model": "tracks.Track"},
        {"model": "tracks.Artist"},
        {"model": "interactions.Like"},
    ],
    "show_sidebar": True,
    "navigation_expanded": False,
    "hide_apps": ["contenttypes", "sessions"],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "tracks": "fas fa-music",
        "tracks.track": "fas fa-wave-square",
        "tracks.artist": "fas fa-microphone",
        "tracks.genre": "fas fa-tags",
        "interactions": "fas fa-heart",
        "interactions.like": "fas fa-heart",
        "interactions.playlist": "fas fa-list-music",
        "interactions.playlistitem": "fas fa-stream",
    },
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle",
    "custom_css": "admin/custom.css",
    "show_ui_builder": False,
    "related_modal_active": True,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-info",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-info",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
