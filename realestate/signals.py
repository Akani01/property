from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Property, Booking, PropertyAnalytics


@receiver(post_save, sender=Property)
def create_property_analytics(sender, instance, created, **kwargs):
    """Create analytics record when a new property is created"""
    if created:
        PropertyAnalytics.objects.create(property=instance)


@receiver(post_save, sender=Booking)
def update_property_analytics(sender, instance, created, **kwargs):
    """Update property analytics when a booking is created or updated"""
    try:
        analytics = instance.property.analytics
    except PropertyAnalytics.DoesNotExist:
        analytics = PropertyAnalytics.objects.create(property=instance.property)
    
    if created:
        analytics.total_bookings += 1
        analytics.total_revenue += instance.total_amount
        
        # Calculate average occupancy
        properties = Property.objects.filter(
            bookings__status__in=['confirmed', 'checked_in', 'checked_out']
        ).distinct()
        total_properties = Property.objects.filter(is_active=True).count()
        if total_properties > 0:
            analytics.average_occupancy_rate = (properties.count() / total_properties) * 100
        
        analytics.save()
    
    # Update property status if fully booked
    if instance.status in ['confirmed', 'checked_in']:
        property_obj = instance.property
        total_rooms = property_obj.total_rooms or 1
        booked_rooms = property_obj.bookings.filter(
            status__in=['confirmed', 'checked_in'],
            check_in__lte=timezone.now(),
            check_out__gte=timezone.now()
        ).count()
        
        if booked_rooms >= total_rooms:
            property_obj.status = 'booked'
            property_obj.save()