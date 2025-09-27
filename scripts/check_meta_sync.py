#!/usr/bin/env python
"""CI helper to compare backend constants with the committed frontend static dial code map.

Exit codes:
 0 - OK
 1 - Mismatch in country sets (backend allows countries not present in frontend map)
 2 - Frontend has extra countries not in backend allowed set.
"""
from pathlib import Path
import re
import sys

BACKEND_CONSTANTS = Path(__file__).resolve().parents[1] / 'users' / 'constants.py'
FRONTEND_DIAL_CODES = Path(__file__).resolve().parents[2] / 'habesha-wedding-dream' / 'src' / 'lib' / 'dialCodes.ts'

backend_text = BACKEND_CONSTANTS.read_text(encoding='utf-8')
frontend_text = FRONTEND_DIAL_CODES.read_text(encoding='utf-8')

# Extract backend allowed countries
allowed = set(re.findall(r'"([A-Z]{2})"\s*[,)]', backend_text.split('ALLOWED_PROVIDER_COUNTRIES')[1].split('}')[0]))
# Extract frontend dial code map keys
front_keys = set(re.findall(r'\b([A-Z]{2}):\s*"\+\d+"', frontend_text))

missing_in_front = sorted(allowed - front_keys)
extra_in_front = sorted(front_keys - allowed)

if missing_in_front:
    print(f"Backend countries missing dial codes in frontend: {missing_in_front}")
    sys.exit(1)
if extra_in_front:
    print(f"Frontend dial code countries not allowed in backend: {extra_in_front}")
    sys.exit(2)
print("Provider meta sync OK (countries)")
