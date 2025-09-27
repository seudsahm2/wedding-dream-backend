from django.core.management.base import BaseCommand
from django.conf import settings
import time

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover - should be installed per requirements
    redis = None  # type: ignore


class Command(BaseCommand):
    help = "Perform a health check against configured Redis endpoints (cache, celery broker/result, channel layer)."

    def add_arguments(self, parser):
        parser.add_argument('--timeout', type=float, default=2.5, help='Socket timeout (seconds).')

    def handle(self, *args, **options):
        if not redis:
            self.stderr.write(self.style.ERROR("redis-py not installed"))
            return 1

        timeout = options['timeout']
        endpoints = {}

        cache_loc = getattr(settings, 'CACHE_LOCATION', None) or getattr(settings, 'CACHE_REDIS_URL', None)
        if cache_loc:
            endpoints['cache'] = cache_loc

        broker = getattr(settings, 'CELERY_BROKER_URL', None)
        if broker:
            endpoints['celery_broker'] = broker

        result = getattr(settings, 'CELERY_RESULT_BACKEND', None)
        if result:
            endpoints['celery_result'] = result

        channel_hosts = None
        cl = getattr(settings, 'CHANNEL_LAYERS', {}).get('default', {})
        config = cl.get('CONFIG', {}) if isinstance(cl, dict) else {}
        hosts = config.get('hosts') if isinstance(config, dict) else None
        if hosts:
            channel_hosts = hosts
        if channel_hosts:
            # Normalize single host entries
            for idx, host in enumerate(channel_hosts):
                endpoints[f'channels_{idx}'] = host

        if not endpoints:
            self.stdout.write(self.style.WARNING('No Redis related endpoints discovered.'))
            return 0

        self.stdout.write(f"Checking {len(endpoints)} Redis endpoint(s)...")
        failures = 0
        for key, url in endpoints.items():
            start = time.time()
            try:
                r = redis.from_url(url, socket_timeout=timeout)
                pong = r.ping()
                elapsed = (time.time() - start) * 1000
                if pong:
                    self.stdout.write(self.style.SUCCESS(f"[{key}] OK ({elapsed:.1f} ms)"))
                else:  # pragma: no cover - unlikely branch
                    failures += 1
                    self.stderr.write(self.style.ERROR(f"[{key}] Unexpected PING response"))
            except Exception as exc:  # pragma: no cover - network dependent
                failures += 1
                self.stderr.write(self.style.ERROR(f"[{key}] FAILED: {exc}"))

        if failures:
            self.stderr.write(self.style.ERROR(f"{failures} endpoint(s) failed."))
            return 1
        self.stdout.write(self.style.SUCCESS('All Redis endpoints healthy.'))
        return 0
