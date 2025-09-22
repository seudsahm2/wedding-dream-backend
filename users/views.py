from rest_framework import permissions, generics, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import UserProfile, ProviderServiceType
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
		payload = request.data.copy()
		# Enforced activation irrespective of DJOSER config
		require_activation = True
		# Phone validation (basic) extracted to helper
		def validate_phone(raw: str, country_code: str):
			import phonenumbers
			phone_raw = raw.strip()
			try:
				# Parse with region; if user omitted '+' this will still work
				parsed = phonenumbers.parse(phone_raw, country_code)
				if not phonenumbers.is_valid_number(parsed):
					return False, "Invalid phone number"
				# Ensure region matches provided ISO country (allow special cases where library maps)
				region = phonenumbers.region_code_for_number(parsed)
				if region and region.upper() != country_code.upper():
					return False, "Phone country code mismatch"
				e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
				return True, e164
			except phonenumbers.NumberParseException:
				return False, "Could not parse phone number"
		
		missing = [f for f in self.REQUIRED_FIELDS if not str(payload.get(f, '')).strip()]
		if missing:
			return Response({"detail": "Missing required fields", "missing": missing}, status=400)
		# Country whitelist + format check
		country = payload.get('country','').upper()
		if len(country) != 2:
			return Response({"country": ["Must be 2-letter ISO code"]}, status=400)
		if country not in ALLOWED_PROVIDER_COUNTRIES:
			return Response({"country": ["Country not supported yet"]}, status=400)
		city = payload.get('city', '').strip()
		if not city:
			return Response({"city": ["City is required"]}, status=400)
		payload['country'] = country
		# Validate provider service type existence if table migrated
		btype = payload.get('business_type')
		try:
			if not ProviderServiceType.objects.filter(slug=btype, active=True).exists():
				return Response({"business_type": ["Invalid provider type"]}, status=400)
		except Exception:
			pass
		# Validate phone
		ok, norm_phone_or_msg = validate_phone(payload['business_phone'], country)
		if not ok:
			return Response({"business_phone": [norm_phone_or_msg]}, status=400)
		payload['business_phone'] = norm_phone_or_msg
		# Create user via Django directly (avoids complexity of djoser remapping). Minimal fields only.
		username = payload['username']
		if User.objects.filter(username=username).exists():
			return Response({"username": ["Username already exists"]}, status=400)
		email = payload.get('email') or ''
		if not email:
			return Response({"email": ["Email is required for provider activation"]}, status=400)
		user = User.objects.create_user(username=username, password=payload['password'], email=email)
		# Force inactive until activation link consumed
		user.is_active = False
		user.save(update_fields=["is_active"])
		profile, _ = UserProfile.objects.get_or_create(user=user)
		profile.role = UserProfile.ROLE_PROVIDER
		profile.business_name = payload['business_name']
		profile.business_phone = payload['business_phone']
		profile.business_type = btype
		profile.country = country
		profile.city = city
		profile.save()
		data = UserSerializer(user).data
		data["role"] = profile.role
		data["is_provider"] = True
		data["country"] = profile.country
		data["business_phone"] = profile.business_phone
		# Always send activation email (best effort) without failing the request if email send crashes
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
		data["activation_required"] = True
		return Response(data, status=201)


class ProviderUpgradeView(generics.GenericAPIView):
	"""Upgrade existing authenticated user to provider (strict unified version)."""
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		profile, _ = UserProfile.objects.get_or_create(user=request.user)
		# Required fields for upgrade
		required = ["business_name", "business_phone", "business_type", "country", "city"]
		missing = [f for f in required if not str(request.data.get(f, '')).strip()]
		if missing:
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
		# Validate phone using same logic as registration
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
		return HttpResponse("<h1>Account Activated</h1><p>You can now log in.</p>", status=200)


