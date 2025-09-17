"""
Legacy settings shim.

This project now uses split settings modules under wedding_dream.settings.
If DJANGO_SETTINGS_MODULE still points at 'wedding_dream.settings',
we load the development settings by default for backward compatibility.
"""

import importlib

_dev = importlib.import_module('wedding_dream.settings.dev')
globals().update({k: v for k, v in _dev.__dict__.items() if k.isupper()})
