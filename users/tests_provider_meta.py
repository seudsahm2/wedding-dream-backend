from django.test import TestCase
from django.urls import reverse
from users.constants import ALLOWED_PROVIDER_COUNTRIES, DIAL_CODE_MAP
from users.models import ProviderServiceType

class ProviderMetaEndpointTests(TestCase):
    def setUp(self):
        ProviderServiceType.objects.create(slug='photo', name='Photography')
        ProviderServiceType.objects.create(slug='venue', name='Venue')
        self.url = reverse('provider-meta')

    def test_provider_meta_structure(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('countries', data)
        self.assertIn('service_types', data)
        self.assertIn('dial_codes', data)
        self.assertIsInstance(data['countries'], list)
        self.assertTrue(set(data['countries']).issubset(ALLOWED_PROVIDER_COUNTRIES))
        # Dial codes subset check
        for k, v in data['dial_codes'].items():
            self.assertEqual(DIAL_CODE_MAP.get(k), v)
        # At least one service type present
        self.assertGreaterEqual(len(data['service_types']), 2)

class DialCodeSyncTests(TestCase):
    def test_allowed_countries_subset_of_dial_codes_keys(self):
        # If a supported country lacks a dial code, frontend auto-prefix might fail.
        missing = [c for c in ALLOWED_PROVIDER_COUNTRIES if c not in DIAL_CODE_MAP]
        self.assertEqual(missing, [], f"Missing dial codes for: {missing}")
