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
