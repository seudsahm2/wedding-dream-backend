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
		prof, _ = UserProfile.objects.get_or_create(user=self.provider_user)
		prof.role = UserProfile.ROLE_PROVIDER
		prof.save(update_fields=['role'])
		self.normal_user = User.objects.create_user(username='norm', password='pass123')
		prof2, _ = UserProfile.objects.get_or_create(user=self.normal_user)
		prof2.role = UserProfile.ROLE_NORMAL
		prof2.save(update_fields=['role'])
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


class ListingAvailabilityTests(TestCase):
	def setUp(self):
		from users.models import UserProfile
		self.client = APIClient()
		self.provider = User.objects.create_user(username='prov2', password='pass123')
		UserProfile.objects.create(user=self.provider, role=UserProfile.ROLE_PROVIDER)
		self.category = Category.objects.create(name='Venue Hall', slug='venue-hall')
		self.listing = Listing.objects.create(title='Hall A', category=self.category, image='x', location='City', price_min=1000, created_by=self.provider, status='published')

	def auth(self, user):
		self.client.force_authenticate(user=user)

	def test_create_booking_and_month_view(self):
		self.auth(self.provider)
		url = reverse('listing-availability-create', args=[self.listing.id])
		resp = self.client.post(url, {
			'start_date': '2025-10-10',
			'end_date': '2025-10-12',
			'status': 'confirmed'
		}, format='json')
		self.assertEqual(resp.status_code, 201, resp.content)
		# Month view
		mv = self.client.get(reverse('listing-availability-month', args=[self.listing.id]), {'month': '2025-10'})
		self.assertEqual(mv.status_code, 200)
		booked = mv.json()['booked']
		self.assertIn('2025-10-10', booked)
		self.assertIn('2025-10-12', booked)

	def test_overlap_booking_rejected(self):
		self.auth(self.provider)
		create_url = reverse('listing-availability-create', args=[self.listing.id])
		r1 = self.client.post(create_url, {'start_date': '2025-11-01', 'end_date': '2025-11-05', 'status': 'confirmed'}, format='json')
		self.assertEqual(r1.status_code, 201)
		r2 = self.client.post(create_url, {'start_date': '2025-11-05', 'end_date': '2025-11-07', 'status': 'confirmed'}, format='json')
		# Overlaps on boundary day 5 (inclusive), should reject
		self.assertEqual(r2.status_code, 400, r2.content)

	def test_public_month_requires_published(self):
		# Set listing to draft and ensure month view returns 404
		self.listing.status = 'draft'
		self.listing.save(update_fields=['status'])
		mv = self.client.get(reverse('listing-availability-month', args=[self.listing.id]), {'month': '2025-10'})
		self.assertEqual(mv.status_code, 404)
