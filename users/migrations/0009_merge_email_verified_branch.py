from django.db import migrations


class Migration(migrations.Migration):
    # Merge migration to unify branches from 0002_userprofile_email_verified (now no-op)
    # and the main chain ending with 0008_userprofile_email_verified.
    dependencies = [
        ('users', '0002_userprofile_email_verified'),
        ('users', '0008_userprofile_email_verified'),
    ]

    operations = []
