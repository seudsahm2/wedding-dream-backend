from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Expect token in query string: ?token=...
        try:
            query_string = scope.get('query_string', b'').decode()
            query_params = parse_qs(query_string)
            token_list = query_params.get('token', [])
            token = token_list[0] if token_list else None
            if token:
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.get_validated_token(token)
                user = jwt_auth.get_user(validated)
                scope['user'] = user
            else:
                scope['user'] = AnonymousUser()
        except Exception:
            scope['user'] = AnonymousUser()
        return await super().__call__(scope, receive, send)
