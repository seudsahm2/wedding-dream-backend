from django.core.management.base import BaseCommand
from django.db import transaction
from listings.models import Category, Listing


GROUPED_CATEGORIES = [
    {
        "slug": "attire-apparel",
        "name": "Attire & Apparel",
        "subchoices": {
            "Women's Attire": [
                "Bride",
                "Maid of Honor (Mize)",
                "Bridesmaids (Ajabi)",
                "Mother of the Bride/Groom",
                "Flower Girls",
                "Family & Guests (Aunts, Sisters)",
            ],
            "Men's Attire": [
                "Groom",
                "Best Man (Mize)",
                "Groomsmen",
                "Father of the Bride/Groom",
                "Ring Bearers",
                "Family & Guests (Uncles, Brothers)",
            ],
            "Accessories": [
                "Jewelry & Veils",
                "Shoes & Footwear",
                "Cultural Accessories",
            ],
        },
    },
    {
        "slug": "beauty-grooming",
        "name": "Beauty & Grooming",
        "subchoices": {
            "Women's Beauty Services": [
                "Bridal Makeup (At-home)",
                "Bridal Hairstyling (At-home)",
                "Salon Services (Family & Guests)",
                "Manicure & Pedicure",
                "Spa & Skin Treatments",
            ],
            "Men's Grooming": [
                "Haircut & Styling",
                "Professional Shave & Beard Trim",
                "Grooming Packages (At-home)",
            ],
        },
    },
    {
        "slug": "venue-decor",
        "name": "Venue & Decor",
        "subchoices": {
            "Venues & Tents": [
                "Wedding Hall",
                "Hotel Ballroom",
                "Outdoor Garden / Space",
                "Tent Rental",
            ],
            "Decoration Services": [
                "Professional Home Decorators",
                "Venue Decorators (Hall/Hotel)",
                "Stage & Backdrop Design",
            ],
            "Decor & Equipment Rentals": [
                "Lighting & Special Effects",
                "Furniture (Chairs, Tables, etc.)",
                "Props & Thematic Items",
                "Sound System Rental",
            ],
        },
    },
    {
        "slug": "food-catering",
        "name": "Food & Catering",
        "subchoices": {
            "Catering Services": [
                "Full-Service Catering (at Venue)",
                "Professional Home Chefs",
                "Buffet & Plated Dinner Service",
            ],
            "Cake & Desserts": [
                "Wedding Cakes",
                "Dessert Tables & Pastries",
            ],
            "Beverage Services": [
                "Bar Service (Modern & Traditional)",
                "Traditional Drink Preparation",
            ],
            "Food & Kitchen Equipment Rental": [
                "Cooking & Food Preparation Tools",
                "Serving Dishes, Plates & Cutlery",
                "Food Service Tables & Linens",
            ],
        },
    },
    {
        "slug": "services-supplies",
        "name": "Services & Supplies",
        "subchoices": {
            "Invitations & Stationery": [
                "Invitation Card Design & Printing",
                "Wedding Programs & Menus",
            ],
            "Gifts & Favors": [
                "Guest Favors & Souvenirs",
                "Cards & Gift Vendors",
            ],
            "Transportation": [
                "Bridal Car Rental",
                "Guest Transportation (Buses, Vans)",
            ],
        },
    },
]


class Command(BaseCommand):
    help = "Wipe and seed listing categories with grouped subchoices."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Confirm destructive reset of categories table.",
        )
        parser.add_argument(
            "--keep-listings",
            action="store_true",
            help="Preserve existing listings by reassigning them to an 'uncategorized' category before wiping.",
        )

    def handle(self, *args, **options):
        force = options.get("--force") or options.get("force")
        keep_listings = options.get("--keep-listings") or options.get("keep_listings")
        if not force:
            self.stdout.write(self.style.WARNING("Use --force to confirm wiping existing categories."))
            return
        with transaction.atomic():
            if keep_listings:
                # Ensure placeholder exists
                uncategorized, _ = Category.objects.get_or_create(slug="uncategorized", defaults={"name": "Uncategorized"})
                # Reassign all listings to placeholder
                affected = Listing.objects.exclude(category=uncategorized).update(category=uncategorized)
                self.stdout.write(self.style.WARNING(f"Reassigned {affected} listings to 'Uncategorized'."))
                # Delete all categories except placeholder
                Category.objects.exclude(pk=uncategorized.pk).delete()
                self.stdout.write(self.style.WARNING("Cleared existing categories (kept 'Uncategorized')."))
            else:
                # Wipe all categories; cascades will delete related listings
                Category.objects.all().delete()
                self.stdout.write(self.style.WARNING("Cleared existing categories (and cascaded listings)."))
            for item in GROUPED_CATEGORIES:
                Category.objects.create(
                    slug=item["slug"],
                    name=item["name"],
                    subchoices=item.get("subchoices") or {},
                )
                self.stdout.write(self.style.SUCCESS(f"Seeded category: {item['name']}"))
        self.stdout.write(self.style.SUCCESS("Category seeding completed."))
