from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from core.throttling import AuthLoginThrottle, AuthLoginUserThrottle, AuthRegisterThrottle
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.core.cache import cache
from .serializers import UnifiedUserCreateSerializer
from django.conf import settings
from .session_utils import session_hashes
from .models import UserSession

def send_activation_email_if_needed(user):  # utility for normal user registration
    try:
        from djoser.utils import encode_uid
        from djoser.tokens import default_token_generator
        from djoser import email as djoser_email
        # Deduplicate within 10 seconds (cache.add returns False if key already exists)
        key = f"activation_email_suppress:{user.id}"
        if not cache.add(key, '1', timeout=10):
            return
        uuid = encode_uid(user.pk)
        token = default_token_generator.make_token(user)
        context = {"user": user, "uid": uuid, "token": token}
        email_cls = getattr(djoser_email, 'ActivationEmail', None)
        if email_cls:
            email_cls(context=context).send(to=[user.email])
    except Exception:
        pass


class ThrottledTokenObtainPairView(TokenObtainPairView):
    # Apply both IP-based and username-based throttles
    throttle_classes = [AuthLoginThrottle, AuthLoginUserThrottle]
    serializer_class = TokenObtainPairSerializer

    def post(self, request: Request, *args, **kwargs):  # type: ignore[override]
        import logging
        logger = logging.getLogger('wedding_dream.auth')
        username = str(request.data.get('username') or '').strip()
        ip = request.META.get('REMOTE_ADDR')
        try:
            # Optional reCAPTCHA gate for login
            try:
                from django.conf import settings as dj_settings
                if getattr(dj_settings, 'RECAPTCHA_ENABLED', False) and 'login' in getattr(dj_settings, 'RECAPTCHA_ENFORCE_ENDPOINTS', set()):
                    token = request.data.get('recaptcha_token') or ''
                    if not token:
                        from rest_framework.exceptions import ValidationError
                        raise ValidationError({'recaptcha_token': ['Missing reCAPTCHA token']})
                    from core.recaptcha import verify_recaptcha
                    ok, reason, score = verify_recaptcha(token, ip)
                    if not ok:
                        from rest_framework.exceptions import ValidationError
                        raise ValidationError({'recaptcha_token': [f'Failed ({reason})']})
            except Exception as _e:
                # If the exception is a ValidationError, let it propagate
                from rest_framework.exceptions import ValidationError as DRFVE
                if isinstance(_e, DRFVE):
                    raise
                logger.debug('recaptcha_login_check_error', exc_info=True)
            response: Response = super().post(request, *args, **kwargs)
            # Attempt to extract refresh token JTI (SimpleJWT encodes jti inside refresh token payload)
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                data = getattr(response, 'data', {}) or {}
                refresh_raw = data.get('refresh')
                if refresh_raw:
                    rt = RefreshToken(refresh_raw)
                    jti = str(rt.get('jti'))
                    ua = request.META.get('HTTP_USER_AGENT') or ''
                    ip_salt = getattr(settings, 'SESSION_IP_HASH_SALT', 'session-salt')
                    jti_hash, ua_hash, ip_hash, label = session_hashes(jti, ua, ip, ip_salt)
                    # Enforce max active sessions cap
                    max_active = getattr(settings, 'SESSION_MAX_ACTIVE', 20)
                    if UserSession.objects.filter(user=rt.user, revoked_at__isnull=True).count() >= max_active:
                        # Revoke oldest (by last_seen ascending) to make room
                        oldest = UserSession.objects.filter(user=rt.user, revoked_at__isnull=True).order_by('last_seen').first()
                        if oldest:
                            oldest.mark_revoked()
                    sess = UserSession.objects.create(
                        user=rt.user,
                        jti_hash=jti_hash,
                        user_agent=ua[:300],
                        ua_hash=ua_hash,
                        ip_hash=ip_hash,
                        label=label,
                    )
                    # Attach session public id to response payload to let client mark current
                    # Also embed in access token for server-side current detection if needed
                    data['session_public_id'] = sess.public_id
                    access_raw = data.get('access')
                    if access_raw:
                        from rest_framework_simplejwt.tokens import AccessToken
                        at = AccessToken(access_raw)
                        at['session_pid'] = sess.public_id
                        # Replace access token in response with updated claim
                        data['access'] = str(at)
                        response.data = data
            except Exception:  # pragma: no cover
                logger.debug('session_record_failed', exc_info=True)
            logger.info('login_success', extra={'event': 'login_success', 'username': username, 'ip': ip, 'status_code': response.status_code})
            return response
        except Exception as e:
            logger.warning('login_failure', extra={'event': 'login_failure', 'username': username, 'ip': ip, 'error': str(e)})
            raise


class ThrottledRegisterView(APIView):
    throttle_classes = [AuthRegisterThrottle]

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = UnifiedUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_activation_email_if_needed(user)
        return Response(serializer.to_representation(user), status=status.HTTP_201_CREATED)

