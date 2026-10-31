import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pricecheck.models import Retailer, Product, Offer, PriceHistory

class Command(BaseCommand):
    help = 'Import authorised merchant CSV with retailer,product,retailer_sku,price,category,brand,barcode,product_url,branch'
    def add_arguments(self,parser): parser.add_argument('csv_path')
    def handle(self,*args,**opts):
        count=0
        with open(opts['csv_path'],newline='',encoding='utf-8-sig') as file:
            for row in csv.DictReader(file):
                try:
                    name=row['product'].strip(); merchant=row['retailer'].strip(); sku=row['retailer_sku'].strip(); price=Decimal(row['price'])
                    if not all((name,merchant,sku)) or price<0: raise ValueError('Invalid required fields')
                    with transaction.atomic():
                        retailer,_=Retailer.objects.get_or_create(name=merchant)
                        barcode=row.get('barcode','').strip()
                        if barcode: product,_=Product.objects.get_or_create(barcode=barcode,defaults={'name':name,'category':row.get('category') or 'Other','brand':row.get('brand') or ''})
                        else: product,_=Product.objects.get_or_create(name=name,brand=row.get('brand') or '',defaults={'category':row.get('category') or 'Other'})
                        offer,_=Offer.objects.update_or_create(retailer=retailer,retailer_sku=sku,branch=row.get('branch') or '',defaults={'product':product,'price':price,'product_url':row.get('product_url') or '','source':'merchant'})
                        PriceHistory.objects.create(offer=offer,price=price)
                    count+=1
                except (KeyError,InvalidOperation,ValueError) as exc: raise CommandError(f'Bad row {count+2}: {exc}') from exc
        self.stdout.write(self.style.SUCCESS(f'Imported {count} offers'))
