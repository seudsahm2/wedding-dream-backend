from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import connection, transaction


class Command(BaseCommand):
    help = (
        "Safely delete users by first removing SimpleJWT blacklist/Outstanding tokens that block FK constraints. "
        "By default deletes ALL non-staff, non-superuser accounts."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--only-user-ids', nargs='+', type=int, default=None,
            help='Optional explicit list of user IDs to delete (overrides default selection).'
        )
        parser.add_argument(
            '--dry-run', action='store_true', help='Print actions without executing.'
        )

    def handle(self, *args, **options):
        User = get_user_model()
        only_ids = options.get('only_user_ids')
        dry_run = bool(options.get('dry_run'))

        if only_ids:
            qs = User.objects.filter(id__in=only_ids)
        else:
            qs = User.objects.filter(is_staff=False, is_superuser=False)

        user_ids = list(qs.values_list('id', flat=True))
        if not user_ids:
            self.stdout.write(self.style.WARNING('No users matched selection. Nothing to do.'))
            return

        self.stdout.write(f"Selected {len(user_ids)} user(s) for deletion: {user_ids[:10]}{'...' if len(user_ids) > 10 else ''}")

        # Clean up token_blacklist tables if they exist
        with connection.cursor() as cur:
            # Detect existence of token tables (works on Postgres and SQLite)
            def table_exists(name: str) -> bool:
                vendor = connection.vendor
                if vendor == 'postgresql':
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_name=%s
                        )
                    """, [name])
                    return bool(cur.fetchone()[0])
                elif vendor == 'sqlite':
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=%s", [name])
                    return bool(cur.fetchone())
                else:
                    # best effort
                    try:
                        cur.execute(f"SELECT 1 FROM {name} WHERE 1=0")
                        return True
                    except Exception:
                        return False

            tbl_outstanding = 'token_blacklist_outstandingtoken'
            tbl_blacklisted = 'token_blacklist_blacklistedtoken'
            has_outstanding = table_exists(tbl_outstanding)
            has_blacklisted = table_exists(tbl_blacklisted)

            if has_outstanding:
                in_list = tuple(user_ids)
                if dry_run:
                    self.stdout.write(self.style.NOTICE(
                        f"Would delete rows from {tbl_blacklisted} referencing tokens of user_ids={in_list} (if table exists)"
                    ))
                    self.stdout.write(self.style.NOTICE(
                        f"Would delete rows from {tbl_outstanding} for user_ids={in_list}"
                    ))
                else:
                    with transaction.atomic():
                        if has_blacklisted:
                            cur.execute(
                                f"""
                                DELETE FROM {tbl_blacklisted}
                                WHERE token_id IN (
                                    SELECT id FROM {tbl_outstanding} WHERE user_id IN %s
                                )
                                """,
                                [in_list],
                            )
                        cur.execute(
                            f"DELETE FROM {tbl_outstanding} WHERE user_id IN %s",
                            [in_list],
                        )
                        self.stdout.write(self.style.SUCCESS("Cleared SimpleJWT blacklist/outstanding tokens."))
            else:
                self.stdout.write("No token_blacklist tables detected; skipping token cleanup.")

            # Clean up legacy/custom session table if present: users_usersession
            tbl_user_session = 'users_usersession'
            if table_exists(tbl_user_session):
                in_list = tuple(user_ids)
                if dry_run:
                    self.stdout.write(self.style.NOTICE(
                        f"Would delete rows from {tbl_user_session} for user_ids={in_list}"
                    ))
                else:
                    cur.execute(
                        f"DELETE FROM {tbl_user_session} WHERE user_id IN %s",
                        [in_list],
                    )
                    self.stdout.write(self.style.SUCCESS(f"Cleared rows in {tbl_user_session}."))

        if dry_run:
            self.stdout.write(self.style.NOTICE("Dry-run enabled: skipping user deletion."))
            return

        # Finally, delete users
        deleted_count = qs.delete()[0]
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} user record(s)."))
