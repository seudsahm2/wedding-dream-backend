from django.apps import AppConfig
from django.core.cache import cache

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class ListingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "listings"

    def ready(self):  # pragma: no cover
        from .models import Category, Listing

        @receiver([post_save, post_delete], sender=Category)
        def _invalidate_categories_cache(*args, **kwargs):
            cache.clear()  # conservative: clear all; can be refined to specific keys

        @receiver([post_save, post_delete], sender=Listing)
        def _invalidate_listings_cache(*args, **kwargs):
            cache.clear()
