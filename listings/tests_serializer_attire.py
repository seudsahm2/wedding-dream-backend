from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from listings.models import Category, Listing
from listings.serializers import ListingSerializer

User = get_user_model()

class ListingSerializerAttireTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='prov', password='pass')
        self.category_attire, _ = Category.objects.get_or_create(name='Attire & Apparel', slug='attire')

    def test_happy_path_attire_with_roles_and_accessory(self):
        data = {
            'title': 'Attire Test',
            'category': 'attire',
            'image': 'http://example.com/img.jpg',
            'location': 'City',
            'price_min': 100,
            'attire_attrs': {
                'roles': ['Women:Bride','Men:Groom'],
                'accessoryType': 'Jewelry & Veils'
            }
        }
        factory = APIRequestFactory()
        request = factory.post('/')
        # Attach a user attribute for serializer.create usage
        setattr(request, 'user', self.user)
        serializer = ListingSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        inst = serializer.save(created_by=self.user)
        self.assertEqual(inst.category.slug, 'attire')
        self.assertEqual(inst.attire_attrs.get('accessoryType'), 'Jewelry & Veils')

    def test_invalid_roles_type(self):
        data = {
            'title': 'Bad Roles',
            'category': 'attire',
            'image': 'x',
            'location': 'Y',
            'attire_attrs': {
                'roles': 'Women:Bride',  # should be list
            }
        }
        serializer = ListingSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('attire_attrs', serializer.errors)

    def test_invalid_accessory_type_type(self):
        data = {
            'title': 'Bad Accessory',
            'category': 'attire',
            'image': 'x',
            'location': 'Y',
            'attire_attrs': {
                'accessoryType': ['not','string'],
            }
        }
        serializer = ListingSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('attire_attrs', serializer.errors)

    def test_attire_bridal_extra_keys_rejected(self):
        cat, _ = Category.objects.get_or_create(name='Bridal Attire', slug='attire-bridal')
        data = {
            'title': 'Bridal',
            'category': 'attire-bridal',
            'image': 'x',
            'location': 'Y',
            'attire_attrs': {
                'sizeRange': '2-16',
                'fabricTypes': ['Silk'],
                'unexpected': 'nope',
            }
        }
        serializer = ListingSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('attire_attrs', serializer.errors)
