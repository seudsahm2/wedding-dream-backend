from django.conf import settings
from django.db import migrations, models


def copy_existing_participants(apps, schema_editor):
    """Copy rows from the implicit M2M table into ThreadParticipant before swapping."""
    connection = schema_editor.connection
    # Old implicit M2M table name created by Django for messaging.MessageThread.participants
    table_name = 'messaging_messagethread_participants'
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT messagethread_id, user_id FROM {table_name}")
            rows = cursor.fetchall()
    except Exception:
        # Table may not exist on fresh installs; nothing to copy
        rows = []

    if not rows:
        return

    ThreadParticipant = apps.get_model('messaging', 'ThreadParticipant')

    seen = set()
    objs = []
    for thread_id, user_id in rows:
        key = (thread_id, user_id)
        if key in seen:
            continue
        seen.add(key)
        objs.append(ThreadParticipant(thread_id=thread_id, user_id=user_id))

    if objs:
        ThreadParticipant.objects.bulk_create(objs, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0003_threadparticipant"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(copy_existing_participants, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="messagethread",
            name="participants",
        ),
        migrations.AddField(
            model_name="messagethread",
            name="participants",
            field=models.ManyToManyField(
                related_name="message_threads",
                through="messaging.ThreadParticipant",
                through_fields=("thread", "user"),
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
