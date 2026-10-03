from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from ads.models import Ad, AdImpression, AdClick, AdConversion
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update ad statistics from tracking data'

    def handle(self, *args, **options):
        self.stdout.write("Updating ad statistics...")
        
        ads = Ad.objects.all()
        updated_count = 0
        
        for ad in ads:
            try:
                # Get real counts from tracking tables
                impressions = AdImpression.objects.filter(ad=ad).count()
                unique_impressions = AdImpression.objects.filter(ad=ad).values('session_id').distinct().count()
                clicks = AdClick.objects.filter(ad=ad).count()
                unique_clicks = AdClick.objects.filter(ad=ad).values('session_id').distinct().count()
                conversions = AdConversion.objects.filter(ad=ad).count()
                conversion_value = AdConversion.objects.filter(ad=ad).aggregate(Sum('value'))['value__sum'] or 0
                
                # Update ad
                ad.impressions = impressions
                ad.unique_impressions = unique_impressions
                ad.clicks = clicks
                ad.unique_clicks = unique_clicks
                ad.conversions = conversions
                ad.conversion_value = conversion_value
                
                # Update CTR
                if impressions > 0:
                    ad.ctr = (clicks / impressions) * 100
                else:
                    ad.ctr = 0
                
                ad.save(update_fields=[
                    'impressions', 'unique_impressions', 'clicks', 'unique_clicks',
                    'conversions', 'conversion_value', 'ctr', 'updated_at'
                ])
                
                updated_count += 1
                
                if updated_count % 100 == 0:
                    self.stdout.write(f"Updated {updated_count} ads...")
                    
            except Exception as e:
                logger.error(f"Error updating ad {ad.id}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error updating ad {ad.id}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} ads"))