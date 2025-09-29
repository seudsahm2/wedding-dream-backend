from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_userprofile_provider_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='business_email',
            field=models.EmailField(blank=True, null=True, max_length=254, help_text='Optional business contact email (may differ from account email)'),
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='provider_types',
        ),
    ]
