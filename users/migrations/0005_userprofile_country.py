from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0004_providerservicetype_userprofile_business_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='country',
            field=models.CharField(max_length=2, blank=True, null=True, help_text='ISO 3166-1 alpha-2 country code'),
        ),
        migrations.AlterModelOptions(
            name='providerservicetype',
            options={'ordering': ['name']},
        ),
    ]
