from __future__ import annotations

import time
from channels.middleware import BaseMiddleware
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser
from django.conf import settings


def _bucket_key(prefix: str, identifier: str) -> str:
    return f"wsrl:{prefix}:{identifier}:{int(time.time() // 60)}"  # per-minute window


class RateLimitMiddleware(BaseMiddleware):
    """
    Basic WebSocket rate limiting:
    - Limit connection attempts per IP per minute
    - Limit messages per user per minute
    Uses Django cache; in production with Redis this is shared across workers.
    """

    async def __call__(self, scope, receive, send):
        conn_limit = int(getattr(settings, "WS_CONN_MAX_PER_MINUTE", 60) or 60)
        msg_limit = int(getattr(settings, "WS_MSG_MAX_PER_MINUTE", 120) or 120)

        # Connection attempts per IP
        client = scope.get("client") or (None, None)
        ip = client[0] or "-"
        key_conn = _bucket_key("conn", ip)
        try:
            current = cache.get(key_conn, 0)
            if current >= conn_limit:
                # Deny by closing handshake early
                # We cannot send a close code here easily without fully accepting; just drop through.
                return  # silently refuse
            cache.incr(key_conn)
        except Exception:
            cache.set(key_conn, 1, timeout=120)
        finally:
            cache.expire(key_conn, 120) if hasattr(cache, "expire") else None

        # Wrap receive to count messages
        async def limited_receive():
            event = await receive()
            if event.get("type") == "websocket.receive":
                user = scope.get("user")
                ident = "anon" if isinstance(user, AnonymousUser) else str(getattr(user, "id", "anon"))
                key_msg = _bucket_key("msg", ident)
                try:
                    count = cache.get(key_msg, 0)
                    if count >= msg_limit:
                        # Transform into a close event to shed load
                        return {"type": "websocket.close", "code": 1013}  # try again later
                    cache.incr(key_msg)
                except Exception:
                    cache.set(key_msg, 1, timeout=120)
                finally:
                    cache.expire(key_msg, 120) if hasattr(cache, "expire") else None
            return event

        return await super().__call__(scope, limited_receive, send)
