import math
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Min, Q
from django.views.decorators.http import require_GET
from .models import Product, Offer, RetailerBranch


def home(request):
    return render(request, 'pricecheck/home.html')


def location_args(request):
    try:
        lat = float(request.GET['lat']); lon = float(request.GET['lon'])
        radius = min(100, max(1, float(request.GET.get('radius', 25))))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        return lat, lon, radius
    except (KeyError, ValueError, TypeError):
        return None


def distance_km(lat1, lon1, lat2, lon2):
    a1, a2 = math.radians(lat1), math.radians(lat2)
    dlat = a2-a1; dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(a1)*math.cos(a2)*math.sin(dlon/2)**2
    return round(6371.0088 * 2 * math.asin(min(1, math.sqrt(a))), 1)


@require_GET
def search(request):
    q = request.GET.get('q', '').strip()[:120]
    category = request.GET.get('category', '').strip()[:80]
    products = Product.objects.all()
    if q:
        products = products.filter(Q(name__icontains=q) | Q(brand__icontains=q) | Q(barcode__iexact=q))
    if category and category.lower() != 'all':
        products = products.filter(category__iexact=category)
    products = products.annotate(lowest=Min('offers__price', filter=Q(offers__available=True, offers__retailer__active=True))).order_by('name')[:40]
    return JsonResponse({'results': [{'id': x.id, 'name': x.name, 'brand': x.brand, 'category': x.category, 'image': x.image_url, 'lowest': str(x.lowest) if x.lowest is not None else None} for x in products]})


@require_GET
def offers(request, pk):
    nearby = request.GET.get('nearby') == '1'
    location = location_args(request)
    entries = Offer.objects.filter(product_id=pk, available=True, retailer__active=True).select_related('retailer', 'branch_location').order_by('price')[:500]
    results = []
    for o in entries:
        branch = o.branch_location
        km = None
        if branch and branch.active and location:
            km = distance_km(location[0], location[1], float(branch.latitude), float(branch.longitude))
        if nearby and (not location or km is None or km > location[2]):
            continue
        results.append({'retailer': o.retailer.name, 'price': str(o.price), 'delivery_fee': str(o.delivery_fee) if o.delivery_fee is not None else None, 'url': o.product_url, 'branch': branch.name if branch else o.branch, 'distance_km': km, 'checked_at': o.checked_at.isoformat(), 'source': o.source})
    results.sort(key=lambda x: (float(x['price']), x['distance_km'] if x['distance_km'] is not None else 999999))
    return JsonResponse({'offers': results[:60], 'location_available': bool(location), 'nearby': nearby})


@require_GET
def branches(request):
    location = location_args(request)
    if not location:
        return JsonResponse({'error': 'Valid coordinates required'}, status=400)
    results = []
    for branch in RetailerBranch.objects.filter(active=True, retailer__active=True).select_related('retailer'):
        km = distance_km(location[0], location[1], float(branch.latitude), float(branch.longitude))
        if km <= location[2]:
            results.append({'id': branch.pk, 'retailer': branch.retailer.name, 'name': branch.name, 'address': branch.address, 'distance_km': km})
    results.sort(key=lambda x: x['distance_km'])
    return JsonResponse({'results': results[:50]})
