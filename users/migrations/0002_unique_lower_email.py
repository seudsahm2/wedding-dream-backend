from django.db import migrations


CONSTRAINT_NAME = 'users_user_email_lower_unique'

def add_ci_unique_email(apps, schema_editor):
    # Raw SQL to add functional unique index for lower(email) if using Postgres; for SQLite fallback we skip.
    engine = schema_editor.connection.vendor
    if engine == 'postgresql':
        schema_editor.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS {CONSTRAINT_NAME} ON auth_user (LOWER(email));')

def remove_ci_unique_email(apps, schema_editor):
    engine = schema_editor.connection.vendor
    if engine == 'postgresql':
        schema_editor.execute(f'DROP INDEX IF EXISTS {CONSTRAINT_NAME};')


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_ci_unique_email, remove_ci_unique_email),
    ]
