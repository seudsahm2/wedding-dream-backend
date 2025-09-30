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
		# Ensure categories needed by tests exist
		Category.objects.get_or_create(slug='attire', defaults={'name': 'Attire'})
		Category.objects.get_or_create(slug='accessories', defaults={'name': 'Accessories'})

	def auth(self, user):
		# Obtain a real JWT using Djoser and attach Authorization header
		resp = self.client.post('/api/v1/auth/login', {
			'username': user.username,
			'password': 'pass123',
		}, format='json')
		self.assertEqual(resp.status_code, 200, resp.content)
		token = resp.json().get('access')
		self.assertTrue(token)
		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
		# JWT header is sufficient for authentication in tests
		return

	def test_provider_creates_draft_listing(self):
		self.auth(self.provider_user)
		# Sanity: ensure API recognizes this user as provider
		me = self.client.get('/api/v1/me')
		self.assertEqual(me.status_code, 200, me.content)
		self.assertTrue(me.json().get('is_provider'))
		resp = self.client.post(reverse('listing-list'), {
			'title': 'Test Attire',
			'category': 'attire',
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
		cat,_ = Category.objects.get_or_create(slug='attire', defaults={'name':'Attire'})
		listing = Listing.objects.create(title='Hidden', category=cat, image='x', location='Y', price_min=0, created_by=self.provider_user)
		resp = self.client.get(reverse('listing-list'))
		self.assertEqual(resp.status_code, 200)
		# Should be empty because draft
		self.assertEqual(len(resp.json().get('results', []) or resp.json() if isinstance(resp.json(), list) else []), 0)

	def test_owner_can_view_draft_detail(self):
		cat,_ = Category.objects.get_or_create(slug='attire', defaults={'name':'Attire'})
		listing = Listing.objects.create(title='Hidden', category=cat, image='x', location='Y', price_min=0, created_by=self.provider_user)
		self.auth(self.provider_user)
		resp = self.client.get(reverse('listing-detail', args=[listing.id]))
		self.assertEqual(resp.status_code, 200)

	def test_non_owner_cannot_view_draft_detail(self):
		cat,_ = Category.objects.get_or_create(slug='attire', defaults={'name':'Attire'})
		listing = Listing.objects.create(title='Hidden', category=cat, image='x', location='Y', price_min=0, created_by=self.provider_user)
		self.auth(self.normal_user)
		resp = self.client.get(reverse('listing-detail', args=[listing.id]))
		self.assertEqual(resp.status_code, 404)

	def test_publish_flow(self):
		self.auth(self.provider_user)
		resp = self.client.post(reverse('listing-list'), {
			'title': 'To Publish',
			'category': 'attire',
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
		self.client.credentials()  # clear auth
		list_resp = self.client.get(reverse('listing-list'))
		results = list_resp.json().get('results', []) if isinstance(list_resp.json(), dict) else list_resp.json()
		self.assertTrue(any(r['id'] == listing_id for r in results))

	def test_create_accessory_listing(self):
		"""Ensure accessories slug with accessory_attrs is accepted and stored."""
		self.auth(self.provider_user)
		resp = self.client.post(reverse('listing-list'), {
			'title': 'Gold Necklace',
			'category': 'accessories',
			'image': 'uploads/img1.jpg',
			'location': 'Addis',
			'price_min': '250.00',
			'accessory_attrs': {
				'accessoryType': 'Jewelry & Veils',
				'material': 'Gold',
				'karat': '18k',
				'images': ['uploads/img1.jpg']
			}
		}, format='json')
		self.assertEqual(resp.status_code, 201, resp.content)
		data = resp.json()
		self.assertEqual(data['category'], 'accessories')
		self.assertIn('accessory_attrs', data)
		self.assertEqual(data['accessory_attrs']['accessoryType'], 'Jewelry & Veils')
		# Publish
		listing_id = data['id']
		pub_resp = self.client.patch(reverse('listing-publish', args=[listing_id]), {})
		self.assertEqual(pub_resp.status_code, 200)
		self.assertEqual(pub_resp.json()['status'], 'published')

	def test_accessory_requires_type(self):
		self.auth(self.provider_user)
		resp = self.client.post(reverse('listing-list'), {
			'title': 'Invalid Accessory',
			'category': 'accessories',
			'image': 'uploads/x.jpg',
			'location': 'Addis',
			'price_min': '100.00',
			'accessory_attrs': {
				# missing accessoryType on purpose
				'material': 'Gold'
			}
		}, format='json')
		self.assertEqual(resp.status_code, 400, resp.content)


class ListingAvailabilityTests(TestCase):
	def setUp(self):
		from users.models import UserProfile
		self.client = APIClient()
		self.provider = User.objects.create_user(username='prov2', password='pass123')
		prof, _ = UserProfile.objects.get_or_create(user=self.provider)
		prof.role = UserProfile.ROLE_PROVIDER
		prof.save(update_fields=['role'])
		self.category = Category.objects.create(name='Venue Hall', slug='venue-hall')
		self.listing = Listing.objects.create(title='Hall A', category=self.category, image='x', location='City', price_min=1000, created_by=self.provider, status='published')

	def auth(self, user):
		resp = self.client.post('/api/v1/auth/login', {
			'username': user.username,
			'password': 'pass123',
		}, format='json')
		self.assertEqual(resp.status_code, 200, resp.content)
		access = resp.json().get('access')
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

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
