"""
Staging settings

This mirrors production security, differing only by environment variables.
Point DATABASE_URL to your Supabase Postgres in the staging environment.
"""

from wedding_dream.settings import prod as _prod

# Pull in all uppercase settings from prod
globals().update({k: v for k, v in _prod.__dict__.items() if k.isupper()})

# Optional: You can tweak values here specific to staging if needed
# DEBUG = False  # already false in prod