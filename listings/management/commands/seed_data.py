import os
import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from listings.models import Category, Listing
from reviews.models import Review
from decimal import Decimal

# Adjust this path to the absolute path of your frontend's mockData.ts file
# This is a simplified representation. In a real scenario, you might have a shared JSON file.
MOCK_DATA_PATH = os.path.join(os.path.dirname(__file__), '../../../../habesha-wedding-dream/src/lib/mockData.ts')

class Command(BaseCommand):
    help = 'Seeds the database with mock data from the frontend'

    def handle(self, *args, **options):
        self.stdout.write('Starting database seeding...')
        self.clear_data()
        self.seed_data()
        self.stdout.write(self.style.SUCCESS('Database seeding complete!'))

    def clear_data(self):
        self.stdout.write('Clearing existing data...')
        Review.objects.all().delete()
        Listing.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def seed_data(self):
        self.stdout.write('Seeding new data...')

        # Create a dummy user for reviews and other relations
        user, _ = User.objects.get_or_create(username='testuser', defaults={'password': 'password', 'email': 'test@example.com'})

        # --- Categories ---
        categories_data = [
            {"name": "Venues", "slug": "VENUE"},
            {"name": "Attire", "slug": "ATTIRE"},
            {"name": "Catering", "slug": "CATERING"},
            {"name": "Rentals", "slug": "RENTAL"},
            {"name": "Services", "slug": "SERVICE"},
            {"name": "Accessories", "slug": "ACCESSORY"},
        ]
        categories = {}
        for cat_data in categories_data:
            category, _ = Category.objects.get_or_create(slug=cat_data['slug'], defaults={'name': cat_data['name']})
            categories[cat_data['slug']] = category
            self.stdout.write(f"  Created category: {category.name}")

        # --- Listings & Reviews ---
        # This is a simplified parser for the TypeScript mock data file.
        # It's brittle and depends on the exact format of the file.
        try:
            with open(MOCK_DATA_PATH, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract listings array
            listings_str = self._extract_json_string(content, 'export const listings: Listing[] = ')
            listings_data = self._parse_ts_object(listings_str)

            # Extract reviews object
            reviews_str = self._extract_json_string(content, 'export const reviewsByListing: Record<string, Review[]> = ')
            reviews_data = self._parse_ts_object(reviews_str)

            for item in listings_data:
                listing = Listing.objects.create(
                    title=item.get('title'),
                    category=categories[item.get('category')],
                    type_label=item.get('typeLabel', ''),
                    image=self._get_image_url(item.get('image')),
                    rating=Decimal(str(item.get('rating', 0.0))),
                    review_count=item.get('reviewCount', 0),
                    location=item.get('location', ''),
                    capacity=item.get('capacity', ''),
                    price_range=item.get('priceRange', ''),
                    features=item.get('features', []),
                    badges=item.get('badges', []),
                    featured=item.get('featured', False),
                    venue_attrs=item.get('venueAttrs'),
                    attire_attrs=item.get('attireAttrs'),
                    catering_attrs=item.get('cateringAttrs'),
                    rental_attrs=item.get('rentalAttrs'),
                    specialty_attrs=item.get('specialtyAttrs'),
                    accessory_attrs=item.get('accessoryAttrs'),
                )
                self.stdout.write(f"    Created listing: {listing.title}")

                # Seed reviews for this listing
                listing_reviews = reviews_data.get(str(item.get('id')))
                if listing_reviews:
                    for review_data in listing_reviews:
                        Review.objects.create(
                            listing=listing,
                            user=user,
                            user_name=review_data.get('userName'),
                            rating=review_data.get('rating'),
                            text=review_data.get('text'),
                        )
                        self.stdout.write(f"      - Added review by {review_data.get('userName')}")

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Mock data file not found at {MOCK_DATA_PATH}"))
            self.stdout.write(self.style.WARNING("Please ensure the frontend and backend projects are in the same parent directory."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse mock data: {e}"))

    def _get_image_url(self, image_path_str):
        # Converts relative frontend asset paths to a placeholder or a local server path.
        # For now, we'll just use the raw string, assuming it's a placeholder URL.
        # In a real setup, you'd copy these to a media folder.
        if image_path_str and 'import(' not in image_path_str:
             # A simple way to handle the dynamic import syntax in the mock file
            base_name = os.path.basename(image_path_str.split("'")[1])
            # This creates a placeholder URL. You should serve these files from your Django media root.
            return f"/static/images/{base_name}"
        return "/static/images/placeholder.svg"


    def _extract_json_string(self, content, start_marker):
        try:
            start_index = content.index(start_marker) + len(start_marker)
            # Find the closing semicolon of the export statement
            end_index = content.index(';', start_index)
            return content[start_index:end_index].strip()
        except ValueError:
            return "[]"

    def _parse_ts_object(self, ts_string):
        # WARNING: This is a very naive and brittle parser.
        # It replaces TS-specific syntax with JSON-compatible syntax.
        # It will break on complex TS objects.
        json_string = ts_string
        # Remove trailing commas from objects and arrays
        json_string = json_string.replace(r',]', ']')
        json_string = json_string.replace(r',}', '}')
        # Replace single quotes with double quotes
        json_string = json_string.replace("'", '"')
        # Replace property names without quotes with quoted names
        json_string = json_string.replace('id:', '"id":')
        json_string = json_string.replace('title:', '"title":')
        json_string = json_string.replace('category:', '"category":')
        json_string = json_string.replace('typeLabel:', '"typeLabel":')
        json_string = json_string.replace('image:', '"image":')
        json_string = json_string.replace('rating:', '"rating":')
        json_string = json_string.replace('reviewCount:', '"reviewCount":')
        json_string = json_string.replace('location:', '"location":')
        json_string = json_string.replace('capacity:', '"capacity":')
        json_string = json_string.replace('priceRange:', '"priceRange":')
        json_string = json_string.replace('features:', '"features":')
        json_string = json_string.replace('badges:', '"badges":')
        json_string = json_string.replace('featured:', '"featured":')
        json_string = json_string.replace('venueAttrs:', '"venueAttrs":')
        json_string = json_string.replace('attireAttrs:', '"attireAttrs":')
        json_string = json_string.replace('cateringAttrs:', '"cateringAttrs":')
        json_string = json_string.replace('rentalAttrs:', '"rentalAttrs":')
        json_string = json_string.replace('specialtyAttrs:', '"specialtyAttrs":')
        json_string = json_string.replace('accessoryAttrs:', '"accessoryAttrs":')
        json_string = json_string.replace('userName:', '"userName":')
        json_string = json_string.replace('text:', '"text":')
        json_string = json_string.replace('createdAt:', '"createdAt":')
        
        # Handle dynamic imports like `image: import('../assets/luxury-wedding-hall.jpg')`
        # This is a regex to find and replace the import statements
        import re
        json_string = re.sub(r'import\(([^)]+)\)', r'"\1"', json_string)

        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"JSON decoding failed: {e}"))
            self.stdout.write(f"Problematic string: {json_string[:500]}...")
            return []
