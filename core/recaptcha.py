import logging
from typing import Tuple
from django.conf import settings
import json
from urllib import request, parse

logger = logging.getLogger(__name__)

VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

def verify_recaptcha(token: str, remote_ip: str | None = None) -> Tuple[bool, str, float | None]:
    """Verify reCAPTCHA token with Google.

    Returns (ok, reason, score)
    For v2 the score will be None.
    """
    if not settings.RECAPTCHA_ENABLED:
        return True, "disabled", None
    secret = settings.RECAPTCHA_SECRET_KEY
    if not secret:
        logger.warning("reCAPTCHA enabled but secret key missing")
        return False, "server_misconfigured", None
    data = {"secret": secret, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    payload = parse.urlencode(data).encode()
    try:
        with request.urlopen(VERIFY_URL, data=payload, timeout=5) as resp:
            raw = resp.read().decode()
            parsed = json.loads(raw)
    except Exception as e:  # pragma: no cover (network error path)
        logger.exception("reCAPTCHA verification error: %s", e)
        return False, "verification_error", None

    success = parsed.get("success", False)
    score = parsed.get("score") if settings.RECAPTCHA_VERSION == 'v3' else None
    action = parsed.get("action")
    if not success:
        return False, "recaptcha_failed", score
    if settings.RECAPTCHA_VERSION == 'v3':
        min_score = getattr(settings, "RECAPTCHA_MIN_SCORE", 0.5)
        if score is not None and score < min_score:
            return False, f"low_score:{score}", score
    return True, action or "ok", score
