import time
import uuid
import contextvars
from typing import Callable
from django.db import connections
from django.http import HttpRequest, HttpResponse

# Context var to carry request id into logs
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIDMiddleware:
    """
    Ensures every request has an X-Request-ID. If provided by the client, we honor it;
    otherwise we generate a UUID4. The value is exposed via response header and
    stored in a contextvar for logging filters.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.headers.get("X-Request-ID") or request.META.get("HTTP_X_REQUEST_ID")
        req_id = (incoming or str(uuid.uuid4())).strip()
        request.META["HTTP_X_REQUEST_ID"] = req_id
        token = request_id_ctx.set(req_id)
        try:
            response = self.get_response(request)
        finally:
            # ensure context var is reset even if an exception occurs
            request_id_ctx.reset(token)
        response["X-Request-ID"] = req_id
        return response


class SlowRequestLoggingMiddleware:
    """
    Logs a warning for slow requests exceeding SLOW_REQUEST_THRESHOLD_MS.
    Adds X-Request-Duration-ms header to responses for easy inspection.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        from django.conf import settings

        self.get_response = get_response
        self.threshold_ms: int = int(getattr(settings, "SLOW_REQUEST_THRESHOLD_MS", 1000))

    def __call__(self, request: HttpRequest) -> HttpResponse:
        import logging

        start = time.perf_counter()
        # Enable debug cursor to allow query logging even when DEBUG=False
        prev_states = {}
        for alias in connections:
            conn = connections[alias]
            prev_states[alias] = getattr(conn, "force_debug_cursor", False)
            conn.force_debug_cursor = True
        try:
            response = self.get_response(request)
        finally:
            for alias in connections:
                connections[alias].force_debug_cursor = prev_states.get(alias, False)
        duration_ms = (time.perf_counter() - start) * 1000.0
        response["X-Request-Duration-ms"] = f"{duration_ms:.0f}"

        if duration_ms >= self.threshold_ms:
            logger = logging.getLogger("wedding_dream.performance")
            logger.warning(
                "slow_request",
                extra={
                    "path": request.path,
                    "method": request.method,
                    "status_code": getattr(response, "status_code", None),
                    "duration_ms": int(duration_ms),
                },
            )
        return response


class SecurityHeadersMiddleware:
    """Inject baseline security headers (CSP, Referrer-Policy, X-Frame-Options, etc.).

    CSP kept strict; adjust script-src/style-src if inline or 3rd-party resources are needed.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        from django.conf import settings
        self.get_response = get_response
        # Allow override via settings.CONTENT_SECURITY_POLICY
        base_csp = getattr(
            settings,
            'CONTENT_SECURITY_POLICY_BASE',
            "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; connect-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-src 'none'; upgrade-insecure-requests"
        )
        report_uri = getattr(settings, 'CSP_REPORT_URI', '')
        if report_uri:
            base_csp = f"{base_csp}; report-uri {report_uri}"
        self.default_csp = getattr(settings, 'CONTENT_SECURITY_POLICY', base_csp)
        self.referrer_policy = getattr(settings, 'SECURE_REFERRER_POLICY', 'same-origin')

    def __call__(self, request: HttpRequest) -> HttpResponse:  # pragma: no cover - header injection
        response = self.get_response(request)
        # Only set if not already present to allow per-view customization
        if 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] = self.default_csp
        response['Referrer-Policy'] = self.referrer_policy
        response.setdefault('X-Frame-Options', 'DENY')
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('X-XSS-Protection', '0')  # modern browsers ignore / use CSP
        response.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        return response
