from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('messaging', '0002_contactrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='ThreadParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unread_count', models.PositiveIntegerField(default=0)),
                ('last_read_at', models.DateTimeField(blank=True, null=True)),
                ('thread', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='thread_participants', to='messaging.messagethread')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='thread_participations', to='auth.user')),
            ],
            options={
                'unique_together': {('thread', 'user')},
            },
        ),
    ]
