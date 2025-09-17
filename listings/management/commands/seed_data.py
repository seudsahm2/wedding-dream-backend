import os
from django.core.management.base import BaseCommand
from listings.models import Category, Listing
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seeds the database with static listing data.'

    def handle(self, *args, **options):
        self.stdout.write("Starting database seeding...")

        # 1. Clean slate
        Listing.objects.all().delete()
        Category.objects.all().delete()
        self.stdout.write("Cleared existing listings and categories.")

        # 2. Define and create categories
        categories_data = [
            {"slug": "VENUE", "name": "Venues"},
            {"slug": "ATTIRE", "name": "Attire"},
            {"slug": "CATERING", "name": "Catering"},
            {"slug": "RENTAL", "name": "Rentals"},
            {"slug": "SERVICE", "name": "Services"},
            {"slug": "ACCESSORY", "name": "Accessories"},
        ]
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=cat_data["slug"],
                defaults={'name': cat_data["name"]}
            )
            categories[category.slug] = category
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))

        # 3. Define static listing data
        listings_data = [
            # Venues
            {
                "title": "Millennium Hall",
                "category_slug": "VENUE",
                "type_label": "Grand Event Venue",
                "image": "assets/hero-wedding-hall.jpg",
                "rating": 4.9, "review_count": 210,
                "location": "Addis Ababa, Ethiopia",
                "capacity": "500-2000 guests",
                "price_range": "$30,000 – $90,000",
                "price_min_decimal": 30000,
                "featured": True,
                "features": ["Grand Ballroom", "On-site Catering", "Valet Parking", "Backup Power"],
                "badges": ["Top Rated", "Featured"],
                "venue_attrs": {"parking": True, "backupPower": True, "kitchen": True},
                "attire_attrs": {}, "catering_attrs": {}, "rental_attrs": {}, "service_attrs": {},
            },
            {
                "title": "Sheraton Addis Luxury Hotel",
                "category_slug": "VENUE",
                "type_label": "5-Star Hotel Venue",
                "image": "assets/luxury-wedding-hall.jpg",
                "rating": 4.8, "review_count": 180,
                "location": "Addis Ababa, Ethiopia",
                "capacity": "200-800 guests",
                "price_range": "$20,000 – $60,000",
                "price_min_decimal": 20000,
                "featured": True,
                "features": ["Multiple Ballrooms", "World-class Service", "Bridal Suite"],
                "badges": ["Luxury"],
                "venue_attrs": {"parking": True, "backupPower": True, "kitchen": True},
                "attire_attrs": {}, "catering_attrs": {}, "rental_attrs": {}, "service_attrs": {},
            },
            # Attire
            {
                "title": "Habesha Kemis by Fikir",
                "category_slug": "ATTIRE",
                "type_label": "Designer Traditional Attire",
                "image": "assets/habesha-kemis.jpg",
                "rating": 4.9, "review_count": 120,
                "location": "Bole, Addis Ababa",
                "price_range": "$1,500 – $5,000",
                "price_min_decimal": 1500,
                "featured": True,
                "features": ["Hand-woven 'Shimena'", "Custom Fitting", "International Shipping"],
                "badges": ["Bestseller"],
                "venue_attrs": {},
                "attire_attrs": {"rental": False, "tailoringNote": "Custom tailoring included"},
                "catering_attrs": {}, "rental_attrs": {}, "service_attrs": {},
            },
            {
                "title": "Modern Luxury Wedding Dress",
                "category_slug": "ATTIRE",
                "type_label": "Modern Bridal Gown",
                "image": "assets/luxury-wedding-dress.jpg",
                "rating": 4.7, "review_count": 95,
                "location": "Kazanchis, Addis Ababa",
                "price_range": "$2,000 – $8,000",
                "price_min_decimal": 2000,
                "featured": False,
                "features": ["Imported Lace", "Multiple Styles", "Accessory Matching"],
                "badges": [],
                "venue_attrs": {},
                "attire_attrs": {"rental": True, "sizeRange": "US 2-20"},
                "catering_attrs": {}, "rental_attrs": {}, "service_attrs": {},
            },
            # Catering
            {
                "title": "Royal Ethiopian Feast",
                "category_slug": "CATERING",
                "type_label": "Gourmet Ethiopian Cuisine",
                "image": "assets/ethiopian-feast.jpg",
                "rating": 5.0, "review_count": 250,
                "location": "Mobile - Serves all of Addis",
                "price_range": "$50 - $150 per person",
                "price_min_decimal": 50,
                "featured": True,
                "features": ["Full 'Doro Wot'", "Live 'Gored Gored' station", "Vegan Options"],
                "badges": ["Authentic"],
                "venue_attrs": {}, "attire_attrs": {},
                "catering_attrs": {"perPersonRange": "$50-$150", "cuisines": ["Ethiopian", "Eritrean"]},
                "rental_attrs": {}, "service_attrs": {},
            },
            {
                "title": "Addis International Catering",
                "category_slug": "CATERING",
                "type_label": "International & Fusion Cuisine",
                "image": "assets/luxury-catering.jpg",
                "rating": 4.8, "review_count": 110,
                "location": "Mobile - Nationwide",
                "price_range": "$80 - $250 per person",
                "price_min_decimal": 80,
                "featured": False,
                "features": ["Italian, French, Asian options", "Professional Waitstaff", "Full Bar Service"],
                "badges": ["Versatile"],
                "venue_attrs": {}, "attire_attrs": {},
                "catering_attrs": {"perPersonRange": "$80-$250", "cuisines": ["International", "Fusion"]},
                "rental_attrs": {}, "service_attrs": {},
            },
        ]

        # 4. Create Listing objects
        for item in listings_data:
            category_slug = item.get('category_slug')
            if not category_slug or category_slug not in categories:
                self.stdout.write(self.style.WARNING(f"Skipping listing with invalid category: {item.get('title')}"))
                continue

            listing = Listing.objects.create(
                category=categories[category_slug],
                title=item.get('title'),
                type_label=item.get('type_label'),
                image=item.get('image'),
                rating=Decimal(str(item.get('rating', 0))),
                review_count=item.get('review_count', 0),
                location=item.get('location'),
                capacity=item.get('capacity'),
                price_range=item.get('price_range'),
                price_min=Decimal(str(item.get('price_min_decimal', '0.0'))),
                features=item.get('features', []),
                badges=item.get('badges', []),
                featured=item.get('featured', False),
                venue_attrs=item.get('venue_attrs', {}),
                attire_attrs=item.get('attire_attrs', {}),
                catering_attrs=item.get('catering_attrs', {}),
                rental_attrs=item.get('rental_attrs', {}),
                service_attrs=item.get('service_attrs', {}),
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created listing: {listing.title}'))

        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))
