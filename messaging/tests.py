from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from listings.models import Listing
from .models import MessageThread, Message


class MessagingApiTests(APITestCase):
	def setUp(self):
		self.user1 = User.objects.create_user(username="u1", password="pass1234")
		self.user2 = User.objects.create_user(username="u2", password="pass1234")
		self.listing = Listing.objects.create(
			title="Test Venue",
			category="VENUE",
			type_label="Venue",
			image="assets/hero-wedding-hall.jpg",
			rating=4.5,
			review_count=10,
			location="AA",
			price_range="$",
			features=[],
		)
		self.thread = MessageThread.objects.create(listing=self.listing)
		self.thread.participants.add(self.user1, self.user2)
		Message.objects.create(thread=self.thread, sender=self.user1, text="Hi")
		Message.objects.create(thread=self.thread, sender=self.user2, text="Hello")

	def auth(self, user: User) -> APIClient:
		c = APIClient()
		c.force_authenticate(user=user)
		return c

	def test_list_threads(self):
		url = "/api/v1/threads/"
		resp = self.auth(self.user1).get(url)
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertTrue(isinstance(resp.data, list))
		self.assertEqual(len(resp.data), 1)
		self.assertEqual(resp.data[0]["id"], self.thread.id)

	def test_get_thread_detail(self):
		url = f"/api/v1/threads/{self.thread.id}/"
		resp = self.auth(self.user1).get(url)
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertIn("messages", resp.data)
		self.assertEqual(len(resp.data["messages"]), 2)

	def test_post_message(self):
		url = f"/api/v1/threads/{self.thread.id}/messages/"
		resp = self.auth(self.user1).post(url, {"text": "How are you?"}, format="json")
		self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
		self.assertEqual(resp.data["text"], "How are you?")

	def test_forbid_non_participant(self):
		outsider = User.objects.create_user(username="outsider", password="pass1234")
		url = f"/api/v1/threads/{self.thread.id}/"
		resp = self.auth(outsider).get(url)
		self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
