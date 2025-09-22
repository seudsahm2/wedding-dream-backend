from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import ProviderServiceType
import json


class UsernameAvailabilityTests(TestCase):
	def setUp(self):
		self.url = reverse('username-available')
		User.objects.create_user(username='ExistingUser', password='test12345')

	def test_invalid_format_too_short(self):
		resp = self.client.get(self.url, {'username': 'ab'})
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertFalse(data['available'])
		self.assertIn('reason', data)

	def test_invalid_format_chars(self):
		resp = self.client.get(self.url, {'username': 'bad!*'})
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertFalse(data['available'])

	def test_available_username(self):
		resp = self.client.get(self.url, {'username': 'fresh_name'})
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertTrue(data['available'])

	def test_taken_case_insensitive(self):
		resp = self.client.get(self.url, {'username': 'existinguser'})
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertFalse(data['available'])

	def test_throttle_limit_exceeded(self):
		# Assuming rate 30/minute; we attempt a bit over the limit
		for i in range(35):
			resp = self.client.get(self.url, {'username': f'unique_name_{i}'})
			if resp.status_code == 429:
				break
		self.assertEqual(resp.status_code, 429, "Expected a 429 after exceeding throttle rate")



class ProviderRegistrationPhoneTests(TestCase):
	"""Tests for phone number validation & activation enforcement in unified RegisterProviderView."""

	def setUp(self):
		# Unified provider registration endpoint (previously register-provider-v2)
		self.url = reverse('register-provider')
		# Minimal provider service type required for validation to pass
		ProviderServiceType.objects.create(slug='photography', name='Photography')

	def _base_payload(self):
		return {
			"username": "phoneuser",
			"password": "StrongPass123",
			"email": "phoneuser@example.com",
			"business_name": "My Biz",
			"business_phone": "+251911223344",  # will override per test
			"country": "ET",
			"city": "Addis Ababa",
			"business_type": "photography",
		}

	def test_phone_country_mismatch_rejected(self):
		payload = self._base_payload()
		# Supply a US number while declaring country ET
		payload["business_phone"] = "+14155552671"  # US number
		resp = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
		self.assertEqual(resp.status_code, 400)
		data = resp.json()
		self.assertIn('business_phone', data)
		self.assertIn('Phone country code mismatch', data['business_phone'][0])

	def test_valid_phone_allows_registration(self):
		payload = self._base_payload()
		resp = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
		self.assertEqual(resp.status_code, 201)
		data = resp.json()
		self.assertEqual(data.get('role'), 'provider')
		self.assertTrue(data.get('is_provider'))
		# Stored phone should be normalized to E.164 (already is) and echo country
		self.assertEqual(data.get('country'), 'ET')

	def test_registration_does_not_return_tokens_and_user_inactive(self):
		payload = self._base_payload()
		payload['username'] = 'activationcheck'
		payload['email'] = 'activationcheck@example.com'
		resp = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
		self.assertEqual(resp.status_code, 201)
		data = resp.json()
		# Ensure tokens are NOT present
		self.assertNotIn('access', data)
		self.assertNotIn('refresh', data)
		self.assertTrue(data.get('activation_required'))
		# Confirm user actually created inactive
		u = User.objects.get(username='activationcheck')
		self.assertFalse(u.is_active)

