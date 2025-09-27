from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_seed_provider_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='city',
            field=models.CharField(blank=True, help_text='City / locality name (frontend library sourced)', max_length=120, null=True),
        ),
    ]
