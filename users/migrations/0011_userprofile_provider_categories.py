from django.db import migrations, models


def backfill_provider_categories(apps, schema_editor):
    UserProfile = apps.get_model('users', 'UserProfile')
    Category = apps.get_model('listings', 'Category')
    ProviderServiceType = apps.get_model('users', 'ProviderServiceType')
    for profile in UserProfile.objects.all().iterator():
        # If old M2M has slugs that also exist in listings.Category, link them
        try:
            old = list(getattr(profile, 'provider_types').all())
        except Exception:
            old = []
        slugs = [getattr(pt, 'slug', None) for pt in old]
        slugs = [s for s in slugs if s]
        if not slugs:
            continue
        cats = list(Category.objects.filter(slug__in=slugs))
        if cats:
            getattr(profile, 'provider_categories').set(cats)


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0007_seed_categories_from_provider_types'),
        ('users', '0010_userprofile_provider_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='provider_categories',
            field=models.ManyToManyField(blank=True, related_name='profiles', to='listings.category'),
        ),
        migrations.RunPython(backfill_provider_categories, migrations.RunPython.noop),
    ]
