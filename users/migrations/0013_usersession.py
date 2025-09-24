from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0012_email_change_request"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("jti_hash", models.CharField(db_index=True, max_length=64)),
                ("user_agent", models.CharField(blank=True, max_length=300)),
                ("ua_hash", models.CharField(blank=True, max_length=64)),
                ("ip_hash", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen", models.DateTimeField(auto_now=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("label", models.CharField(blank=True, max_length=120)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sessions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-last_seen"],
            },
        ),
        migrations.AddIndex(
            model_name="usersession",
            index=models.Index(fields=["user", "last_seen"], name="users_sess_user_id_3c440a_idx"),
        ),
        migrations.AddIndex(
            model_name="usersession",
            index=models.Index(fields=["jti_hash"], name="users_sess_jti_has_6c4c69_idx"),
        ),
    ]
