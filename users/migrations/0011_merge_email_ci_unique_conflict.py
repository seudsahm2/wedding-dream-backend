from django.db import migrations


class Migration(migrations.Migration):
    # Merge 0002_unique_lower_email (legacy) and 0010_email_ci_unique (new consolidated)
    dependencies = [
        ('users', '0002_unique_lower_email'),
        ('users', '0010_email_ci_unique'),
    ]

    operations = []
