from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_userprofile_business_email_verified'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='provider_subchoices',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='provider_subchoice_tokens',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
