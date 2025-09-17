from wedding_dream.settings import base as _base
import os

# Pull in all uppercase settings from base
globals().update({k: v for k, v in _base.__dict__.items() if k.isupper()})

DEBUG = False

# Security & hosts
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()]

# CORS & CSRF
CORS_ALLOW_ALL_ORIGINS = False
if not globals().get('CORS_ALLOWED_ORIGINS'):
    CORS_ALLOWED_ORIGINS = []  # must be set via env

# Security headers (initial, can expand later)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', '1') == '1'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = 'same-origin'

# Email backend config via env expected

# Logging can be expanded later (JSON structure, request IDs)
