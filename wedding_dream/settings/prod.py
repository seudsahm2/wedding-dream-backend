from wedding_dream.settings import base as _base
import environ  # type: ignore[import-not-found]

# Pull in all uppercase settings from base
globals().update({k: v for k, v in _base.__dict__.items() if k.isupper()})

DEBUG = False

# Security & hosts
_env = getattr(_base, 'env', environ.Env())
_base_allowed_hosts = getattr(_base, 'ALLOWED_HOSTS', ['127.0.0.1', 'localhost'])
ALLOWED_HOSTS = _env.list('ALLOWED_HOSTS', default=_base_allowed_hosts)  # type: ignore[arg-type]

# CORS & CSRF
CORS_ALLOW_ALL_ORIGINS = _env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)  # type: ignore[arg-type]
if not globals().get('CORS_ALLOWED_ORIGINS'):
    CORS_ALLOWED_ORIGINS = _env.list('CORS_ALLOWED_ORIGINS', default=[])  # type: ignore[arg-type]

# Security headers (initial, can expand later)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = _env.bool('SECURE_SSL_REDIRECT', default=True)  # type: ignore[arg-type]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = _env.int('SECURE_HSTS_SECONDS', default=31536000)  # type: ignore[arg-type]
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = 'same-origin'

# Email backend config via env expected

# Logging can be expanded later (JSON structure, request IDs)
