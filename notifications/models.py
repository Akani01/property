from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
import re
from django.core.cache import cache

User = get_user_model()


class Notification(models.Model):
    """Unified notification system for all apps"""
    
    NOTIFICATION_TYPES = (
        # Hiring app events
        ('job_application', 'Job Application'),
        ('job_alert', 'Job Alert'),
        ('post_like', 'Post Like'),
        ('post_comment', 'Post Comment'),
        ('comment_reply', 'Comment Reply'),
        ('mention', 'Mention'),
        ('follow', 'Follow'),
        ('connection_request', 'Connection Request'),
        ('profile_view', 'Profile View'),
        
        # RealEstate app events
        ('property_created', 'Property Created'),
        ('property_updated', 'Property Updated'),
        ('property_booked', 'Property Booked'),
        ('property_inquiry', 'Property Inquiry'),
        ('property_review', 'Property Review'),
        ('property_wishlist', 'Property Wishlist'),
        ('property_status_change', 'Property Status Change'),
        ('maintenance_request', 'Maintenance Request'),
        ('maintenance_update', 'Maintenance Update'),
        ('booking_confirmation', 'Booking Confirmation'),
        ('booking_cancellation', 'Booking Cancellation'),
        ('room_available', 'Room Available'),
        
        # Bursary/Education
        ('bursary', 'Bursary Update'),
        ('university', 'University Update'),
        ('school', 'School Update'),
        ('application', 'Application Update'),
        
        # System
        ('system', 'System Notification'),
        ('message', 'Message'),
        ('reminder', 'Reminder'),
        ('newsletter', 'Newsletter'),
        ('promotion', 'Promotion'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core fields - UNIQUE related_name to avoid conflicts
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notification_recipient'  # Changed from 'notifications'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_sender'  # Changed from 'sent_notifications'
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='system')
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    formatted_message = models.TextField(blank=True, null=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    is_clicked = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    
    # Action
    action_url = models.CharField(max_length=500, blank=True, null=True)
    action_label = models.CharField(max_length=100, blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    
    # Media
    image_url = models.CharField(max_length=500, blank=True, null=True)
    
    # Priority
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Reference to related objects (using string references for cross-app compatibility)
    # Hiring app references - UNIQUE related_name
    applicant_profile = models.ForeignKey(
        'hiring.ApplicantProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_related_hiring'
    )
    business_profile = models.ForeignKey(
        'hiring.BusinessProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_related_hiring'
    )
    job = models.ForeignKey(
        'hiring.JobListing', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_related_hiring'
    )
    application = models.ForeignKey(
        'hiring.Application', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_related_hiring'
    )
    post = models.ForeignKey(
        'hiring.Post', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_related_hiring'
    )
    comment = models.ForeignKey(
        'hiring.Comment', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_related_hiring'
    )
    
    # RealEstate app references - UNIQUE related_name
    property_ref = models.ForeignKey(
        'realestate.Property', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_related_realestate'
    )
    booking = models.ForeignKey(
        'realestate.Booking', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_related_realestate'
    )
    room = models.ForeignKey(
        'realestate.Room', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_related_realestate'
    )
    maintenance = models.ForeignKey(
        'realestate.MaintenanceRequest', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_related_realestate'
    )
    
    # Bursary/Education references
    bursary_id = models.CharField(max_length=100, blank=True, null=True)
    university_id = models.CharField(max_length=100, blank=True, null=True)
    school_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional data")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notification_records'  # Changed from 'notifications' to avoid conflict
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
            cache.delete(f"notif_unread_{self.recipient_id}")
    
    def mark_as_unread(self):
        """Mark notification as unread"""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_clicked(self):
        """Mark notification as clicked"""
        self.is_clicked = True
        self.save(update_fields=['is_clicked'])
    
    def dismiss(self):
        """Dismiss notification"""
        self.is_dismissed = True
        self.dismissed_at = timezone.now()
        self.save(update_fields=['is_dismissed', 'dismissed_at'])
    
    def get_formatted_message(self):
        """Return message with bold and italic formatting"""
        if self.formatted_message:
            return self.formatted_message
        # Convert **text** to <strong>text</strong>
        formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', self.message)
        # Convert *text* to <em>text</em>
        formatted = re.sub(r'\*(.*?)\*', r'<em>\1</em>', formatted)
        # Convert links
        formatted = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', formatted)
        return formatted
    
    def get_icon_class(self):
        """Get icon class based on notification type"""
        icons = {
            # Hiring
            'job_application': 'fas fa-briefcase',
            'job_alert': 'fas fa-bell',
            'post_like': 'fas fa-heart',
            'post_comment': 'fas fa-comment',
            'comment_reply': 'fas fa-reply',
            'mention': 'fas fa-at',
            'follow': 'fas fa-user-plus',
            'connection_request': 'fas fa-handshake',
            'profile_view': 'fas fa-eye',
            
            # RealEstate
            'property_created': 'fas fa-home',
            'property_updated': 'fas fa-edit',
            'property_booked': 'fas fa-calendar-check',
            'property_inquiry': 'fas fa-question-circle',
            'property_review': 'fas fa-star',
            'property_wishlist': 'fas fa-heart',
            'property_status_change': 'fas fa-exchange-alt',
            'maintenance_request': 'fas fa-tools',
            'maintenance_update': 'fas fa-wrench',
            'booking_confirmation': 'fas fa-check-circle',
            'booking_cancellation': 'fas fa-times-circle',
            'room_available': 'fas fa-door-open',
            
            # Bursary/Education
            'bursary': 'fas fa-graduation-cap',
            'university': 'fas fa-university',
            'school': 'fas fa-school',
            'application': 'fas fa-file-alt',
            
            # System
            'system': 'fas fa-bell',
            'message': 'fas fa-envelope',
            'reminder': 'fas fa-clock',
            'newsletter': 'fas fa-newspaper',
            'promotion': 'fas fa-tag',
        }
        return icons.get(self.notification_type, 'fas fa-bell')
    
    def get_color(self):
        """Get color based on notification type"""
        colors = {
            'job_application': '#7b1fa2',
            'job_alert': '#0d6efd',
            'post_like': '#dc3545',
            'post_comment': '#0d6efd',
            'comment_reply': '#6c757d',
            'mention': '#fd7e14',
            'follow': '#28a745',
            'connection_request': '#20c997',
            'profile_view': '#17a2b8',
            
            'property_created': '#3f51b5',
            'property_updated': '#ff9800',
            'property_booked': '#e91e63',
            'property_inquiry': '#ffc107',
            'property_review': '#ff6b6b',
            'property_wishlist': '#e91e63',
            'property_status_change': '#6f42c1',
            'maintenance_request': '#fd7e14',
            'maintenance_update': '#20c997',
            'booking_confirmation': '#28a745',
            'booking_cancellation': '#dc3545',
            'room_available': '#17a2b8',
            
            'bursary': '#4caf50',
            'university': '#3f51b5',
            'school': '#ff9800',
            'application': '#0d6efd',
            
            'system': '#6c757d',
            'message': '#0d6efd',
            'reminder': '#ffc107',
            'newsletter': '#6c757d',
            'promotion': '#e83e8c',
        }
        return colors.get(self.notification_type, '#6c757d')
    
    # Helper methods
    def get_property(self):
        """Get the related property"""
        return self.property_ref
    
    def get_property_id(self):
        """Get property ID"""
        return self.property_ref.id if self.property_ref else None
    
    def get_property_title(self):
        """Get property title"""
        return self.property_ref.title if self.property_ref else None
    
    def get_job_id(self):
        """Get job ID"""
        return self.job.id if self.job else None
    
    def get_job_title(self):
        """Get job title"""
        return self.job.title if self.job else None
    
    def get_booking_id(self):
        """Get booking ID"""
        return self.booking.id if self.booking else None
    
    def get_maintenance_id(self):
        """Get maintenance ID"""
        return self.maintenance.id if self.maintenance else None
    
    def get_post_id(self):
        """Get post ID"""
        return self.post.id if self.post else None
    
    @property
    def time_ago(self):
        """Get human-readable time ago"""
        if not self.created_at:
            return "Just now"
        diff = timezone.now() - self.created_at
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"


class NotificationPreference(models.Model):
    """User notification preferences"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='notification_pref'  # Unique related_name
    )
    
    # Email preferences
    email_notifications = models.BooleanField(default=True)
    email_application_updates = models.BooleanField(default=True)
    email_bursary_updates = models.BooleanField(default=True)
    email_university_updates = models.BooleanField(default=True)
    email_school_updates = models.BooleanField(default=True)
    email_job_alerts = models.BooleanField(default=True)
    email_property_updates = models.BooleanField(default=True)
    
    # In-app preferences
    in_app_notifications = models.BooleanField(default=True)
    in_app_application_updates = models.BooleanField(default=True)
    in_app_bursary_updates = models.BooleanField(default=True)
    in_app_university_updates = models.BooleanField(default=True)
    in_app_school_updates = models.BooleanField(default=True)
    in_app_job_alerts = models.BooleanField(default=True)
    in_app_property_updates = models.BooleanField(default=True)
    
    # Push notifications
    push_notifications = models.BooleanField(default=False)
    
    # Sound preferences
    sound_enabled = models.BooleanField(default=True)
    sound_volume = models.IntegerField(default=70, help_text="Volume percentage 0-100")
    selected_sound = models.CharField(max_length=50, default='default', choices=[
        ('default', 'Default'),
        ('gentle', 'Gentle'),
        ('pop', 'Pop'),
        ('chime', 'Chime'),
        ('bell', 'Bell'),
        ('none', 'None'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_pref_records'  # Unique table name
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.username}"


class NotificationLog(models.Model):
    """Log of sent notifications"""
    DELIVERY_CHANNELS = (
        ('email', 'Email'),
        ('in_app', 'In-App'),
        ('push', 'Push Notification'),
        ('sms', 'SMS'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    notification = models.ForeignKey(
        Notification, 
        on_delete=models.CASCADE, 
        related_name='logs'
    )
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notification_logs'
    )
    channel = models.CharField(max_length=10, choices=DELIVERY_CHANNELS, default='in_app')
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'notification_log_records'  # Unique table name
        ordering = ['-sent_at']
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        indexes = [
            models.Index(fields=['recipient', '-sent_at']),
        ]
    
    def __str__(self):
        return f"{self.notification.title} - {self.recipient.username} ({self.get_channel_display()})"


class NotificationDevice(models.Model):
    """User devices for push notifications"""
    DEVICE_TYPES = (
        ('web', 'Web Browser'),
        ('mobile', 'Mobile App'),
        ('tablet', 'Tablet'),
        ('desktop', 'Desktop'),
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notification_devices'
    )
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, default='web')
    device_id = models.CharField(max_length=255, unique=True)
    registration_token = models.CharField(max_length=500)
    endpoint = models.URLField(max_length=500, blank=True, null=True)
    p256dh = models.CharField(max_length=255, blank=True, null=True)
    auth = models.CharField(max_length=255, blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notification_device_records'  # Unique table name
    
    def __str__(self):
        return f"{self.user.username} - {self.device_type}"


class NotificationSound(models.Model):
    """User notification sound preferences (kept for backward compatibility)"""
    SOUND_CHOICES = (
        ('default', 'Default'),
        ('gentle', 'Gentle'),
        ('pop', 'Pop'),
        ('chime', 'Chime'),
        ('bell', 'Bell'),
        ('none', 'None'),
    )
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='notification_sound_pref'
    )
    sound_enabled = models.BooleanField(default=True)
    sound_volume = models.IntegerField(default=70, help_text="Volume percentage 0-100")
    selected_sound = models.CharField(max_length=50, default='default', choices=SOUND_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_sound_records'  # Unique table name
    
    def __str__(self):
        return f"{self.user.username} - Sound: {self.selected_sound}"