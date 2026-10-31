from django.db import models
from django.conf import settings

class Retailer(models.Model):
    name = models.CharField(max_length=160, unique=True)
    website = models.URLField(blank=True)
    logo = models.URLField(blank=True)
    active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=120, blank=True)
    barcode = models.CharField(max_length=80, blank=True, db_index=True)
    sku = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=80, default='Other', db_index=True)
    image_url = models.URLField(blank=True)
    def __str__(self): return self.name

class Offer(models.Model):
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, related_name='offers')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='offers')
    retailer_sku = models.CharField(max_length=160)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='ZAR')
    product_url = models.URLField(blank=True)
    available = models.BooleanField(default=True)
    branch = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=30, default='merchant')
    checked_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['retailer','retailer_sku','branch'], name='pricecheck_unique_offer')]
    def __str__(self): return f'{self.product} - {self.retailer}'

class PriceHistory(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='history')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True)

class PriceAlert(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    target_price = models.DecimalField(max_digits=12, decimal_places=2)
    active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user','product'], name='pricecheck_unique_alert')]
