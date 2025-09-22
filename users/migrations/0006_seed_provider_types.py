from django.db import migrations

def seed_types(apps, schema_editor):
    ProviderServiceType = apps.get_model('users', 'ProviderServiceType')
    if not ProviderServiceType.objects.filter(slug='venue').exists():
        ProviderServiceType.objects.create(slug='venue', name='Venue', active=True)

def unseed_types(apps, schema_editor):
    ProviderServiceType = apps.get_model('users', 'ProviderServiceType')
    # Keep data (safe), or uncomment to delete:
    # ProviderServiceType.objects.filter(slug='venue').delete()
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0005_userprofile_country'),
    ]

    operations = [
        migrations.RunPython(seed_types, unseed_types),
    ]
