from django.test import TestCase
from users.constants import ALLOWED_PROVIDER_COUNTRIES

class AllowedCountriesConsistencyTests(TestCase):
    def test_expected_countries_present(self):
        # Core markets we rely on in tests & frontend dial code map
        for code in ["ET", "US", "AE"]:
            self.assertIn(code, ALLOWED_PROVIDER_COUNTRIES)

    def test_non_empty_and_uppercase(self):
        self.assertTrue(ALLOWED_PROVIDER_COUNTRIES)
        for c in ALLOWED_PROVIDER_COUNTRIES:
            self.assertEqual(c, c.upper())
            self.assertEqual(len(c), 2)
