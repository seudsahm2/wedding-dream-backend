# Generated manually for ListingAvailability model
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0004_listing_image_thumb_alter_listing_image'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ListingAvailability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(choices=[('tentative', 'Tentative'), ('confirmed', 'Confirmed'), ('canceled', 'Canceled')], default='confirmed', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_availability', to=settings.AUTH_USER_MODEL)),
                ('listing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='availability', to='listings.listing')),
            ],
            options={
                'ordering': ['start_date'],
            },
        ),
        migrations.AddIndex(
            model_name='listingavailability',
            index=models.Index(fields=['listing', 'start_date'], name='listings_li_listing_7ff800_idx'),
        ),
        migrations.AddIndex(
            model_name='listingavailability',
            index=models.Index(fields=['listing', 'end_date'], name='listings_li_listing_c8ab45_idx'),
        ),
    ]
