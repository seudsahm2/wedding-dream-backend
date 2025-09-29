from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_add_business_email_drop_legacy_types'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='ProviderServiceType',
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql='DROP TABLE IF EXISTS "users_providerservicetype" CASCADE;',
                    reverse_sql='CREATE TABLE IF NOT EXISTS "users_providerservicetype" (slug varchar(60) PRIMARY KEY, name varchar(120) NOT NULL, active boolean NOT NULL DEFAULT true);'
                ),
            ],
        ),
    ]
