from django.core.management.base import BaseCommand
from users.models import ProviderServiceType

DEFAULT_TYPES = [
    ("attire-bridal", "Bridal Gowns & Accessories"),
    ("attire-groom", "Groom Suits & Accessories"),
    ("attire-party", "Wedding Party Attire"),
    ("beauty-bridal", "Bridal Beauty"),
    ("beauty-groom", "Groom Grooming & Care"),
    ("venue", "Venues & Halls"),
    ("catering", "Chef & Catering Services"),
    ("rental-equipment", "Equipment Rental"),
    ("decor-service", "Professional Decorators"),
    ("decor-rental", "Decor & Stage Rentals"),
    ("tent", "Tent Rentals"),
    ("makeup", "Makeup Artists"),
    ("cards-gifts", "Cards & Gifts"),
]

class Command(BaseCommand):
    help = "Seed provider service types (idempotent)"

    def handle(self, *args, **options):
        created = 0
        for slug, name in DEFAULT_TYPES:
            obj, was_created = ProviderServiceType.objects.update_or_create(
                slug=slug, defaults={"name": name, "active": True}
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} new provider service types."))