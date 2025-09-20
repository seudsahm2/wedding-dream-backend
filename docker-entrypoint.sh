#!/usr/bin/env sh
set -e

# Optional: wait for DB if DATABASE_URL present
if [ -n "$DATABASE_URL" ]; then
	echo "[entrypoint] DATABASE_URL present. Optionally waiting for DB..."
fi

SKIP_AUTO_MIGRATE=0
if [ "$1" = "python" ] && [ "$2" = "manage.py" ]; then
	case "$3" in
		makemigrations|shell|showmigrations|collectstatic|createsuperuser)
			SKIP_AUTO_MIGRATE=1
			;;
	esac
fi

if [ "$SKIP_AUTO_MIGRATE" -eq 0 ]; then
	echo "[entrypoint] Applying migrations"
	python manage.py migrate --noinput || echo "[entrypoint] WARNING: migrate failed (possibly expected for management command)"
else
	echo "[entrypoint] Skipping auto migrate for management command: $3"
fi

if [ "${DJANGO_SETTINGS_MODULE}" = "wedding_dream.settings.prod" ]; then
	echo "[entrypoint] Collecting static files"
	python manage.py collectstatic --noinput
fi

echo "[entrypoint] Starting app: $@"
exec "$@"

