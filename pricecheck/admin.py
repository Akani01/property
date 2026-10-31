from django.contrib import admin
from .models import Retailer, RetailerBranch, Product, Offer, PriceHistory, PriceAlert
admin.site.register(Retailer)
admin.site.register(RetailerBranch)
admin.site.register(Product)
admin.site.register(Offer)
admin.site.register(PriceHistory)
admin.site.register(PriceAlert)
