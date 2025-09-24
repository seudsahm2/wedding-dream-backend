from rest_framework import permissions, generics, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import UserProfile, ProviderServiceType, EmailChangeRequest
from .constants import ALLOWED_PROVIDER_COUNTRIES, DIAL_CODE_MAP
from core.throttling import PreferencesUpdateThrottle
from .serializers import (
	UserSerializer,
	UserProfileSerializer,
	ProviderUpgradeSerializer,
	ProviderServiceTypeSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from djoser.views import UserViewSet
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import escape
from django.http import HttpResponse
from django.utils import timezone
from django.conf import settings as dj_settings
import secrets, hashlib


class MeView(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		# Ensure profile exists
		profile, _ = UserProfile.objects.get_or_create(user=request.user)
		serializer = UserSerializer(request.user)
		data = serializer.data
		data["role"] = profile.role
		data["is_provider"] = profile.role == UserProfile.ROLE_PROVIDER
		data["country"] = profile.country
		data["city"] = profile.city
		data["email_verified"] = profile.email_verified
		return Response(data)


class PreferencesView(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated]
	throttle_classes = [PreferencesUpdateThrottle]

	def put(self, request):
		profile, _ = UserProfile.objects.get_or_create(user=request.user)
		serializer = UserProfileSerializer(instance=profile, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data)


class ProviderUpgradeView(generics.GenericAPIView):
	"""Allow an authenticated normal user to become a provider.
	Idempotent: calling again when already provider just returns current profile.
	"""
	permission_classes = [permissions.IsAuthenticated]
	serializer_class = ProviderUpgradeSerializer

	def post(self, request):
		profile, _ = UserProfile.objects.get_or_create(user=request.user)
		update_fields = []
		if profile.role != UserProfile.ROLE_PROVIDER:
			profile.role = UserProfile.ROLE_PROVIDER
			update_fields.append("role")
		# Allow optional business fields on upgrade
		for fld in ["business_name", "business_phone", "business_type"]:
			val = request.data.get(fld)
			if val is not None:
				setattr(profile, fld, val)
				if fld not in update_fields:
					update_fields.append(fld)
		if update_fields:
			profile.save(update_fields=update_fields)
		return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class RegisterProviderView(APIView):
	"""Provider registration (strict + enforced activation).

	Requires: username, password, email, business_name, business_phone, country, city, business_type.
	ALWAYS requires email activation before login or tokens are issued (ignores global SEND_ACTIVATION_EMAIL toggle for this path).
	"""
	permission_classes = []
	authentication_classes = []

	REQUIRED_FIELDS = ["username", "password", "email", "business_name", "business_phone", "country", "city", "business_type"]

	def post(self, request):
		from .serializers import UnifiedUserCreateSerializer
		payload = request.data.copy()
		payload['is_provider'] = True
		payload['password2'] = payload.get('password2') or payload.get('password')  # allow single password field fallback
		ser = UnifiedUserCreateSerializer(data=payload)
		ser.is_valid(raise_exception=True)
		user = ser.save()
		# Send activation email (reuse helper)
		from .auth_views import send_activation_email_if_needed
		send_activation_email_if_needed(user)
		return Response(ser.to_representation(user), status=201)


class ProviderUpgradeView(generics.GenericAPIView):
	"""Upgrade existing authenticated user to provider (strict unified version).

	New: Requires verified email (profile.email_verified). If not verified, returns 403 and
	triggers resend of activation link (best-effort) so user can complete verification first.
	Logs all attempts.
	"""
	permission_classes = [permissions.IsAuthenticated]

	def _log(self, event: str, user, **extra):  # pragma: no cover (logging utility)
		import logging
		logger = logging.getLogger('wedding_dream.auth')
		payload = {"event": event, "user_id": user.id, "username": user.username, **extra}
		logger.info(event, extra=payload)

	def _resend_activation(self, user):  # best-effort resend
		try:
			from djoser.utils import encode_uid
			from djoser.tokens import default_token_generator
			from djoser import email as djoser_email
			uuid = encode_uid(user.pk)
			token = default_token_generator.make_token(user)
			context = {"user": user, "uid": uuid, "token": token}
			email_cls = getattr(djoser_email, 'ActivationEmail', None)
			if email_cls:
				email_cls(context=context).send(to=[user.email])
		except Exception:  # pragma: no cover
			pass

	def post(self, request):
		profile, _ = UserProfile.objects.get_or_create(user=request.user)
		if profile.role == UserProfile.ROLE_PROVIDER:
			self._log('provider_upgrade_already_provider', request.user, email_verified=profile.email_verified)
			ser = UserSerializer(request.user).data
			ser['role'] = profile.role
			ser['is_provider'] = True
			ser['email_verified'] = profile.email_verified
			return Response(ser, status=200)
		if not profile.email_verified:
			# Resend activation and block
			self._resend_activation(request.user)
			self._log('provider_upgrade_blocked_unverified', request.user, email_verified=False)
			return Response({"detail": "Email not verified. Activation link resent."}, status=403)
		# Required fields for upgrade
		required = ["business_name", "business_phone", "business_type", "country", "city"]
		missing = [f for f in required if not str(request.data.get(f, '')).strip()]
		if missing:
			self._log('provider_upgrade_missing_fields', request.user, missing=missing, email_verified=profile.email_verified)
			return Response({"detail": "Missing required fields", "missing": missing}, status=400)
		country = request.data.get('country','').upper()
		if len(country) != 2:
			return Response({"country": ["Must be 2-letter ISO code"]}, status=400)
		if country not in ALLOWED_PROVIDER_COUNTRIES:
			return Response({"country": ["Country not supported yet"]}, status=400)
		city = request.data.get('city','').strip()
		if not city:
			return Response({"city": ["City is required"]}, status=400)
		btype = request.data.get('business_type')
		try:
			if not ProviderServiceType.objects.filter(slug=btype, active=True).exists():
				return Response({"business_type": ["Invalid provider type"]}, status=400)
		except Exception:
			pass
		# Validate phone
		def validate_phone(raw: str, country_code: str):
			import phonenumbers
			try:
				parsed = phonenumbers.parse(raw.strip(), country_code)
				if not phonenumbers.is_valid_number(parsed):
					return False, "Invalid phone number"
				region = phonenumbers.region_code_for_number(parsed)
				if region and region.upper() != country_code.upper():
					return False, "Phone country code mismatch"
				from phonenumbers import PhoneNumberFormat, format_number
				return True, format_number(parsed, PhoneNumberFormat.E164)
			except Exception:
				return False, "Could not parse phone number"
		ok_phone, norm_phone = validate_phone(request.data['business_phone'], country)
		if not ok_phone:
			return Response({"business_phone": [norm_phone]}, status=400)
		profile.business_name = request.data['business_name']
		profile.business_phone = norm_phone
		profile.business_type = btype
		profile.country = country
		profile.city = city
		profile.role = UserProfile.ROLE_PROVIDER
		profile.save()
		ser = UserSerializer(request.user).data
		ser['role'] = profile.role
		ser['is_provider'] = True
		ser['country'] = profile.country
		ser['business_phone'] = profile.business_phone
		ser['email_verified'] = profile.email_verified
		self._log('provider_upgrade_success', request.user, email_verified=profile.email_verified)
		return Response(ser, status=200)


class ProviderServiceTypeListView(generics.ListAPIView):
	queryset = ProviderServiceType.objects.filter(active=True)
	serializer_class = ProviderServiceTypeSerializer
	permission_classes = []
	pagination_class = None


class ProviderMetaView(APIView):
	"""Return provider onboarding metadata: allowed countries + active service types + dial codes.

	Lightweight cached data for frontend to avoid hardcoding.
	"""
	permission_classes = []
	authentication_classes = []

	def get(self, request):
		service_types = list(ProviderServiceType.objects.filter(active=True).values("slug", "name"))
		countries = sorted(ALLOWED_PROVIDER_COUNTRIES)
		# Simple version heuristic: hash of sorted countries + service type slugs count
		import hashlib, json
		ver_basis = json.dumps({
			"countries": countries,
			"service_slugs": sorted([st["slug"] for st in service_types]),
		}, separators=(",", ":"))
		etag = hashlib.sha256(ver_basis.encode("utf-8")).hexdigest()[:16]
		if_none_match = request.headers.get("If-None-Match")
		if if_none_match == etag:
			from rest_framework.response import Response as DRFResponse
			resp = DRFResponse(status=304)
			resp["ETag"] = etag
			return resp
		payload = {
			"version": etag,
			"countries": countries,
			"dial_codes": {k: DIAL_CODE_MAP[k] for k in countries if k in DIAL_CODE_MAP},
			"service_types": service_types,
		}
		resp = Response(payload)
		resp["Cache-Control"] = "public, max-age=600"  # 10 minutes client cache
		resp["ETag"] = etag
		return resp


class CountriesListView(APIView):
	permission_classes = []
	authentication_classes = []

	# Minimal initial set; can expand or load from a fixture later
	COUNTRIES = [
		{"code": "ET", "name": "Ethiopia"},
		{"code": "KE", "name": "Kenya"},
		{"code": "US", "name": "United States"},
		{"code": "GB", "name": "United Kingdom"},
		{"code": "AE", "name": "United Arab Emirates"},
	]

	def get(self, request):
		return Response(self.COUNTRIES)


class UsernameAvailabilityView(APIView):
	permission_classes = []
	authentication_classes = []
	from core.throttling import UsernameAvailabilityThrottle
	throttle_classes = [UsernameAvailabilityThrottle]

	def get(self, request):
		username = request.query_params.get('username','').strip()
		if not username:
			return Response({"detail": "username query parameter required"}, status=400)
		# Basic character whitelist (letters, numbers, underscore, dash) length 3-32
		import re
		if not re.fullmatch(r'[A-Za-z0-9_-]{3,32}', username):
			return Response({"available": False, "reason": "invalid_format"})
		exists = User.objects.filter(username__iexact=username).exists()
		return Response({"available": not exists})


class UsernameReminderView(APIView):
	"""Accept an email and, if any users exist with that email, send a reminder listing their usernames.
	Always return 200 with generic response to avoid leaking whether the email exists.
	"""
	permission_classes = []
	authentication_classes = []
	from core.throttling import UsernameReminderThrottle
	throttle_classes = [UsernameReminderThrottle]

	def post(self, request: Request):
		email = str(request.data.get('email', '')).strip().lower()
		if not email or '@' not in email:
			return Response({"detail": "If the email exists, a reminder will be sent."}, status=200)
		usernames = list(User.objects.filter(email__iexact=email).values_list('username', flat=True))
		if usernames:
			subject = "Your account username(s)"
			body_lines = [
				"You (or someone) requested a reminder of usernames associated with this email.",
				"",
				"Usernames:",
				*[f" - {u}" for u in usernames],
				"",
				"If you did not request this, you can ignore the email.",
			]
			try:
				send_mail(
					subject=subject,
					message="\n".join(body_lines),
					from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@localhost'),
					recipient_list=[email],
					fail_silently=True,
				)
			except Exception:  # pragma: no cover
				pass
		return Response({"detail": "If the email exists, a reminder will be sent."}, status=200)


class EmailChangeRequestView(APIView):
	permission_classes = [permissions.IsAuthenticated]
	from core.throttling import EmailChangeThrottle
	throttle_classes = [EmailChangeThrottle]

	def post(self, request):
		new_email = str(request.data.get('new_email') or '').strip().lower()
		if not new_email:
			return Response({'new_email': ['This field is required']}, status=400)
		if User.objects.filter(email__iexact=new_email).exists():
			return Response({'new_email': ['Email already in use']}, status=400)
		# Invalidate prior pending requests for this user & email
		EmailChangeRequest.objects.filter(user=request.user, consumed_at__isnull=True, new_email=new_email).delete()
		# Generate token
		token_raw = secrets.token_urlsafe(32)
		token = hashlib.sha256(token_raw.encode()).hexdigest()[:64]
		token_minutes = getattr(settings, 'EMAIL_CHANGE_TOKEN_MINUTES', 60)
		expires_at = timezone.now() + timezone.timedelta(minutes=token_minutes)
		EmailChangeRequest.objects.create(user=request.user, new_email=new_email, token=token, expires_at=expires_at)
		# Email best-effort
		try:
			from django.core.mail import send_mail
			activation_url = f"{getattr(dj_settings,'PUBLIC_BASE_URL','http://localhost:5173')}/confirm-email-change/{token_raw}"
			# We send token_raw encoded; verify uses hash
			body = f"Use this link to confirm your email change: {activation_url}\nIf you did not request this, ignore the message."
			send_mail(
				"Confirm your email change",
				body,
				getattr(dj_settings,'DEFAULT_FROM_EMAIL','no-reply@localhost'),
				[new_email],
				fail_silently=True,
			)
		except Exception:
			pass
		return Response({'detail': 'Email change requested. Check new inbox to confirm.'}, status=201)


class EmailChangeConfirmView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		token_raw = str(request.data.get('token') or '').strip()
		if not token_raw:
			return Response({'token': ['Token required']}, status=400)
		token_hash = hashlib.sha256(token_raw.encode()).hexdigest()[:64]
		try:
			rec = EmailChangeRequest.objects.get(token=token_hash, user=request.user, consumed_at__isnull=True)
		except EmailChangeRequest.DoesNotExist:
			return Response({'detail': 'Invalid or expired token'}, status=400)
		if rec.is_expired():
			return Response({'detail': 'Token expired'}, status=400)
		# Apply email change
		user = request.user
		user.email = rec.new_email
		user.save(update_fields=['email'])
		# Reset verification status
		profile, _ = UserProfile.objects.get_or_create(user=user)
		profile.email_verified = False
		profile.save(update_fields=['email_verified'])
		rec.consumed_at = timezone.now()
		rec.save(update_fields=['consumed_at'])
		# Trigger new activation email for verification of new address
		from .auth_views import send_activation_email_if_needed
		send_activation_email_if_needed(user)
		return Response({'detail': 'Email updated. Please verify new address.'}, status=200)


class ActivationRedirectView(APIView):
	"""GET /activate/<uid>/<token> convenience endpoint for activation via browser click."""
	permission_classes = []
	authentication_classes = []

	def get(self, request, uid: str, token: str):  # type: ignore[override]
		# Manual activation logic (mirrors Djoser ActivationView behavior without import dependency)
		from django.contrib.auth.tokens import default_token_generator
		from django.utils.encoding import force_str
		from django.utils.http import urlsafe_base64_decode
		from django.contrib.auth.models import User
		
		try:
			uid_int = force_str(urlsafe_base64_decode(uid))
			user = User.objects.get(pk=uid_int)
		except Exception:
			return HttpResponse("<h1>Invalid Activation Link</h1><p>The link is malformed.</p>", status=400)

		if not default_token_generator.check_token(user, token):
			return HttpResponse("<h1>Invalid or Expired Activation Link</h1><p>Please request a new activation email.</p>", status=400)

		# Activate user if not already active
		changed = False
		if not user.is_active:
			user.is_active = True
			changed = True
		profile = getattr(user, 'profile', None)
		if profile and not profile.email_verified:
			profile.email_verified = True
			profile.save(update_fields=['email_verified'])
			changed = True
		if changed:
			# Persist activation status
			user.save(update_fields=['is_active'])
			# Log activation success
			import logging
			logging.getLogger('wedding_dream.auth').info('activation_success', extra={'event': 'activation_success', 'user_id': user.id, 'username': user.username})
		return HttpResponse("<h1>Account Activated</h1><p>You can now log in.</p>", status=200)


from .models import UserSession  # placed at end to avoid circular import issues earlier


class SessionListView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		sessions = UserSession.objects.filter(user=request.user).order_by('-last_seen')[:100]
		# Try to detect current session from JWT claim
		current_pid = None
		try:
			token = getattr(request, 'auth', None)
			if token is not None:
				# SimpleJWT token acts like a dict
				current_pid = token.get('session_pid', None)
		except Exception:
			current_pid = None
		out = []
		for s in sessions:
			out.append({
				'public_id': s.public_id,
				'label': s.label or 'Device',
				'created_at': s.created_at,
				'last_seen': s.last_seen,
				'revoked': bool(s.revoked_at),
				'is_current': (s.public_id == current_pid) if current_pid else False,
			})
		return Response({'results': out})


class SessionRevokeView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		pid = request.data.get('public_id')
		if not pid:
			# backward compatibility: accept integer id
			legacy_id = request.data.get('id')
			if not legacy_id:
				return Response({'detail': 'public_id required'}, status=400)
			try:
				s = UserSession.objects.get(id=legacy_id, user=request.user)
			except UserSession.DoesNotExist:
				return Response({'detail': 'Not found'}, status=404)
		else:
			try:
				s = UserSession.objects.get(public_id=pid, user=request.user)
			except UserSession.DoesNotExist:
				return Response({'detail': 'Not found'}, status=404)
		if s.revoked_at:
			return Response({'detail': 'Already revoked'})
		s.mark_revoked()
		return Response({'detail': 'Revoked'})


class SessionRevokeAllOtherView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		# Determine current session from token claim if present; allow override via keep_public_id
		keep_public_id = request.data.get('keep_public_id')
		if not keep_public_id:
			try:
				token = getattr(request, 'auth', None)
				if token is not None:
					keep_public_id = token.get('session_pid', None)
			except Exception:
				keep_public_id = None
		qs = UserSession.objects.filter(user=request.user, revoked_at__isnull=True)
		if keep_public_id:
			qs = qs.exclude(public_id=keep_public_id)
		count = 0
		for s in qs.iterator():
			s.mark_revoked()
			count += 1
		return Response({'detail': f'Revoked {count} sessions'})


