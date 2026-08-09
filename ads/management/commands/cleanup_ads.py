from django.core.management.base import BaseCommand
from django.utils import timezone
from ads.models import Ad
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up expired and old ads'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to keep completed/expired ads (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_date = timezone.now() - timezone.timedelta(days=days)

        self.stdout.write(f"Cleaning up ads older than {days} days...")
        
        # Find ads to clean up
        expired_ads = Ad.objects.filter(
            status__in=[Ad.STATUS_EXPIRED, Ad.STATUS_COMPLETED, Ad.STATUS_DELETED],
            updated_at__lt=cutoff_date
        )
        
        count = expired_ads.count()
        
        if dry_run:
            self.stdout.write(f"Would delete {count} ads (dry run)")
            for ad in expired_ads[:10]:
                self.stdout.write(f"  - {ad.title} ({ad.id})")
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more")
            return

        # Delete them
        deleted_count = 0
        for ad in expired_ads:
            try:
                ad.delete()
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting ad {ad.id}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error deleting ad {ad.id}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} ads"))