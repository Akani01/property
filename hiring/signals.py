# realestate/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Property, PropertyAnalytics

@receiver(post_save, sender=Property)
def create_property_analytics(sender, instance, created, **kwargs):
    """Create analytics record when a new property is created"""
    if created:
        PropertyAnalytics.objects.create(property=instance)

@receiver(post_save, sender=Property)
def update_property_analytics_on_save(sender, instance, **kwargs):
    """Update analytics when property is saved (for existing properties)"""
    # This # realestate/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Property, PropertyAnalytics

@receiver(post_save, sender=Property)
def create_property_analytics(sender, instance, created, **kwargs):
    """Create analytics record when a new property is created"""
    if created:
        PropertyAnalytics.objects.create(property=instance)

@receiver(post_save, sender=Property)
def update_property_analytics_on_save(sender, instance, **kwargs):
    """Update analytics when property is saved (for existing properties)"""
    # This ensures existing properties without analytics get them
    PropertyAnalytics.objects.get_or_create(property=instance)ensures existing properties without analytics get them
    PropertyAnalytics.objects.get_or_create(property=instance)