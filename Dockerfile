## Multi-stage Dockerfile for wedding_dream backend
# Targets:
#   base     -> system deps & python installed
#   builder  -> install build deps & wheels
#   runtime  -> slim final image with project code & runtime deps

ARG PYTHON_VERSION=3.12
ARG HOST_UID=1000
ARG HOST_GID=1000
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH="/app"

WORKDIR /app

# System deps (psycopg2, Pillow etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    wget \
    git \
  && rm -rf /var/lib/apt/lists/*

FROM base AS builder
COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel \
    && pip wheel --wheel-dir /wheels -r requirements.txt

FROM base AS runtime
LABEL org.opencontainers.image.source="https://github.com/seudsahm2/wedding_dream_backend" \
      org.opencontainers.image.description="Wedding Dream Django Backend" \
      org.opencontainers.image.licenses="MIT"

# Create non-root user matching host UID/GID (fallback 1000:1000)
RUN groupadd -g ${HOST_GID} app || groupadd -r app; \
    useradd -u ${HOST_UID} -g ${HOST_GID} -m app || useradd -r -g app app

COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links /wheels /wheels/*

# Copy project (only necessary files)
# Copy entrypoint outside of /app to avoid losing executable bit when /app is bind-mounted in dev
COPY --chmod=755 docker-entrypoint.sh /entrypoint.sh
COPY manage.py ./
COPY wedding_dream ./wedding_dream
COPY core ./core
COPY listings ./listings
COPY reviews ./reviews
COPY messaging ./messaging
COPY wishlist ./wishlist
COPY users ./users
# assets directory is optional; create empty placeholder so Django STATIC/MEDIA logic doesn't fail if referenced
RUN mkdir -p /app/assets

ENV DJANGO_SETTINGS_MODULE=wedding_dream.settings.prod \
    PORT=8000 \
    GUNICORN_WORKERS=3 \
    GUNICORN_TIMEOUT=60

USER app
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "wedding_dream.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
