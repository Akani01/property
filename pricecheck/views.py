from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Min, Q
from django.views.decorators.http import require_GET
from .models import Product, Offer

def home(request):
    return render(request, 'pricecheck/home.html')

@require_GET
def search(request):
    q = request.GET.get('q','').strip()[:120]
    category = request.GET.get('category','').strip()[:80]
    products = Product.objects.all()
    if q: products = products.filter(Q(name__icontains=q)|Q(brand__icontains=q)|Q(barcode__iexact=q))
    if category and category.lower()!='all': products = products.filter(category__iexact=category)
    products = products.annotate(lowest=Min('offers__price',filter=Q(offers__available=True))).order_by('name')[:40]
    return JsonResponse({'results':[{'id':x.id,'name':x.name,'brand':x.brand,'category':x.category,'image':x.image_url,'lowest':str(x.lowest) if x.lowest is not None else None} for x in products]})

@require_GET
def offers(request, pk):
    entries=Offer.objects.filter(product_id=pk,available=True,retailer__active=True).select_related('retailer').order_by('price')[:60]
    return JsonResponse({'offers':[{'retailer':o.retailer.name,'price':str(o.price),'delivery_fee':str(o.delivery_fee) if o.delivery_fee is not None else None,'url':o.product_url,'branch':o.branch,'checked_at':o.checked_at.isoformat(),'source':o.source} for o in entries]})


from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from .models import Retailer, PriceHistory

@login_required
@require_POST
def business_add_offer(request):
    user=request.user
    if not (user.is_staff or user.is_superuser or (getattr(user,'user_type',None)=='admin' and hasattr(user,'business_profile'))):
        return JsonResponse({'success':False,'error':'Business account required'},status=403)
    name=request.POST.get('name','').strip()[:255]
    barcode=request.POST.get('barcode','').strip()[:80]
    sku=request.POST.get('sku','').strip()[:120]
    category=request.POST.get('category','Other').strip()[:80]
    brand=request.POST.get('brand','').strip()[:120]
    if not name or not sku:
        return JsonResponse({'success':False,'error':'Product name and SKU are required'},status=400)
    try:
        price=Decimal(request.POST.get('price',''))
        if not price.is_finite() or price<=0 or price>9999999999:
            raise InvalidOperation
    except (InvalidOperation,TypeError):
        return JsonResponse({'success':False,'error':'Enter a valid positive price'},status=400)
    from hiring.models import BusinessProfile
    profile=BusinessProfile.objects.filter(user=user).first()
    if not profile and not (user.is_staff or user.is_superuser):
        return JsonResponse({'success':False,'error':'Business profile required'},status=403)
    store_name=profile.company_name if profile else 'OppoGlobe Admin'
    with transaction.atomic():
        retailer,_=Retailer.objects.get_or_create(name=store_name,defaults={'active':True})
        product=Product.objects.filter(barcode=barcode).first() if barcode else None
        if product is None:
            product=Product.objects.filter(name__iexact=name,brand__iexact=brand).first()
        if product is None:
            product=Product.objects.create(name=name,brand=brand,barcode=barcode,sku=sku,category=category)
        offer,_=Offer.objects.update_or_create(retailer=retailer,retailer_sku=sku,branch='',defaults={'product':product,'price':price,'currency':'ZAR','available':True,'source':'merchant'})
        PriceHistory.objects.create(offer=offer,price=price)
    return JsonResponse({'success':True,'product_id':product.pk,'offer_id':offer.pk,'message':'Offer saved'})
