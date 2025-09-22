# Migration moved to resolve conflict: add email_verified after city field
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_userprofile_city'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email_verified',
            field=models.BooleanField(default=False, help_text='True once user has confirmed email address'),
        ),
    ]
