# ads/utils.py

from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from .models import Ad, AdImpression, AdClick, AdConversion, AdCategory
import logging

logger = logging.getLogger(__name__)


def get_random_ad(position='feed', user=None):
    """
    Get a random active ad for a specific position
    
    Args:
        position (str): Ad placement position (feed, sidebar, top, bottom, popup, both)
        user (User): Optional user for targeting
    
    Returns:
        Ad: Random active ad or None
    """
    now = timezone.now()
    ads = Ad.objects.filter(
        status=Ad.STATUS_ACTIVE,
        is_active=True,
        start_date__lte=now
    ).exclude(
        end_date__lt=now
    ).exclude(
        max_impressions__lte=Ad.objects.get_queryset().model.impressions
    ).exclude(
        max_clicks__lte=Ad.objects.get_queryset().model.clicks
    ).filter(
        Q(position=position) | Q(position=Ad.PLACEMENT_BOTH)
    )
    
    if user and user.is_authenticated:
        # Apply targeting filters
        if hasattr(user, 'user_type'):
            ads = ads.filter(
                Q(target_user_types__contains=[user.user_type]) | 
                Q(target_user_types__isnull=True) |
                Q(target_user_types=[])
            )
        
        # Apply age targeting if available
        if hasattr(user, 'applicantprofile') and user.applicantprofile:
            profile = user.applicantprofile
            if hasattr(profile, 'birth_date') and profile.birth_date:
                today = timezone.now().date()
                age = today.year - profile.birth_date.year - ((today.month, today.day) < (profile.birth_date.month, profile.birth_date.day))
                ads = ads.filter(
                    Q(target_min_age__lte=age) | Q(target_min_age__isnull=True)
                ).filter(
                    Q(target_max_age__gte=age) | Q(target_max_age__isnull=True)
                )
    
    ads = ads.order_by('-priority', '?')
    return ads.first()


def get_ads_for_position(position='feed', limit=10, user=None):
    """
    Get multiple ads for a specific position
    
    Args:
        position (str): Ad placement position
        limit (int): Maximum number of ads to return
        user (User): Optional user for targeting
    
    Returns:
        QuerySet: List of active ads
    """
    now = timezone.now()
    ads = Ad.objects.filter(
        status=Ad.STATUS_ACTIVE,
        is_active=True,
        start_date__lte=now
    ).exclude(
        end_date__lt=now
    ).exclude(
        max_impressions__lte=Ad.objects.get_queryset().model.impressions
    ).exclude(
        max_clicks__lte=Ad.objects.get_queryset().model.clicks
    ).filter(
        Q(position=position) | Q(position=Ad.PLACEMENT_BOTH)
    )
    
    if user and user.is_authenticated:
        if hasattr(user, 'user_type'):
            ads = ads.filter(
                Q(target_user_types__contains=[user.user_type]) | 
                Q(target_user_types__isnull=True) |
                Q(target_user_types=[])
            )
    
    ads = ads.order_by('-priority', '-created_at')[:limit]
    return ads


def calculate_ad_ctr(ad):
    """
    Calculate Click-Through Rate for an ad
    
    Args:
        ad (Ad): Ad instance
    
    Returns:
        float: CTR percentage
    """
    if ad.impressions > 0:
        return (ad.clicks / ad.impressions) * 100
    return 0.0


def calculate_ad_conversion_rate(ad):
    """
    Calculate Conversion Rate for an ad
    
    Args:
        ad (Ad): Ad instance
    
    Returns:
        float: Conversion rate percentage
    """
    if ad.clicks > 0:
        return (ad.conversions / ad.clicks) * 100
    return 0.0


