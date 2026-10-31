"""Import a licensed retailer JSON feed from a configured HTTPS URL or local JSON file.

No retailer is connected by default. Configure each feed only after obtaining
commercial permission. Format: {"items": [{"retailer": "...", "sku": "...",
"name": "...", "price": "12.99", "barcode": "...", "url": "https://..."}]}
"""
import json
import os
import ssl
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pricecheck.models import Offer, PriceHistory, Product, Retailer


class Command(BaseCommand):
    help = 'Synchronise an authorised retailer feed; configure URL and token in environment'

    def add_arguments(self, parser):
        parser.add_argument('--file', help='Local licensed JSON feed for testing/import')
        parser.add_argument('--url-env', default='PRICECHECK_FEED_URL', help='Name of environment variable holding the HTTPS feed URL')
        parser.add_argument('--token-env', default='PRICECHECK_FEED_TOKEN', help='Name of environment variable holding the feed bearer token')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        if options['file']:
            with open(options['file'], encoding='utf-8') as stream:
                payload = json.load(stream)
        else:
            url = os.getenv(options['url_env'], '').strip()
            parsed = urlparse(url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                raise CommandError('Configure a valid HTTPS retailer feed URL first')
            allowed = [x.strip().lower() for x in os.getenv('PRICECHECK_ALLOWED_FEED_HOSTS', '').split(',') if x.strip()]
            if parsed.hostname.lower() not in allowed:
                raise CommandError('Feed host must be explicitly listed in PRICECHECK_ALLOWED_FEED_HOSTS')
            headers = {'Accept':'application/json', 'User-Agent':'OppoGlobePriceCheck/1.0'}
            token = os.getenv(options['token_env'], '')
            if token:
                headers['Authorization'] = 'Bearer ' + token
            # Reject redirects to avoid forwarding credentials to unexpected hosts.
            from urllib.request import build_opener, HTTPSHandler, HTTPRedirectHandler
            class NoRedirect(HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None
            opener = build_opener(HTTPSHandler(context=ssl.create_default_context()), NoRedirect())
            try:
                with opener.open(Request(url, headers=headers), timeout=20) as response:
                    if int(response.headers.get('Content-Length', '0')) > 5_000_000:
                        raise CommandError('Feed exceeds 5 MB')
                    raw = response.read(5_000_001)
                    if len(raw) > 5_000_000:
                        raise CommandError('Feed exceeds 5 MB')
                    payload = json.loads(raw)
            except (OSError, ValueError) as exc:
                raise CommandError('Unable to retrieve or parse authorised feed') from exc
        items = payload.get('items') if isinstance(payload, dict) else None
        if not isinstance(items, list) or len(items) > 10000:
            raise CommandError('Feed must contain an items list with no more than 10,000 entries')
        count = 0
        for i, row in enumerate(items, 1):
            try:
                merchant = str(row['retailer']).strip()[:160]
                sku = str(row['sku']).strip()[:160]
                name = str(row['name']).strip()[:255]
                price = Decimal(str(row['price']))
                if not merchant or not sku or not name or not price.is_finite() or price < 0 or price > 9999999999:
                    raise ValueError('Invalid required value')
                if options['dry_run']:
                    count += 1
                    continue
                with transaction.atomic():
                    retailer, _ = Retailer.objects.get_or_create(name=merchant)
                    barcode = str(row.get('barcode') or '').strip()[:80]
                    brand = str(row.get('brand') or '').strip()[:120]
                    category = str(row.get('category') or 'Other').strip()[:80]
                    if barcode:
                        product, _ = Product.objects.get_or_create(barcode=barcode, defaults={'name':name,'brand':brand,'category':category})
                    else:
                        product, _ = Product.objects.get_or_create(name=name, brand=brand, defaults={'category':category})
                    branch = str(row.get('branch') or '').strip()[:200]
                    url = str(row.get('url') or '')[:200]
                    if url and urlparse(url).scheme not in ('http', 'https'):
                        raise ValueError('Invalid product URL')
                    offer, created = Offer.objects.update_or_create(retailer=retailer, retailer_sku=sku, branch=branch, defaults={'product':product,'price':price,'product_url':url,'source':'authorised_feed','available':bool(row.get('available',True))})
                    if created or not PriceHistory.objects.filter(offer=offer).order_by('-recorded_at').values_list('price',flat=True).first() == price:
                        PriceHistory.objects.create(offer=offer,price=price)
                count += 1
            except (KeyError, TypeError, InvalidOperation, ValueError) as exc:
                raise CommandError(f'Invalid feed item {i}: {exc}') from exc
        self.stdout.write(self.style.SUCCESS(f'{"Validated" if options["dry_run"] else "Imported"} {count} offers'))
