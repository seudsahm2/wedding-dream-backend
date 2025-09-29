from django.db import migrations


def seed_categories_from_provider_types(apps, schema_editor):
    Category = apps.get_model('listings', 'Category')
    ProviderServiceType = apps.get_model('users', 'ProviderServiceType')
    # For each existing provider service type, ensure a matching Category exists
    for pst in ProviderServiceType.objects.all().iterator():
        if not Category.objects.filter(slug=pst.slug).exists():
            Category.objects.create(slug=pst.slug, name=pst.name)


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0006_rename_listings_li_listing_7ff800_idx_listings_li_listing_9d4a9d_idx_and_more'),
        ('users', '0006_seed_provider_types'),
    ]

    operations = [
        migrations.RunPython(seed_categories_from_provider_types, migrations.RunPython.noop),
    ]
