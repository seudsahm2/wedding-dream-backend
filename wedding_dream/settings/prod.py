from wedding_dream.settings import base as _base
import environ  # type: ignore[import-not-found]
import logging
import sys

# Pull in all uppercase settings from base
globals().update({k: v for k, v in _base.__dict__.items() if k.isupper()})

DEBUG = False

# Security & hosts
_env = getattr(_base, 'env', environ.Env())
_base_allowed_hosts = getattr(_base, 'ALLOWED_HOSTS', ['127.0.0.1', 'localhost'])
ALLOWED_HOSTS = _env.list('ALLOWED_HOSTS', default=_base_allowed_hosts)  # type: ignore[arg-type]

# CORS & CSRF
# Never allow-all in prod
CORS_ALLOW_ALL_ORIGINS = False
# Allowed origins (exact) and optional regex patterns
CORS_ALLOWED_ORIGINS = _env.list('CORS_ALLOWED_ORIGINS', default=[])  # type: ignore[arg-type]
CORS_ALLOWED_ORIGIN_REGEXES = _env.list('CORS_ALLOWED_ORIGIN_REGEXES', default=[])  # type: ignore[arg-type]
# Allow cookies/Authorization headers when needed
CORS_ALLOW_CREDENTIALS = _env.bool('CORS_ALLOW_CREDENTIALS', default=True)  # type: ignore[arg-type]

# CSRF: add your admin/API domains, including scheme and port
CSRF_TRUSTED_ORIGINS = _env.list('CSRF_TRUSTED_ORIGINS', default=[])  # type: ignore[arg-type]

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
EMAIL_BACKEND = _env.str('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')  # type: ignore[arg-type]
EMAIL_HOST = _env.str('EMAIL_HOST', default='smtp.sendgrid.net')  # type: ignore[arg-type]
EMAIL_PORT = _env.int('EMAIL_PORT', default=587)  # type: ignore[arg-type]
EMAIL_USE_TLS = _env.bool('EMAIL_USE_TLS', default=True)  # type: ignore[arg-type]
EMAIL_HOST_USER = _env.str('EMAIL_HOST_USER', default='apikey')  # type: ignore[arg-type]
EMAIL_HOST_PASSWORD = _env.str('EMAIL_HOST_PASSWORD', default='')  # type: ignore[arg-type]
DEFAULT_FROM_EMAIL = _env.str('DEFAULT_FROM_EMAIL', default='noreply@your-domain.example')  # type: ignore[arg-type]

# Celery: ensure Redis broker/result are set for prod
CELERY_BROKER_URL = _env.str('CELERY_BROKER_URL', default=_base.REDIS_URL or 'redis://127.0.0.1:6379/2')  # type: ignore[arg-type]
CELERY_RESULT_BACKEND = _env.str('CELERY_RESULT_BACKEND', default=_base.REDIS_URL or 'redis://127.0.0.1:6379/3')  # type: ignore[arg-type]

# Logging can be expanded later (JSON structure, request IDs)
SLOW_REQUEST_THRESHOLD_MS = _env.int('SLOW_REQUEST_THRESHOLD_MS', default=1000)  # type: ignore[arg-type]
SLOW_DB_QUERY_MS = _env.int('SLOW_DB_QUERY_MS', default=200)  # type: ignore[arg-type]

# Cache: Redis via django-redis
CACHE_TTL = _env.int('CACHE_TTL', default=300)  # type: ignore[arg-type]
CACHES = {
	"default": {
		"BACKEND": "django_redis.cache.RedisCache",
		"LOCATION": _base.REDIS_URL or _env.str('CACHE_REDIS_URL', default='redis://127.0.0.1:6379/1'),  # type: ignore[arg-type]
		"OPTIONS": {
			"CLIENT_CLASS": "django_redis.client.DefaultClient",
		},
		"TIMEOUT": CACHE_TTL,
	}
}

# Insert request/slow middlewares early, after SecurityMiddleware
_mw = list(getattr(_base, "MIDDLEWARE", []))
_insert_at = 1 if _mw and _mw[0] == "django.middleware.security.SecurityMiddleware" else 0
_mw.insert(_insert_at, "core.middleware.RequestIDMiddleware")
_mw.insert(_insert_at + 1, "core.middleware.SlowRequestLoggingMiddleware")
MIDDLEWARE = _mw

# Structured JSON logging
class RequestIdFilter(logging.Filter):
	def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
		try:
			from core.middleware import request_id_ctx
			record.request_id = request_id_ctx.get()
		except Exception:
			record.request_id = "-"
		return True

LOGGING = {
	"version": 1,
	"disable_existing_loggers": False,
	"filters": {
		"request_id": {
			"()": RequestIdFilter,
		},
		"slow_sql": {
			"()": "wedding_dream.settings.prod.SlowSQLFilter",
		},
	},
	"formatters": {
		"json": {
			"()": "pythonjsonlogger.jsonlogger.JsonFormatter",
			"fmt": "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
		},
	},
	"handlers": {
		"console": {
			"class": "logging.StreamHandler",
			"stream": sys.stdout,
			"filters": ["request_id"],
			"formatter": "json",
		},
		"console_slow_sql": {
			"class": "logging.StreamHandler",
			"stream": sys.stdout,
			"filters": ["request_id", "slow_sql"],
			"formatter": "json",
		},
	},
	"loggers": {
		"django": {"handlers": ["console"], "level": "INFO", "propagate": False},
		"django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
		"wedding_dream": {"handlers": ["console"], "level": "INFO", "propagate": False},
		"wedding_dream.performance": {"handlers": ["console"], "level": "WARNING", "propagate": False},
		# Log all SQL; the slow_sql filter will emit only slow ones via console_slow_sql
		"django.db.backends": {"handlers": ["console_slow_sql"], "level": "DEBUG", "propagate": False},
	},
}

class SlowSQLFilter(logging.Filter):  # pragma: no cover
	def filter(self, record: logging.LogRecord) -> bool:
		try:
			duration: float | None = None
			raw = getattr(record, "duration", None)
			if raw is None and hasattr(record, "args") and isinstance(record.args, dict):
				raw = record.args.get("duration")
			if raw is not None:
				try:
					duration = float(raw)  # type: ignore[arg-type]  # seconds
					duration *= 1000.0  # convert to ms to compare against threshold
				except Exception:
					duration = None
			if duration is None:
				# Try parse from message like "(0.123) SELECT ..."
				msg = str(record.getMessage())
				if msg.startswith("(") and ")" in msg:
					maybe = msg.split(")", 1)[0].strip("(")
					try:
						duration = float(maybe) * 1000.0
					except Exception:
						duration = None
			return bool(duration is not None and duration >= float(SLOW_DB_QUERY_MS))  # type: ignore[arg-type]
		except Exception:
			return False

# Sentry integration (opt-in via SENTRY_DSN)
SENTRY_DSN = _base.SENTRY_DSN
if SENTRY_DSN:
	try:
		import sentry_sdk  # type: ignore
		from sentry_sdk.integrations.django import DjangoIntegration  # type: ignore
		from sentry_sdk.integrations.logging import LoggingIntegration  # type: ignore

		sentry_sdk.init(
			dsn=str(SENTRY_DSN),
			integrations=[
				DjangoIntegration(),
				LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
			],
			traces_sample_rate=_env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),  # type: ignore[arg-type]
			profiles_sample_rate=_env.float("SENTRY_PROFILES_SAMPLE_RATE", default=0.0),  # type: ignore[arg-type]
			send_default_pii=False,
		)
	except Exception:
		pass
