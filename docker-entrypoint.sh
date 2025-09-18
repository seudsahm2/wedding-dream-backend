#!/usr/bin/env sh
set -e

# Optional: wait for DB if DATABASE_URL present
if [ -n "$DATABASE_URL" ]; then
	echo "[entrypoint] DATABASE_URL present. Optionally waiting for DB..."
fi

echo "[entrypoint] Applying migrations"
python manage.py migrate --noinput

if [ "${DJANGO_SETTINGS_MODULE}" = "wedding_dream.settings.prod" ]; then
	echo "[entrypoint] Collecting static files"
	python manage.py collectstatic --noinput
fi

echo "[entrypoint] Starting app: $@"
exec "$@"

