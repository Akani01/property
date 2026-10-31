"""Public, permission-aware cross-module search. No private data is indexed."""
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.urls import reverse
from hiring.models import JobListing
from realestate.models import Property
from education.models import School, University, Bursary
from pricecheck.models import Product

@require_GET
def search_page(request):
    return render(request, 'universal_search.html')

@require_GET
def search_api(request):
    query = request.GET.get('q', '').strip()[:100]
    category = request.GET.get('category', 'all').lower()
    if category not in {'all','jobs','properties','schools','universities','bursaries','products'}:
        return JsonResponse({'error':'Unknown category'}, status=400)
    if len(query) < 2:
        return JsonResponse({'results': [], 'query':query})
    results=[]
    def add(kind, title, detail, url, pk):
        results.append({'type':kind,'title':str(title),'detail':str(detail or '')[:180],'url':url,'id':pk})
    if category in ('all','jobs'):
        for obj in JobListing.objects.filter(status='published').filter(Q(title__icontains=query)|Q(company_name__icontains=query)|Q(location__icontains=query)|Q(job_description__icontains=query)).order_by('-created_at')[:12]:
            add('jobs',obj.title, f'{obj.company_name} · {obj.location}', reverse('job_detail_page',args=[obj.pk]),obj.pk)
    if category in ('all','properties'):
        for obj in Property.objects.filter(is_active=True).exclude(status__in=['closed','maintenance']).filter(Q(title__icontains=query)|Q(description__icontains=query)|Q(city__icontains=query)|Q(address__icontains=query)).order_by('-id')[:12]:
            add('properties',obj.title,obj.city,reverse('property_detail',args=[obj.pk]),obj.pk)
    if category in ('all','schools'):
        for obj in School.objects.filter(is_active=True, is_public=True).filter(Q(name__icontains=query)|Q(city__icontains=query)|Q(province__icontains=query)).order_by('name')[:12]:
            add('schools',obj.name,obj.city,reverse('education_school_detail',args=[obj.pk]),obj.pk)
    if category in ('all','universities'):
        for obj in University.objects.filter(is_active=True, is_public=True).filter(Q(name__icontains=query)|Q(city__icontains=query)|Q(province__icontains=query)).order_by('name')[:12]:
            add('universities',obj.name,obj.city,reverse('education_university_detail',args=[obj.pk]),obj.pk)
    if category in ('all','bursaries'):
        for obj in Bursary.objects.filter(is_active=True,closing_date__gte=timezone.localdate()).filter(Q(title__icontains=query)|Q(provider__icontains=query)|Q(description__icontains=query)).order_by('closing_date')[:12]:
            add('bursaries',obj.title,obj.provider,reverse('education_bursary_detail',args=[obj.pk]),obj.pk)
    if category in ('all','products'):
        for obj in Product.objects.filter(Q(name__icontains=query)|Q(brand__icontains=query)|Q(barcode__iexact=query)).order_by('name')[:12]:
            add('products',obj.name,obj.brand,f'/pricecheck/?q={__import__("urllib.parse",fromlist=["quote"]).quote(query)}',obj.pk)
    results.sort(key=lambda r:(not r['title'].lower().startswith(query.lower()),r['type'],r['title']))
    return JsonResponse({'query':query,'results':results[:48]})
