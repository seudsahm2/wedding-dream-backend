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

"""
Production security & HTTPS

Notes when running behind a reverse proxy (e.g., Nginx/Traefik):
- Ensure the proxy sets X-Forwarded-Proto and X-Forwarded-Host correctly.
- USE_X_FORWARDED_HOST/PORT should be enabled so Django builds absolute URLs properly.
- If you have a health endpoint that must remain HTTP (no redirect), add it to SECURE_REDIRECT_EXEMPT.
"""

# Honor proxy headers for scheme and host
USE_X_FORWARDED_HOST = _env.bool('USE_X_FORWARDED_HOST', default=True)  # type: ignore[arg-type]
USE_X_FORWARDED_PORT = _env.bool('USE_X_FORWARDED_PORT', default=True)  # type: ignore[arg-type]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HTTPS enforcement and redirect exemptions (regex list)
SECURE_SSL_REDIRECT = _env.bool('SECURE_SSL_REDIRECT', default=True)  # type: ignore[arg-type]
SECURE_REDIRECT_EXEMPT = _env.list('SECURE_REDIRECT_EXEMPT', default=[r'^health/?$'])  # type: ignore[arg-type]

# HSTS
SECURE_HSTS_SECONDS = _env.int('SECURE_HSTS_SECONDS', default=31536000)  # type: ignore[arg-type]
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)  # type: ignore[arg-type]
SECURE_HSTS_PRELOAD = _env.bool('SECURE_HSTS_PRELOAD', default=True)  # type: ignore[arg-type]

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = _env.bool('SECURE_CONTENT_TYPE_NOSNIFF', default=True)  # type: ignore[arg-type]
SECURE_REFERRER_POLICY = _env.str('SECURE_REFERRER_POLICY', default='same-origin')  # type: ignore[arg-type]
X_FRAME_OPTIONS = _env.str('X_FRAME_OPTIONS', default='DENY')  # type: ignore[arg-type]
SECURE_CROSS_ORIGIN_OPENER_POLICY = _env.str('SECURE_CROSS_ORIGIN_OPENER_POLICY', default='same-origin')  # type: ignore[arg-type]

# Cookies: secure, HttpOnly, and SameSite
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = _env.bool('SESSION_COOKIE_HTTPONLY', default=True)  # type: ignore[arg-type]
SESSION_COOKIE_SAMESITE = _env.str('SESSION_COOKIE_SAMESITE', default='Lax')  # type: ignore[arg-type]
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = _env.bool('CSRF_COOKIE_HTTPONLY', default=True)  # type: ignore[arg-type]
CSRF_COOKIE_SAMESITE = _env.str('CSRF_COOKIE_SAMESITE', default='Lax')  # type: ignore[arg-type]

# Email backend config via env expected

# Logging can be expanded later (JSON structure, request IDs)
