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
