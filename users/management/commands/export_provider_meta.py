import json
from django.core.management.base import BaseCommand
from users.constants import ALLOWED_PROVIDER_COUNTRIES, DIAL_CODE_MAP
from listings.models import Category

class Command(BaseCommand):
    help = "Export provider meta (allowed countries, dial codes, active service types) as JSON."

    def add_arguments(self, parser):
        parser.add_argument('--out', '-o', type=str, help='Output file path (if omitted prints to stdout)')
        parser.add_argument('--indent', type=int, default=2, help='JSON indentation (default 2)')

    def handle(self, *args, **options):
        # Use listings.Category as provider types
        service_types = list(Category.objects.all().order_by('name').values('slug', 'name'))
        data = {
            'countries': sorted(ALLOWED_PROVIDER_COUNTRIES),
            'dial_codes': {c: DIAL_CODE_MAP[c] for c in ALLOWED_PROVIDER_COUNTRIES if c in DIAL_CODE_MAP},
            'service_types': service_types,
        }
        payload = json.dumps(data, indent=options['indent'], sort_keys=True)
        out_path = options.get('out')
        if out_path:
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(payload + '\n')
            self.stdout.write(self.style.SUCCESS(f'Exported provider meta to {out_path}'))
        else:
            self.stdout.write(payload)
