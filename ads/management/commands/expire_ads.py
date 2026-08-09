from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q, F
from ads.models import Ad
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check and expire ads that have reached their end date or limits'

    def handle(self, *args, **options):
        self.stdout.write("Checking for ads to expire...")
        
        now = timezone.now()
        
        # Find ads that need to be expired
        expired_ads = Ad.objects.filter(
            status=Ad.STATUS_ACTIVE,
            is_active=True
        ).filter(
            Q(end_date__lt=now) |
            Q(max_impressions__lte=F('impressions')) |
            Q(max_clicks__lte=F('clicks'))
        )
        
        count = expired_ads.count()
        
        if count == 0:
            self.stdout.write("No ads to expire")
            return
        
        expired_count = 0
        for ad in expired_ads:
            try:
                ad.status = Ad.STATUS_EXPIRED
                ad.is_active = False
                ad.save(update_fields=['status', 'is_active', 'updated_at'])
                expired_count += 1
                
                # Log the expiration reason
                reason = []
                if ad.end_date and ad.end_date < now:
                    reason.append("end date passed")
                if ad.max_impressions and ad.impressions >= ad.max_impressions:
                    reason.append("max impressions reached")
                if ad.max_clicks and ad.clicks >= ad.max_clicks:
                    reason.append("max clicks reached")
                
                self.stdout.write(f"Expired ad: {ad.title} - {', '.join(reason)}")
                
            except Exception as e:
                logger.error(f"Error expiring ad {ad.id}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error expiring ad {ad.id}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Successfully expired {expired_count} ads"))