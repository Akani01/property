from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Ad, AdImpression, AdClick, AdConversion
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Ad)
def ad_post_save(sender, instance, created, **kwargs):
    """Handle ad creation and updates"""
    if created:
        # New ad created
        logger.info(f"New ad created: {instance.title} by {instance.advertiser.username}")
        
        # Send notification to admin for approval
        if instance.status == Ad.STATUS_PENDING:
            send_ad_approval_notification(instance)
    
    else:
        # Ad updated
        # Check if status changed to active
        if instance.status == Ad.STATUS_ACTIVE and not instance.is_verified:
            # If an admin manually set to active without approval
            logger.warning(f"Ad {instance.id} set to active without verification")
        
        # Check if status changed to rejected
        if instance.status == Ad.STATUS_REJECTED and instance.review_notes:
            send_ad_rejection_notification(instance)


@receiver(pre_save, sender=Ad)
def ad_pre_save(sender, instance, **kwargs):
    """Validate ad before saving"""
    # Ensure start_date is not in the past for new ads
    if not instance.pk and instance.start_date < timezone.now():
        instance.start_date = timezone.now()


@receiver(post_save, sender=AdImpression)
def impression_post_save(sender, instance, created, **kwargs):
    """Track impression events"""
    if created:
        # Log impression for analytics
        logger.debug(f"Impression recorded for ad {instance.ad_id}")


@receiver(post_save, sender=AdClick)
def click_post_save(sender, instance, created, **kwargs):
    """Track click events"""
    if created:
        logger.debug(f"Click recorded for ad {instance.ad_id}")


@receiver(post_save, sender=AdConversion)
def conversion_post_save(sender, instance, created, **kwargs):
    """Track conversion events"""
    if created:
        logger.debug(f"Conversion recorded for ad {instance.ad_id}")


def send_ad_approval_notification(ad):
    """Send email notification to admins about new ad needing approval"""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        admins = User.objects.filter(is_superuser=True)
        if not admins:
            return
        
        subject = f"New Ad Needs Approval: {ad.title}"
        message = f"""
        A new ad has been created and needs your approval.
        
        Ad Title: {ad.title}
        Advertiser: {ad.advertiser.username}
        Ad Type: {ad.get_ad_type_display()}
        Position: {ad.get_position_display()}
        Price: {ad.get_display_price()}
        
        Please review and approve/reject this ad in the admin panel.
        """
        
        for admin in admins:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [admin.email],
                fail_silently=True,
            )
    except Exception as e:
        logger.error(f"Error sending approval notification: {str(e)}")


def send_ad_rejection_notification(ad):
    """Send email notification to advertiser about ad rejection"""
    try:
        subject = f"Your Ad was Rejected: {ad.title}"
        message = f"""
        Your ad "{ad.title}" has been rejected.
        
        Reason: {ad.review_notes}
        
        If you have any questions, please contact support.
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [ad.advertiser.email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Error sending rejection notification: {str(e)}")