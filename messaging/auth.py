from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Basic Origin allowlist to reduce CSRF over WS (not a replacement for auth)
        try:
            origin = None
            for header_name, header_val in scope.get('headers', []) or []:
                if header_name == b'origin':
                    origin = header_val.decode(errors='ignore')
                    break
            allowed = getattr(settings, 'WS_ALLOWED_ORIGINS', [])
            if origin and allowed and origin not in allowed:
                # Short-circuit unauthorized origins
                scope['user'] = AnonymousUser()
                return await super().__call__(scope, receive, send)
        except Exception:
            # Never block on origin parsing errors; continue
            pass

        # Authentication via Authorization: Bearer <token> or query param ?token=
        user = AnonymousUser()
        try:
            token = None
            # Authorization header
            for header_name, header_val in scope.get('headers', []) or []:
                if header_name == b'authorization':
                    value = header_val.decode(errors='ignore')
                    if value.lower().startswith('bearer '):
                        token = value.split(' ', 1)[1].strip()
                        break
            # Fallback to query param
            if not token:
                query_string = scope.get('query_string', b'').decode()
                query_params = parse_qs(query_string)
                token_list = query_params.get('token', [])
                token = token_list[0] if token_list else None
            if token:
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.get_validated_token(token)
                user = jwt_auth.get_user(validated)
        except Exception:
            user = AnonymousUser()

        scope['user'] = user
        return await super().__call__(scope, receive, send)
