from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()

class Ad(models.Model):
    """Ad model for sponsored content with full tracking capabilities"""
    
    # Ad Types
    TYPE_PROPERTY = 'property'
    TYPE_SERVICE = 'service'
    TYPE_PROMOTION = 'promotion'
    TYPE_EVENT = 'event'
    TYPE_BRAND = 'brand'
    TYPE_OTHER = 'other'
    
    AD_TYPES = [
        (TYPE_PROPERTY, 'Property'),
        (TYPE_SERVICE, 'Service'),
        (TYPE_PROMOTION, 'Promotion'),
        (TYPE_EVENT, 'Event'),
        (TYPE_BRAND, 'Brand Awareness'),
        (TYPE_OTHER, 'Other'),
    ]
    
    # Status
    STATUS_DRAFT = 'draft'
    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_PAUSED = 'paused'
    STATUS_EXPIRED = 'expired'
    STATUS_REJECTED = 'rejected'
    STATUS_COMPLETED = 'completed'
    STATUS_DELETED = 'deleted'
    
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_PAUSED, 'Paused'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_DELETED, 'Deleted'),
    ]
    
    # Placement
    PLACEMENT_FEED = 'feed'
    PLACEMENT_SIDEBAR = 'sidebar'
    PLACEMENT_TOP = 'top'
    PLACEMENT_BOTTOM = 'bottom'
    PLACEMENT_POPUP = 'popup'
    PLACEMENT_BOTH = 'both'
    
    PLACEMENT_CHOICES = [
        (PLACEMENT_FEED, 'Feed'),
        (PLACEMENT_SIDEBAR, 'Sidebar'),
        (PLACEMENT_TOP, 'Top Banner'),
        (PLACEMENT_BOTTOM, 'Bottom Banner'),
        (PLACEMENT_POPUP, 'Popup'),
        (PLACEMENT_BOTH, 'Both'),
    ]
    
    # Basic Info
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ad_type = models.CharField(max_length=20, choices=AD_TYPES, default=TYPE_PROMOTION)
    
    # Media
    image = models.ImageField(upload_to='ads/%Y/%m/%d/', blank=True, null=True)
    image_url = models.URLField(blank=True, help_text="External image URL if no image uploaded")
    video_url = models.URLField(blank=True, help_text="Video URL (YouTube, Vimeo, etc.)")
    thumbnail_url = models.URLField(blank=True, help_text="Thumbnail for video ads")
    
    # Pricing
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    price_currency = models.CharField(max_length=10, default='ZAR')
    display_price = models.CharField(max_length=100, blank=True, help_text="Custom price display (e.g., 'From R2,500,000')")
    
    # Targeting
    target_audience = models.JSONField(default=dict, blank=True, help_text="Targeting criteria (age, gender, interests, etc.)")
    target_locations = models.JSONField(default=list, blank=True, help_text="List of target locations")
    target_property_types = models.JSONField(default=list, blank=True, help_text="List of property types to target")
    target_user_types = models.JSONField(default=list, blank=True, help_text="List of user types to target")
    target_min_age = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    target_max_age = models.IntegerField(null=True, blank=True, validators=[MaxValueValidator(120)])
    
    # Scheduling
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)
    max_impressions = models.IntegerField(null=True, blank=True, help_text="Maximum number of impressions")
    max_clicks = models.IntegerField(null=True, blank=True, help_text="Maximum number of clicks")
    
    # Budget & Bidding
    budget_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    budget_daily = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    cost_per_click = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_per_impression = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_per_conversion = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Performance
    impressions = models.IntegerField(default=0)
    unique_impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    unique_clicks = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    conversion_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ctr = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Click Through Rate %")
    
    # Placement
    position = models.CharField(max_length=20, choices=PLACEMENT_CHOICES, default=PLACEMENT_FEED)
    priority = models.IntegerField(default=0, help_text="Higher number = higher priority")
    frequency_cap = models.IntegerField(default=0, help_text="Max times per user per day (0 = unlimited)")
    
    # Relationships
    advertiser = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ads')
    property = models.ForeignKey('realestate.Property', on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='ads')
    category = models.ForeignKey('ads.AdCategory', on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='ads')
    
    # Status & Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    # Call to Action
    cta_text = models.CharField(max_length=50, default='Learn More')
    cta_link = models.URLField(blank=True)
    cta_button_color = models.CharField(max_length=20, default='#8a2be2')
    cta_button_text_color = models.CharField(max_length=20, default='#ffffff')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='approved_ads')
    reviewed_at = models.DateTimeField(blank=True, null=True)
    review_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['position', 'priority']),
            models.Index(fields=['advertiser', 'status']),
        ]
        verbose_name = 'Ad'
        verbose_name_plural = 'Ads'
    
    def __str__(self):
        return f"{self.title} - {self.advertiser.username}"
    
    def is_valid(self):
        """Check if ad is currently valid/active"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.status != self.STATUS_ACTIVE:
            return False
        if self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        if self.max_impressions and self.impressions >= self.max_impressions:
            return False
        if self.max_clicks and self.clicks >= self.max_clicks:
            return False
        return True
    
    def get_display_price(self):
        """Get display price"""
        if self.display_price:
            return self.display_price
        if self.price:
            return f"{self.price_currency} {self.price:,.0f}"
        return "Contact for Price"
    
    def record_impression(self, user=None, session_id=None, ip_address=None, user_agent=None):
        """Record an ad impression"""
        self.impressions += 1
        
        # Check if this is a unique impression
        if user and user.is_authenticated:
            if not AdImpression.objects.filter(ad=self, user=user).exists():
                self.unique_impressions += 1
        elif session_id:
            if not AdImpression.objects.filter(ad=self, session_id=session_id).exists():
                self.unique_impressions += 1
        
        self.save(update_fields=['impressions', 'unique_impressions'])
        
        # Create impression record
        return AdImpression.objects.create(
            ad=self,
            user=user,
            session_id=session_id or 'anonymous',
            ip_address=ip_address,
            user_agent=user_agent or ''
        )
    
    def record_click(self, user=None, session_id=None, ip_address=None, user_agent=None):
        """Record an ad click"""
        self.clicks += 1
        
        # Check if this is a unique click
        if user and user.is_authenticated:
            if not AdClick.objects.filter(ad=self, user=user).exists():
                self.unique_clicks += 1
        elif session_id:
            if not AdClick.objects.filter(ad=self, session_id=session_id).exists():
                self.unique_clicks += 1
        
        # Update CTR
        if self.impressions > 0:
            self.ctr = (self.clicks / self.impressions) * 100
        
        self.save(update_fields=['clicks', 'unique_clicks', 'ctr'])
        
        # Create click record
        return AdClick.objects.create(
            ad=self,
            user=user,
            session_id=session_id or 'anonymous',
            ip_address=ip_address,
            user_agent=user_agent or ''
        )
    
    def record_conversion(self, user=None, session_id=None, conversion_type='', value=0):
        """Record a conversion"""
        self.conversions += 1
        self.conversion_value += value
        self.save(update_fields=['conversions', 'conversion_value'])
        
        return AdConversion.objects.create(
            ad=self,
            user=user,
            session_id=session_id or 'anonymous',
            conversion_type=conversion_type,
            value=value
        )
    
    def get_ctr_percentage(self):
        """Get CTR as percentage string"""
        if self.impressions == 0:
            return "0.00%"
        return f"{(self.clicks / self.impressions * 100):.2f}%"
    
    def get_spent(self):
        """Calculate total spent on this ad"""
        return self.clicks * self.cost_per_click + self.impressions * self.cost_per_impression
    
    def get_remaining_budget(self):
        """Get remaining budget"""
        return self.budget_total - self.get_spent()


class AdCategory(models.Model):
    """Category for ads"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Ad Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class AdImpression(models.Model):
    """Track individual ad impressions for analytics"""
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='impression_records')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['ad', 'viewed_at']),
            models.Index(fields=['session_id']),
            models.Index(fields=['user', 'viewed_at']),
        ]
        ordering = ['-viewed_at']
    
    def __str__(self):
        return f"Impression on {self.ad.title} at {self.viewed_at}"


