#!/usr/bin/env sh
set -e

echo "[entrypoint] Starting initialization"

# Simplified: prefer DEV_DATABASE_URL if present (local dev), else MIGRATION_DATABASE_URL, else DATABASE_URL
EFFECTIVE_DB_URL=""
if [ -n "$DEV_DATABASE_URL" ]; then
	EFFECTIVE_DB_URL="$DEV_DATABASE_URL"
elif [ -n "$MIGRATION_DATABASE_URL" ]; then
	EFFECTIVE_DB_URL="$MIGRATION_DATABASE_URL"
elif [ -n "$DATABASE_URL" ]; then
	EFFECTIVE_DB_URL="$DATABASE_URL"
fi

if [ -z "$EFFECTIVE_DB_URL" ]; then
	echo "[entrypoint][FATAL] No database URL provided (MIGRATION_DATABASE_URL / DATABASE_URL / DEV_DATABASE_URL)." >&2
	exit 1
fi

echo "[entrypoint] Using DB URL for migrate: ${EFFECTIVE_DB_URL%%:*}//***@${EFFECTIVE_DB_URL#*@} (redacted credentials)"

SKIP_AUTO_MIGRATE=0
if [ "$1" = "python" ] && [ "$2" = "manage.py" ]; then
	case "$3" in
		makemigrations|shell|showmigrations|collectstatic|createsuperuser)
			SKIP_AUTO_MIGRATE=1
			;;
	esac
fi

wait_for_db() {
	ATTEMPTS=${DB_CONNECT_ATTEMPTS:-8}
	SLEEP=${DB_CONNECT_SLEEP:-3}
	i=1
	while [ $i -le $ATTEMPTS ]; do
		python - <<PY || true
import os, sys
import psycopg2
url = os.environ.get('EFFECTIVE_DB_URL')
try:
		psycopg2.connect(url, connect_timeout=5).close()
		print('DB reachable')
		sys.exit(0)
except Exception as e:
		print(f'Attempt {os.environ.get("i")} failed: {e}')
		sys.exit(1)
PY
		status=$?
		if [ $status -eq 0 ]; then
			return 0
		fi
		if [ $i -lt $ATTEMPTS ]; then
			echo "[entrypoint] DB not ready (attempt $i/$ATTEMPTS) — retrying in ${SLEEP}s"
			sleep $SLEEP
		fi
		i=$((i+1))
	done
	echo "[entrypoint][FATAL] Database not reachable after $ATTEMPTS attempts" >&2
	return 1
}

if [ $SKIP_AUTO_MIGRATE -eq 0 ]; then
	echo "[entrypoint] Waiting for database connectivity..."
	if ! EFFECTIVE_DB_URL="$EFFECTIVE_DB_URL" wait_for_db; then
		echo "[entrypoint][FATAL] Database unreachable." >&2
		exit 1
	fi
	echo "[entrypoint] Applying migrations"
	# Export DATABASE_URL for Django (so ORM uses whichever effective one succeeded)
	export DATABASE_URL="$EFFECTIVE_DB_URL"
	python manage.py migrate --noinput
else
	echo "[entrypoint] Skipping auto migrate for management command: $3"
fi

if [ "${DJANGO_SETTINGS_MODULE}" = "wedding_dream.settings.prod" ]; then
	echo "[entrypoint] Collecting static files"
	python manage.py collectstatic --noinput
fi

echo "[entrypoint] Launching: $@"
exec "$@"

