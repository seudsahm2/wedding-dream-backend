from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_drop_providerservicetype"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="business_email_verified",
            field=models.BooleanField(default=False),
        ),
    ]
