from django.db import migrations


INDEX_NAME = 'users_auth_user_email_lower_unique'


def dedupe_emails(apps, schema_editor):
    """Before adding functional unique index on lower(email), ensure no duplicates.

    Strategy: For each set of case-insensitive duplicates, keep the earliest (lowest id)
    email untouched. For others, append "+dup<N>" tag before the '@' to preserve
    deliverability potential while making values unique. Example:
        User1: Test@Example.com -> stays Test@Example.com
        User2: test@example.com -> becomes test+dup2@example.com
        User3: TEST@example.com -> becomes TEST+dup3@example.com
    """
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        # SQLite path: uniqueness will be best-effort at app layer; skip structural change.
        return
    # Use raw SQL for efficiency.
    with connection.cursor() as cur:
        # Find duplicate groups (case-insensitive) excluding NULL/empty emails
        cur.execute(
            """
            SELECT lower(email) AS key, array_agg(id ORDER BY id) ids
            FROM auth_user
            WHERE email IS NOT NULL AND email <> ''
            GROUP BY lower(email)
            HAVING COUNT(*) > 1;
            """
        )
        rows = cur.fetchall()
        for key, ids in rows:
            # Skip first id
            for i, user_id in enumerate(ids[1:], start=2):
                # Fetch current email
                cur.execute("SELECT email FROM auth_user WHERE id = %s", [user_id])
                (current_email,) = cur.fetchone()
                if '@' in current_email:
                    local, domain = current_email.split('@', 1)
                    new_email = f"{local}+dup{i}@{domain}"
                else:
                    new_email = f"{current_email}+dup{i}"
                cur.execute("UPDATE auth_user SET email=%s WHERE id=%s", [new_email, user_id])


def add_functional_unique_index(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cur:
        cur.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME} ON auth_user (LOWER(email));"
        )


def drop_functional_unique_index(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cur:
        cur.execute(
            f"DROP INDEX IF EXISTS {INDEX_NAME};"
        )


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0009_merge_email_verified_branch'),
    ]

    operations = [
        migrations.RunPython(dedupe_emails, migrations.RunPython.noop),
        migrations.RunPython(add_functional_unique_index, drop_functional_unique_index),
    ]
