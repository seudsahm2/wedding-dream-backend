import os
from wedding_dream.settings import base as _base

# Pull in all uppercase settings from base
globals().update({k: v for k, v in _base.__dict__.items() if k.isupper()})

# Overrides for development
DEBUG = True

# Common dev defaults if not explicitly set
if not globals().get('CORS_ALLOWED_ORIGINS'):
    CORS_ALLOW_ALL_ORIGINS = True  # type: ignore[assignment]

# Allowed hosts for dev
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
# Ensure Django test client host is allowed to prevent DisallowedHost during tests
if 'testserver' not in ALLOWED_HOSTS:  # pragma: no cover - simple defensive addition
    ALLOWED_HOSTS.append('testserver')

# Database selection precedence (development):
# 1. DEV_DATABASE_URL (explicit dev override)
# 2. DATABASE_URL (e.g., Supabase or local Postgres)
# 3. Fallback to SQLite file
_dev_override = os.environ.get('DEV_DATABASE_URL', '').strip()
_db_url = os.environ.get('DATABASE_URL', '').strip()
if _dev_override:
    _dev_db = _base.env.db('DEV_DATABASE_URL')  # type: ignore[arg-type]
elif _db_url:
    _dev_db = _base.env.db('DATABASE_URL')  # type: ignore[arg-type]
else:
    _dev_db = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(_base.BASE_DIR / "db.sqlite3"),
    }
globals()["DATABASES"]["default"] = _dev_db  # type: ignore[index]

"""Development email configuration

Priority:
1. If DEV_EMAIL_BACKEND is set, honor all DEV_EMAIL_* env vars.
2. Else, if MAILPIT is running (assumed via docker-compose override), use Mailpit SMTP (host=mailpit, port=1025, no auth/TLS).
3. Else, fallback to console backend.
"""
_explicit_dev_backend = _base.env.str('DEV_EMAIL_BACKEND', default='').strip()
if _explicit_dev_backend:
    EMAIL_BACKEND = _explicit_dev_backend  # type: ignore[assignment]
    EMAIL_HOST = _base.env.str('DEV_EMAIL_HOST', default='')  # type: ignore[arg-type]
    EMAIL_PORT = _base.env.int('DEV_EMAIL_PORT', default=587)  # type: ignore[arg-type]
    EMAIL_USE_TLS = _base.env.bool('DEV_EMAIL_USE_TLS', default=True)  # type: ignore[arg-type]
    EMAIL_HOST_USER = _base.env.str('DEV_EMAIL_HOST_USER', default='')  # type: ignore[arg-type]
    EMAIL_HOST_PASSWORD = _base.env.str('DEV_EMAIL_HOST_PASSWORD', default='')  # type: ignore[arg-type]
else:
    # Try Mailpit (container service name 'mailpit')
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # type: ignore[assignment]
    EMAIL_HOST = 'mailpit'  # type: ignore[assignment]
    EMAIL_PORT = 1025  # type: ignore[assignment]
    EMAIL_USE_TLS = False  # type: ignore[assignment]
    EMAIL_HOST_USER = ''  # type: ignore[assignment]
    EMAIL_HOST_PASSWORD = ''  # type: ignore[assignment]

DEFAULT_FROM_EMAIL = _base.env.str('DEFAULT_FROM_EMAIL', default='no-reply@localhost.test')  # type: ignore[arg-type]

# Note: If you want an additional looser daily cap for username reminders,
# you can later introduce a second throttle scope (e.g., username_reminder_day)
# and include it on the view. For now we keep a single conservative scope.