def get_ad_stats(advertiser):
    """
    Get comprehensive statistics for an advertiser
    
    Args:
        advertiser (User): The advertiser user
    
    Returns:
        dict: Statistics data
    """
    ads = Ad.objects.filter(advertiser=advertiser)
    
    total_ads = ads.count()
    active_ads = ads.filter(status=Ad.STATUS_ACTIVE).count()
    pending_ads = ads.filter(status=Ad.STATUS_PENDING).count()
    rejected_ads = ads.filter(status=Ad.STATUS_REJECTED).count()
    expired_ads = ads.filter(status=Ad.STATUS_EXPIRED).count()
    
    total_impressions = sum(ad.impressions for ad in ads) if ads else 0
    total_clicks = sum(ad.clicks for ad in ads) if ads else 0
    total_conversions = sum(ad.conversions for ad in ads) if ads else 0
    
    total_spent = sum(ad.get_spent() for ad in ads) if ads else 0
    
    return {
        'total_ads': total_ads,
        'active_ads': active_ads,
        'pending_ads': pending_ads,
        'rejected_ads': rejected_ads,
        'expired_ads': expired_ads,
        'total_impressions': total_impressions,
        'total_clicks': total_clicks,
        'total_conversions': total_conversions,
        'total_spent': float(total_spent),
        'click_through_rate': (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
        'conversion_rate': (total_conversions / total_clicks * 100) if total_clicks > 0 else 0,
        'cost_per_click': (total_spent / total_clicks) if total_clicks > 0 else 0,
        'cost_per_impression': (total_spent / total_impressions) if total_impressions > 0 else 0,
    }


def get_ad_performance_data(ad, days=30):
    """
    Get performance data for a specific ad over time
    
    Args:
        ad (Ad): Ad instance
        days (int): Number of days to look back
    
    Returns:
        dict: Performance data
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    
    impressions = AdImpression.objects.filter(
        ad=ad,
        viewed_at__gte=cutoff_date
    )
    
    clicks = AdClick.objects.filter(
        ad=ad,
        clicked_at__gte=cutoff_date
    )
    
    conversions = AdConversion.objects.filter(
        ad=ad,
        converted_at__gte=cutoff_date
    )
    
    daily_data = []
    for i in range(days):
        date = timezone.now() - timezone.timedelta(days=i)
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timezone.timedelta(days=1)
        
        daily_impressions = impressions.filter(viewed_at__range=[start_of_day, end_of_day]).count()
        daily_clicks = clicks.filter(clicked_at__range=[start_of_day, end_of_day]).count()
        daily_conversions = conversions.filter(converted_at__range=[start_of_day, end_of_day]).count()
        
        daily_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'impressions': daily_impressions,
            'clicks': daily_clicks,
            'conversions': daily_conversions,
            'ctr': (daily_clicks / daily_impressions * 100) if daily_impressions > 0 else 0,
        })
    
    return {
        'total_impressions': impressions.count(),
        'total_clicks': clicks.count(),
        'total_conversions': conversions.count(),
        'daily_data': daily_data,
        'overall_ctr': (clicks.count() / impressions.count() * 100) if impressions.count() > 0 else 0,
    }


def get_top_performing_ads(advertiser, limit=5):
    """
    Get top performing ads for an advertiser
    
    Args:
        advertiser (User): The advertiser user
        limit (int): Number of ads to return
    
    Returns:
        QuerySet: Top performing ads
    """
    return Ad.objects.filter(
        advertiser=advertiser,
        status=Ad.STATUS_ACTIVE
    ).order_by('-ctr', '-clicks')[:limit]


def get_ad_by_slug_or_id(identifier):
    """
    Get ad by slug or UUID
    
    Args:
        identifier (str): Ad slug or UUID
    
    Returns:
        Ad: Ad instance or None
    """
    try:
        import uuid
        uuid_obj = uuid.UUID(identifier)
        return Ad.objects.get(id=uuid_obj)
    except (ValueError, AttributeError, Ad.DoesNotExist):
        try:
            return Ad.objects.get(slug=identifier)
        except Ad.DoesNotExist:
            return None


def check_ad_limits(ad):
    """
    Check if ad has reached its limits
    
    Args:
        ad (Ad): Ad instance
    
    Returns:
        dict: Limit status
    """
    now = timezone.now()
    
    result = {
        'is_valid': True,
        'reasons': []
    }
    
    if not ad.is_active:
        result['is_valid'] = False
        result['reasons'].append('Ad is not active')
    
    if ad.status != Ad.STATUS_ACTIVE:
        result['is_valid'] = False
        result['reasons'].append(f"Ad status is {ad.status}")
    
    if ad.end_date and ad.end_date < now:
        result['is_valid'] = False
        result['reasons'].append('Ad has expired')
    
    if ad.max_impressions and ad.impressions >= ad.max_impressions:
        result['is_valid'] = False
        result['reasons'].append('Max impressions reached')
    
    if ad.max_clicks and ad.clicks >= ad.max_clicks:
        result['is_valid'] = False
        result['reasons'].append('Max clicks reached')
    
    return result


def get_category_stats():
    """
    Get statistics for all ad categories
    
    Returns:
        list: Category statistics
    """
    categories = AdCategory.objects.filter(is_active=True)
    result = []
    
    for category in categories:
        ads_count = Ad.objects.filter(category=category).count()
        active_ads = Ad.objects.filter(category=category, status=Ad.STATUS_ACTIVE).count()
        
        result.append({
            'id': str(category.id),
            'name': category.name,
            'total_ads': ads_count,
            'active_ads': active_ads,
            'icon': category.icon,
            'slug': category.slug,
        })
    
    return result


def record_ad_interaction(ad_id, user, interaction_type, **kwargs):
    """
    Record an ad interaction (impression, click, or conversion)
    
    Args:
        ad_id (str): Ad UUID
        user (User): User performing the interaction
        interaction_type (str): Type of interaction
        **kwargs: Additional data
    
    Returns:
        dict: Interaction result
    """
    try:
        ad = Ad.objects.get(id=ad_id)
    except Ad.DoesNotExist:
        return {'success': False, 'error': 'Ad not found'}
    
    if interaction_type == 'impression':
        session_id = kwargs.get('session_id', 'anonymous')
        ip_address = kwargs.get('ip_address', '0.0.0.0')
        user_agent = kwargs.get('user_agent', '')
        
        try:
            impression = ad.record_impression(
                user=user,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            return {'success': True, 'impression_id': str(impression.id)}
        except Exception as e:
            logger.error(f"Error recording impression: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    elif interaction_type == 'click':
        session_id = kwargs.get('session_id', 'anonymous')
        ip_address = kwargs.get('ip_address', '0.0.0.0')
        user_agent = kwargs.get('user_agent', '')
        
        try:
            click = ad.record_click(
                user=user,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            return {'success': True, 'click_id': str(click.id), 'redirect_url': ad.cta_link}
        except Exception as e:
            logger.error(f"Error recording click: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    elif interaction_type == 'conversion':
        session_id = kwargs.get('session_id', 'anonymous')
        conversion_type = kwargs.get('conversion_type', '')
        value = kwargs.get('value', 0)
        
        try:
            conversion = ad.record_conversion(
                user=user,
                session_id=session_id,
                conversion_type=conversion_type,
                value=value
            )
            return {'success': True, 'conversion_id': str(conversion.id)}
        except Exception as e:
            logger.error(f"Error recording conversion: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    return {'success': False, 'error': 'Invalid interaction type'}


def get_user_ad_interactions(user, ad_id=None):
    """
    Get a user's interactions with ads
    
    Args:
        user (User): The user
        ad_id (str): Optional ad ID to filter
    
    Returns:
        dict: User interactions
    """
    result = {
        'impressions': [],
        'clicks': [],
        'conversions': []
    }
    
    if ad_id:
        result['impressions'] = AdImpression.objects.filter(
            user=user,
            ad_id=ad_id
        ).order_by('-viewed_at')
        
        result['clicks'] = AdClick.objects.filter(
            user=user,
            ad_id=ad_id
        ).order_by('-clicked_at')
        
        result['conversions'] = AdConversion.objects.filter(
            user=user,
            ad_id=ad_id
        ).order_by('-converted_at')
    else:
        result['impressions'] = AdImpression.objects.filter(
            user=user
        ).order_by('-viewed_at')
        
        result['clicks'] = AdClick.objects.filter(
            user=user
        ).order_by('-clicked_at')
        
        result['conversions'] = AdConversion.objects.filter(
            user=user
        ).order_by('-converted_at')
    
    return result


def get_available_positions():
    """
    Get all available ad positions
    
    Returns:
        list: Available positions
    """
    return [
        {'value': 'feed', 'label': 'Feed'},
        {'value': 'sidebar', 'label': 'Sidebar'},
        {'value': 'top', 'label': 'Top Banner'},
        {'value': 'bottom', 'label': 'Bottom Banner'},
        {'value': 'popup', 'label': 'Popup'},
        {'value': 'both', 'label': 'Both'},
    ]


def get_ad_types():
    """
    Get all ad types
    
    Returns:
        list: Ad types
    """
    return [
        {'value': 'property', 'label': 'Property'},
        {'value': 'service', 'label': 'Service'},
        {'value': 'promotion', 'label': 'Promotion'},
        {'value': 'event', 'label': 'Event'},
        {'value': 'brand', 'label': 'Brand Awareness'},
        {'value': 'other', 'label': 'Other'},
    ]


def generate_ad_reference():
    """
    Generate a unique ad reference number
    
    Returns:
        str: Unique reference
    """
    import random
    import string
    prefix = 'AD'
    year = timezone.now().strftime('%Y')
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}-{year}-{random_chars}"