class AdClick(models.Model):
    """Track ad clicks"""
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='click_records')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    clicked_at = models.DateTimeField(auto_now_add=True)
    converted = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['ad', 'clicked_at']),
            models.Index(fields=['session_id']),
            models.Index(fields=['user', 'clicked_at']),
        ]
        ordering = ['-clicked_at']
    
    def __str__(self):
        return f"Click on {self.ad.title} at {self.clicked_at}"


class AdConversion(models.Model):
    """Track conversions from ads"""
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='conversion_records')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100, db_index=True)
    conversion_type = models.CharField(max_length=50, blank=True)
    value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    converted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['ad', 'converted_at']),
            models.Index(fields=['session_id']),
        ]
        ordering = ['-converted_at']
    
    def __str__(self):
        return f"Conversion on {self.ad.title} at {self.converted_at}"


class AdSchedule(models.Model):
    """Advanced scheduling for ads"""
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=[
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), 
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['ad', 'day_of_week']
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.ad.title} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class AdTargetingRule(models.Model):
    """Advanced targeting rules for ads"""
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='targeting_rules')
    rule_type = models.CharField(max_length=50, choices=[
        ('location', 'Location'),
        ('property_type', 'Property Type'),
        ('user_type', 'User Type'),
        ('interest', 'Interest'),
        ('behavior', 'Behavior'),
        ('custom', 'Custom'),
    ])
    operator = models.CharField(max_length=20, choices=[
        ('equals', 'Equals'),
        ('contains', 'Contains'),
        ('starts_with', 'Starts With'),
        ('ends_with', 'Ends With'),
        ('in', 'In List'),
        ('not_in', 'Not In List'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
        ('between', 'Between'),
    ])
    value = models.JSONField(help_text="Rule value(s)")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.ad.title} - {self.rule_type} {self.operator} {self.value}"