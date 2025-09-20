from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.urls import reverse
from listings.models import Category, Listing
from users.models import UserProfile


User = get_user_model()


class ListingOwnershipTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.provider_user = User.objects.create_user(username='prov', password='pass123')
		UserProfile.objects.create(user=self.provider_user, role=UserProfile.ROLE_PROVIDER)
		self.normal_user = User.objects.create_user(username='norm', password='pass123')
		UserProfile.objects.create(user=self.normal_user, role=UserProfile.ROLE_NORMAL)
		self.category = Category.objects.create(name='Venues', slug='venue')

	def auth(self, user):
		self.client.force_authenticate(user=user)

	def test_provider_creates_draft_listing(self):
		self.auth(self.provider_user)
		resp = self.client.post(reverse('listing-list'), {
			'title': 'Test Venue',
			'category': 'venue',
			'image': 'http://example.com/x.jpg',
			'location': 'City',
			'price_min': '1000.00',
		}, format='json')
		self.assertEqual(resp.status_code, 201, resp.content)
		data = resp.json()
		self.assertEqual(data['status'], 'draft')
		self.assertIsNone(data['published_at'])
		self.assertIsNotNone(data['created_by'])

	def test_draft_not_visible_public(self):
		listing = Listing.objects.create(title='Hidden', category=self.category, image='x', location='Y', price_min=0, created_by=self.provider_user)
		resp = self.client.get(reverse('listing-list'))
		self.assertEqual(resp.status_code, 200)
		# Should be empty because draft
		self.assertEqual(len(resp.json().get('results', []) or resp.json() if isinstance(resp.json(), list) else []), 0)

	def test_owner_can_view_draft_detail(self):
		listing = Listing.objects.create(title='Hidden', category=self.category, image='x', location='Y', price_min=0, created_by=self.provider_user)
		self.auth(self.provider_user)
		resp = self.client.get(reverse('listing-detail', args=[listing.id]))
		self.assertEqual(resp.status_code, 200)

	def test_non_owner_cannot_view_draft_detail(self):
		listing = Listing.objects.create(title='Hidden', category=self.category, image='x', location='Y', price_min=0, created_by=self.provider_user)
		self.auth(self.normal_user)
		resp = self.client.get(reverse('listing-detail', args=[listing.id]))
		self.assertEqual(resp.status_code, 404)

	def test_publish_flow(self):
		self.auth(self.provider_user)
		resp = self.client.post(reverse('listing-list'), {
			'title': 'To Publish',
			'category': 'venue',
			'image': 'http://example.com/x.jpg',
			'location': 'City',
			'price_min': '500.00',
		}, format='json')
		listing_id = resp.json()['id']
		publish_url = reverse('listing-publish', args=[listing_id])
		pub_resp = self.client.patch(publish_url, {})
		self.assertEqual(pub_resp.status_code, 200, pub_resp.content)
		self.assertEqual(pub_resp.json()['status'], 'published')
		# Now visible publicly
		self.client.force_authenticate(user=None)
		list_resp = self.client.get(reverse('listing-list'))
		results = list_resp.json().get('results', []) if isinstance(list_resp.json(), dict) else list_resp.json()
		self.assertTrue(any(r['id'] == listing_id for r in results))
