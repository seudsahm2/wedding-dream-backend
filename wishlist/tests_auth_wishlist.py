from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from listings.models import Listing, Category


class AuthWishlistTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(slug="VENUE", name="Venues")
        self.listing = Listing.objects.create(
            title="Test Venue",
            category=self.category,
            type_label="Venue",
            image="assets/hero-wedding-hall.jpg",
            location="Addis Ababa",
            price_range="$$$",
            features=[],
        )

    def auth_user(self, username="alice", password="pass12345"):
        User.objects.create_user(username=username, password=password)
        # Djoser/SimpleJWT login
        res = self.client.post("/api/v1/auth/login", {"username": username, "password": password}, format="json")
        self.assertEqual(res.status_code, 200)
        token = res.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_register_login_and_wishlist_crud(self):
        # Register
        res = self.client.post("/api/v1/auth/register", {"username": "bob", "password": "pass12345"}, format="json")
        self.assertIn(res.status_code, (200, 201))
        # If activation is required by config, mark user active for test continuity
        try:
            u = User.objects.get(username="bob")
            if not u.is_active:
                u.is_active = True
                u.save(update_fields=["is_active"])
        except Exception:
            pass

        # Login
        res = self.client.post("/api/v1/auth/login", {"username": "bob", "password": "pass12345"}, format="json")
        self.assertEqual(res.status_code, 200)
        access = res.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        # Wishlist list empty
        res = self.client.get("/api/v1/wishlist")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

        # Add to wishlist
        res = self.client.post("/api/v1/wishlist", {"listing_id": self.listing.id}, format="json")
        self.assertEqual(res.status_code, 201)
        item = res.json()
        self.assertEqual(item["listing_id"], self.listing.id)

        # List has one
        res = self.client.get("/api/v1/wishlist")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

        # Delete
        res = self.client.delete(f"/api/v1/wishlist/{self.listing.id}")
        self.assertIn(res.status_code, (200, 204))

    def test_wishlist_requires_auth(self):
        res = self.client.get("/api/v1/wishlist")
        self.assertEqual(res.status_code, 401)
        res = self.client.post("/api/v1/wishlist", {"listing_id": self.listing.id}, format="json")
        self.assertEqual(res.status_code, 401)
