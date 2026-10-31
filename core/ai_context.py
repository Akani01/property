"""Limited, database-grounded context for OppoGlobe chat.
Only published/public records are exposed. Never send private user records to an LLM.
"""
import re
from django.db.models import Q


def build_chat_context(query, user):
    from realestate.models import Property
    from hiring.models import JobListing
    tokens = [w for w in re.findall(r'[\w-]+', query) if len(w) >= 3][:7]
    result = {'platform': 'OppoGlobe', 'user': {'username': user.username}, 'properties': [], 'jobs': []}
    if not tokens:
        return result
    prop_filter = Q()
    job_filter = Q()
    for token in tokens:
        prop_filter |= Q(title__icontains=token) | Q(city__icontains=token) | Q(description__icontains=token)
        job_filter |= Q(title__icontains=token) | Q(location__icontains=token) | Q(company_name__icontains=token)
    try:
        for p in Property.objects.filter(is_active=True, status='available').filter(prop_filter).order_by('-pk')[:6]:
            result['properties'].append({'id': str(p.pk), 'title': p.title, 'city': p.city, 'listing_type': p.listing_type, 'price_zar': str(p.base_price)})
    except Exception:
        # Missing migrations or unavailable module must not crash chat.
        pass
    try:
        for j in JobListing.objects.filter(status='published').filter(job_filter).order_by('-pk')[:6]:
            result['jobs'].append({'id': str(j.pk), 'title': j.title, 'company': j.company_name, 'location': j.location, 'apply_by': str(j.apply_by)})
    except Exception:
        pass
    return result
