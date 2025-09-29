from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0007_seed_categories_from_provider_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='subchoices',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]
