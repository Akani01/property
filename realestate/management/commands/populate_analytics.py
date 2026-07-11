# realestate/management/commands/populate_analytics.py
from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone
from datetime import timedelta
from realestate.models import Property, PropertyAnalytics, Booking

class Command(BaseCommand):
    help = 'Populate analytics for existing properties'

    def handle(self, *args, **options):
        self.stdout.write('🔄 Starting analytics population...')
        
        properties = Property.objects.filter(is_active=True)
        total = properties.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('⚠️ No active properties found'))
            return
        
        created_count = 0
        updated_count = 0
        
        for property in properties:
            # Get or create analytics
            analytics, created = PropertyAnalytics.objects.get_or_create(property=property)
            
            if created:
                created_count += 1
            else:
                updated_count += 1
            
            # Update with existing data
            bookings = property.bookings.all()
            
            # Total bookings
            analytics.total_bookings = bookings.count()
            
            # Total views (from property)
            analytics.total_views = property.views_count or 0
            
            # Total revenue
            revenue = bookings.aggregate(total=models.Sum('total_amount'))['total'] or 0
            analytics.total_revenue = revenue
            
            # Last 30 days metrics
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_bookings = bookings.filter(created_at__gte=thirty_days_ago)
            analytics.bookings_last_30_days = recent_bookings.count()
            analytics.revenue_last_30_days = recent_bookings.aggregate(
                total=models.Sum('total_amount')
            )['total'] or 0
            
            # Recent inquiries
            analytics.inquiries_last_30_days = property.inquiries.filter(
                created_at__gte=thirty_days_ago
            ).count()
            
            # Average booking duration
            if analytics.total_bookings > 0:
                total_days = sum((b.check_out - b.check_in).days for b in bookings)
                analytics.average_booking_duration = total_days / analytics.total_bookings
            
            # Reviews
            approved_reviews = property.reviews.filter(is_approved=True)
            analytics.reviews_count = approved_reviews.count()
            
            if approved_reviews.exists():
                avg = approved_reviews.aggregate(avg=models.Avg('overall_rating'))['avg']
                analytics.average_rating = avg or 0
            else:
                analytics.average_rating = 0
            
            analytics.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Successfully populated analytics: {created_count} created, {updated_count} updated'
            )
        )