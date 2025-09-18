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

# Database: force SQLite in dev unless DEV_DATABASE_URL is provided
# This avoids accidental use of production DATABASE_URL locally.
_dev_url = os.environ.get('DEV_DATABASE_URL', '').strip()
if _dev_url:
    _dev_db = _base.env.db('DEV_DATABASE_URL')  # type: ignore[arg-type]
else:
    _dev_db = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(_base.BASE_DIR / "db.sqlite3"),
    }
globals()["DATABASES"]["default"] = _dev_db  # type: ignore[index]

# Dev email defaults: Mailgun SMTP (optional). Falls back to console backend if not set.
if not globals().get('EMAIL_BACKEND') or globals().get('EMAIL_BACKEND') == 'django.core.mail.backends.console.EmailBackend':
    EMAIL_BACKEND = _base.env.str('DEV_EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')  # type: ignore[arg-type]
    EMAIL_HOST = _base.env.str('DEV_EMAIL_HOST', default='')  # type: ignore[arg-type]
    EMAIL_PORT = _base.env.int('DEV_EMAIL_PORT', default=587)  # type: ignore[arg-type]
    EMAIL_USE_TLS = _base.env.bool('DEV_EMAIL_USE_TLS', default=True)  # type: ignore[arg-type]
    EMAIL_HOST_USER = _base.env.str('DEV_EMAIL_HOST_USER', default='')  # type: ignore[arg-type]
    EMAIL_HOST_PASSWORD = _base.env.str('DEV_EMAIL_HOST_PASSWORD', default='')  # type: ignore[arg-type]
