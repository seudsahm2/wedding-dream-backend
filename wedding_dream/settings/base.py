from pathlib import Path
import os
import environ  # type: ignore[import-not-found]

BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env(
    DEBUG=(bool, False),
)
# Load .env if present at project root
env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env.str('SECRET_KEY', default='insecure-default-change-me')  # type: ignore[arg-type]

# Default: DEBUG false; overridden in dev.py
DEBUG = env.bool('DEBUG', default=False)  # type: ignore[arg-type]

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])  # type: ignore[arg-type]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party apps
    "channels",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "rest_framework_simplejwt",
    "djoser",

    # Local apps
    "core",
    "listings",
    "reviews",
    "messaging",
    "wishlist",
    "users",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wedding_dream.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "wedding_dream.wsgi.application"
ASGI_APPLICATION = "wedding_dream.asgi.application"

DATABASES = {
    "default": env.db('DATABASE_URL', default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),  # type: ignore[arg-type]
}

# Static files (collected for production)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files (user uploads) — local dev defaults
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Backend repo-provided assets (images under backend/assets/) for dev/demo
# We serve these at /assets/ when DEBUG; in production you should host on a CDN
BACKEND_ASSETS_URL = "/assets/"
BACKEND_ASSETS_DIR = BASE_DIR / "assets"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_RENDERER_CLASSES_TEMPLATE_PACK": "rest_framework/vertical/",
    "EXCEPTION_HANDLER": "core.exceptions.exception_handler",
}

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "guest_reviews": "5/hour",
    "contact_requests": "10/hour",
    # Per-user throttles (scoped in views)
    "user_reviews": "20/hour",            # posting reviews while authenticated
    "messages_send": "60/minute",         # sending chat messages
    "threads_start": "20/hour",           # starting new threads
    "wishlist_modify": "60/hour",         # wishlist add/remove per user
    "preferences_update": "30/hour",      # profile updates per user
    "contact_requests_user": "20/hour",   # authenticated contact requests
    # Optional auth endpoints (Djoser) — to be wired if/when supported
    "auth_login": "20/hour",
    "auth_register": "10/hour",
}

DJOSER = {
    "LOGIN_FIELD": "username",
    "SERIALIZERS": {},
}

from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# CORS defaults (tighten in prod.py, relax in dev.py)
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])  # type: ignore[arg-type]
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)  # type: ignore[arg-type]
CORS_URLS_REGEX = r'^/api/.*$'

# Channels layer: default to in-memory; prod.py can override with Redis
CHANNEL_LAYERS: dict = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
REDIS_URL = env.str('REDIS_URL', default='')  # type: ignore[arg-type]
if REDIS_URL:
    CHANNEL_LAYERS["default"] = {  # type: ignore[assignment]
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }

# WebSocket allowed origins (used by custom Channels auth/rate-limit middleware)
WS_ALLOWED_ORIGINS = env.list('WS_ALLOWED_ORIGINS', default=['http://localhost:5173', 'http://127.0.0.1:5173'])  # type: ignore[arg-type]
# Basic runtime limits (connections per IP per minute, messages per user per minute)
WS_CONN_MAX_PER_MINUTE = env.int('WS_CONN_MAX_PER_MINUTE', default=60)  # type: ignore[arg-type]
WS_MSG_MAX_PER_MINUTE = env.int('WS_MSG_MAX_PER_MINUTE', default=120)  # type: ignore[arg-type]

# Email backend (optional: for prod)
EMAIL_BACKEND = env.str('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')  # type: ignore[arg-type]
EMAIL_HOST = env.str('EMAIL_HOST', default='')  # type: ignore[arg-type]
EMAIL_PORT = env.int('EMAIL_PORT', default=587)  # type: ignore[arg-type]
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)  # type: ignore[arg-type]
EMAIL_HOST_USER = env.str('EMAIL_HOST_USER', default='')  # type: ignore[arg-type]
EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD', default='')  # type: ignore[arg-type]

# Sentry DSN (optional)
SENTRY_DSN = env.str('SENTRY_DSN', default='')  # type: ignore[arg-type]

# Media storage backend selection (local | supabase)
MEDIA_STORAGE_BACKEND = env.str('MEDIA_STORAGE_BACKEND', default='local')  # type: ignore[arg-type]

# Supabase (optional) — used when MEDIA_STORAGE_BACKEND=supabase
# For public buckets, media URL will be constructed as:
#   {SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{path}
# For private buckets you will need to implement signed URL generation.
SUPABASE_URL = env.str('SUPABASE_URL', default='')  # type: ignore[arg-type]
SUPABASE_BUCKET = env.str('SUPABASE_BUCKET', default='')  # type: ignore[arg-type]
SUPABASE_ANON_KEY = env.str('SUPABASE_ANON_KEY', default='')  # type: ignore[arg-type]
SUPABASE_SERVICE_ROLE_KEY = env.str('SUPABASE_SERVICE_ROLE_KEY', default='')  # type: ignore[arg-type]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Celery common defaults (dev may override broker/result to local memory)
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL', default=REDIS_URL or 'redis://127.0.0.1:6379/2')  # type: ignore[arg-type]
CELERY_RESULT_BACKEND = env.str('CELERY_RESULT_BACKEND', default=REDIS_URL or 'redis://127.0.0.1:6379/3')  # type: ignore[arg-type]
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False)  # type: ignore[arg-type]
CELERY_TASK_TIME_LIMIT = env.int('CELERY_TASK_TIME_LIMIT', default=300)  # type: ignore[arg-type]
CELERY_TASK_SOFT_TIME_LIMIT = env.int('CELERY_TASK_SOFT_TIME_LIMIT', default=240)  # type: ignore[arg-type]
CELERY_WORKER_MAX_TASKS_PER_CHILD = env.int('CELERY_WORKER_MAX_TASKS_PER_CHILD', default=1000)  # type: ignore[arg-type]
CELERY_WORKER_PREFETCH_MULTIPLIER = env.int('CELERY_WORKER_PREFETCH_MULTIPLIER', default=1)  # type: ignore[arg-type]

# Optional celery beat example schedule (can be enabled when running beat)
from celery.schedules import crontab  # type: ignore
CELERY_BEAT_SCHEDULE = {
    "cleanup-temp-files-hourly": {
        "task": "core.tasks.cleanup_temp_files",
        "schedule": crontab(minute=0),  # every hour
    },
}
