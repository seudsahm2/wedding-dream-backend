from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_merge_email_verified_branch'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Create the M2M table only if it doesn't already exist (avoids duplicate-table errors on environments
            # where the table was manually created or left over from earlier runs)
            database_operations=[
                                migrations.RunSQL(
                                        sql='''
                                        CREATE TABLE IF NOT EXISTS "users_userprofile_provider_types" (
                                                "userprofile_id" integer NOT NULL REFERENCES "users_userprofile" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
                                                "providerservicetype_id" varchar(60) NOT NULL REFERENCES "users_providerservicetype" ("slug") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
                                        );
                                        DO $$ BEGIN
                                            IF NOT EXISTS (
                                                SELECT 1 FROM pg_indexes WHERE schemaname = ANY (current_schemas(false)) AND indexname = 'users_userprofile_provider_types_userprofile_id_providerservicetype_id_uniq'
                                            ) THEN
                                                CREATE UNIQUE INDEX "users_userprofile_provider_types_userprofile_id_providerservicetype_id_uniq"
                                                ON "users_userprofile_provider_types" ("userprofile_id", "providerservicetype_id");
                                            END IF;
                                        END $$;
                                        ''',
                    reverse_sql='''
                    -- Intentionally do not drop the table to avoid data loss on migration rollback
                    ''',
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='userprofile',
                    name='provider_types',
                    field=models.ManyToManyField(blank=True, related_name='profiles', to='users.providerservicetype'),
                ),
            ],
        ),
    ]
