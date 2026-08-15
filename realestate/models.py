from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
import random
import string
from decimal import Decimal
from django.db.models import Func, Value, CharField
from django.db.models.functions import Length

User = get_user_model()

# Import from hiring app if exists
try:
    from hiring.models import BusinessProfile, CustomUser, ApplicantProfile
except ImportError:
    # Fallback if hiring app not yet created
    BusinessProfile = models.Model
    CustomUser = User
    ApplicantProfile = models.Model

# ============================================
# COUNTRY MODEL - Global Support
# ============================================


class Country(models.Model):
    """Country model with calling codes for smart phone detection"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=2, unique=True)
    code3 = models.CharField(max_length=3, blank=True)
    calling_code = models.CharField(max_length=10, unique=True)
    flag = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['name']
        indexes = [
            models.Index(fields=['calling_code']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"{self.name} (+{self.calling_code})"
    
    @classmethod
    def detect_country(cls, phone_number):
        """Detect country from phone number by calling code"""
        if not phone_number:
            return None
        
        # Clean the number
        cleaned = ''.join(filter(str.isdigit, phone_number))
        if not cleaned:
            return None
        
        # Get all active countries and annotate with length
        from django.db.models import CharField, Value
        from django.db.models.functions import Length
        
        countries = cls.objects.filter(is_active=True).annotate(
            code_length=Length('calling_code')
        ).order_by('-code_length')
        
        # Try to match calling code
        for country in countries:
            if cleaned.startswith(country.calling_code):
                return country
        
        return None

# ============================================
# 1. DYNAMIC CATEGORY MANAGEMENT
# ============================================

class PropertyCategory(models.Model):
    """Dynamic categories - users can add their own"""
    CATEGORY_TYPES = (
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('hospitality', 'Hospitality'),
        ('industrial', 'Industrial'),
        ('student_housing', 'Student Housing'),
        ('retail', 'Retail'),
        ('entertainment', 'Entertainment'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=100, unique=True)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, default='other')
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class")
    custom_fields = models.JSONField(default=dict, blank=True, help_text="Custom fields for this category")
    is_system = models.BooleanField(default=False, help_text="System default category")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['name']
        verbose_name_plural = 'Property Categories'
    
    def __str__(self):
        return self.name


class PropertyType(models.Model):
    """Dynamic property types with size classifications"""
    SIZE_CLASSIFICATIONS = (
        ('micro', 'Micro (Student Room/Single Room)'),
        ('small', 'Small (1-3 Bedrooms)'),
        ('medium', 'Medium (4-6 Bedrooms)'),
        ('large', 'Large (7-15 Bedrooms)'),
        ('extra_large', 'Extra Large (15+ Rooms/Mall/Hotel)'),
        ('complex', 'Complex (Multi-building/Estate)'),
        ('commercial', 'Commercial Building'),
        ('other', 'Other'),
    )
    
    BOOKING_PERIOD_CHOICES = (
        ('hour', 'Hours'),
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
        ('flexible', 'Flexible'),
    )
    
    name = models.CharField(max_length=100)
    category = models.ForeignKey(PropertyCategory, on_delete=models.PROTECT, related_name='property_types')
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    size_classification = models.CharField(max_length=20, choices=SIZE_CLASSIFICATIONS, default='small')
    
    # Flags
    is_commercial = models.BooleanField(default=False)
    is_residential = models.BooleanField(default=True)
    is_hospitality = models.BooleanField(default=False)
    is_student_housing = models.BooleanField(default=False)
    
    # Capacity
    min_occupancy = models.PositiveIntegerField(default=1)
    max_occupancy = models.PositiveIntegerField(default=2)
    min_booking_duration = models.PositiveIntegerField(default=1)
    max_booking_duration = models.PositiveIntegerField(null=True, blank=True)
    booking_period = models.CharField(max_length=10, choices=BOOKING_PERIOD_CHOICES, default='day')
    
    # Pricing model
    PRICING_MODELS = (
        ('fixed', 'Fixed Price'),
        ('dynamic', 'Dynamic Pricing'),
        ('seasonal', 'Seasonal Pricing'),
        ('negotiable', 'Negotiable'),
        ('per_person', 'Per Person'),
        ('per_unit', 'Per Unit'),
        ('per_sqm', 'Per Square Meter'),
        ('custom', 'Custom Pricing'),
    )
    pricing_model = models.CharField(max_length=20, choices=PRICING_MODELS, default='fixed')
    
    # Custom attributes
    custom_attributes = models.JSONField(default=dict, blank=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['name']
        unique_together = ['name', 'category']
    
    def __str__(self):
        return f"{self.name} ({self.get_size_classification_display()})"


class PropertyFeature(models.Model):
    """Dynamic features - can be created by users"""
    FEATURE_CATEGORIES = (
        ('amenity', 'Amenity'),
        ('facility', 'Facility'),
        ('safety', 'Safety'),
        ('utility', 'Utility'),
        ('entertainment', 'Entertainment'),
        ('accessibility', 'Accessibility'),
        ('business', 'Business'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=20, choices=FEATURE_CATEGORIES, default='other')
    is_custom = models.BooleanField(default=False, help_text="User-created feature")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['name']
    
    def __str__(self):
        return self.name


# ============================================
# 2. MAIN PROPERTY MODEL
# ============================================

class Property(models.Model):
    """Main property model supporting all types from student rooms to malls"""
    
    LISTING_TYPES = (
        ('sale', 'For Sale'),
        ('rent', 'For Rent'),
        ('lease', 'For Lease'),
        ('booking', 'For Booking'),
        ('event', 'For Events'),
        ('auction', 'Auction'),
    )
    
    TRANSACTION_TYPES = (
        ('sale', 'Sale'),
        ('rental', 'Rental'),
        ('lease', 'Lease'),
        ('booking', 'Booking'),
        ('event_rental', 'Event Rental'),
        ('auction', 'Auction'),
        ('timeshare', 'Timeshare'),
    )
    
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance'),
        ('coming_soon', 'Coming Soon'),
        ('closed', 'Closed'),
        ('sold', 'Sold'),
        ('rented', 'Rented'),
    )
    
    BOOKING_MODES = (
        ('instant', 'Instant Booking'),
        ('scheduled', 'Scheduled Booking'),
        ('on_demand', 'On-Demand'),
        ('subscription', 'Subscription'),
        ('traditional', 'Traditional Booking'),
    )
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property_reference = models.CharField(max_length=50, unique=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Categorization
    property_type = models.ForeignKey(PropertyType, on_delete=models.PROTECT, related_name='properties')
    custom_category_name = models.CharField(max_length=100, blank=True, help_text="If property type not available")
    custom_category_description = models.TextField(blank=True)
    features = models.ManyToManyField(PropertyFeature, related_name='properties', blank=True)
    
    # Location
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='South Africa')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Google Maps integration
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    formatted_address = models.TextField(blank=True)
    place_id = models.CharField(max_length=255, blank=True)
    neighborhood = models.CharField(max_length=100, blank=True)
    landmark = models.CharField(max_length=200, blank=True)
    map_zoom_level = models.PositiveIntegerField(default=15)
    location_data = models.JSONField(default=dict, blank=True)
    
    # Size & Capacity
    total_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Total area in sq meters")
    land_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Land area in sq meters")
    floor_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Floor area in sq meters")
    total_rooms = models.PositiveIntegerField(default=1, help_text="Total number of rooms/units")
    total_floors = models.PositiveIntegerField(default=1)
    max_occupancy = models.PositiveIntegerField(default=1, help_text="Maximum people that can occupy")
    
    # Rooms/Units count by type
    room_count = models.JSONField(default=dict, blank=True, help_text="Count by room type")
    
    # Specifications
    bedrooms = models.PositiveIntegerField(default=0)
    bathrooms = models.PositiveIntegerField(default=0)
    garages = models.PositiveIntegerField(default=0)
    parking_spaces = models.PositiveIntegerField(default=0)
    
    # Amenities & Features
    amenities = models.JSONField(default=list, blank=True)
    
    # Pricing
    base_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Base price for booking/rent/sale")
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Price per room/unit")
    price_per_sqm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_currency = models.CharField(max_length=3, default='ZAR')
    
    # Booking specific
    BOOKING_UNITS = (
        ('hour', 'Per Hour'),
        ('day', 'Per Day'),
        ('week', 'Per Week'),
        ('month', 'Per Month'),
        ('year', 'Per Year'),
    )
    booking_unit = models.CharField(max_length=10, choices=BOOKING_UNITS, default='day')
    
    # Pricing Structures
    PRICING_STRUCTURES = (
        ('fixed', 'Fixed Price'),
        ('tiered', 'Tiered Pricing'),
        ('dynamic', 'Dynamic Pricing'),
        ('negotiable', 'Negotiable'),
        ('per_person', 'Per Person'),
        ('per_night', 'Per Night'),
    )
    pricing_structure = models.CharField(max_length=20, choices=PRICING_STRUCTURES, default='fixed')
    pricing_details = models.JSONField(default=dict, blank=True, help_text="Tiered or dynamic pricing details")
    
    # Listing Details
    listing_type = models.CharField(max_length=10, choices=LISTING_TYPES, default='booking')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='booking')
    listing_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    # Property status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    
    # Booking availability
    is_bookable = models.BooleanField(default=True)
    booking_mode = models.CharField(max_length=20, choices=BOOKING_MODES, default='traditional')
    available_from = models.DateField(null=True, blank=True)
    available_until = models.DateField(null=True, blank=True)
    minimum_stay = models.PositiveIntegerField(default=1, help_text="Minimum stay in booking_unit")
    maximum_stay = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum stay in booking_unit")
    
    # Management & Ownership
    owner = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_properties')
    listing_agent = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='listed_properties')
    company = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='properties', null=True, blank=True)
    
    # Real-time tracking (OPTIONAL - for on-demand booking)
    is_online = models.BooleanField(default=False, help_text="Property is currently available for instant booking")
    last_heartbeat = models.DateTimeField(null=True, blank=True, help_text="Last time property sent heartbeat signal")
    current_occupancy = models.PositiveIntegerField(default=0, help_text="Current number of people in property")
    max_capacity = models.PositiveIntegerField(default=1, help_text="Maximum capacity")
    agent_status = models.CharField(max_length=20, choices=[
        ('available', 'Available'),
        ('on_route', 'On Route'),
        ('booked', 'Booked'),
        ('offline', 'Offline'),
    ], default='offline')
    assigned_agent = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_properties')
    
    # Media
    main_image = models.ImageField(
        upload_to='properties/main/%Y/%m/%d/',
        null=True, blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]
    )
    virtual_tour_url = models.URLField(blank=True, help_text="Virtual tour link (YouTube, Matterport, etc.)")
    additional_images = models.JSONField(default=list, blank=True)
    
    # Marketing
    is_featured = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Custom fields
    custom_fields = models.JSONField(default=dict, blank=True, help_text="Additional custom fields")
     
    # Interaction counters
    likes_count = models.PositiveIntegerField(default=0, help_text="Number of likes")
    dislikes_count = models.PositiveIntegerField(default=0, help_text="Number of dislikes")
    
    # Rating fields
    average_rating = models.FloatField(default=0.0, help_text="Average rating (1-5 stars)")
    rating_count = models.PositiveIntegerField(default=0, help_text="Number of ratings")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['city', 'country']),
            models.Index(fields=['base_price']),
            models.Index(fields=['listing_type']),
            models.Index(fields=['status']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['is_active']),
            models.Index(fields=['property_type']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.company.company_name if self.company else 'No Company'}"
    
    # ============================================
    # ✅ FIXED SAVE METHOD - KEEPS YOUR ORIGINAL
    # ============================================
    def save(self, *args, **kwargs):
        if not self.property_reference:
            year = timezone.now().year
            random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.property_reference = f"PROP-{year}-{random_chars}"
        
        # ✅ AUTO-GEOCODE IF ADDRESS EXISTS BUT NO COORDINATES
        if self.address and (not self.latitude or not self.longitude):
            self.geocode_address()
        
        super().save(*args, **kwargs)
    
    # ============================================
    # ✅ GEOCODING METHOD - NEW
    # ============================================
    def geocode_address(self):
        """Convert address to latitude/longitude automatically"""
        from django.conf import settings
        
        google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        
        if not google_api_key:
            print("⚠️ Google Maps API key not configured for geocoding")
            return
        
        # Build full address
        address_parts = [
            self.address,
            self.city,
            self.state,
            self.country,
            self.postal_code
        ]
        full_address = ', '.join([p for p in address_parts if p])
        
        if not full_address:
            return
        
        try:
            import requests
            url = f'https://maps.googleapis.com/maps/api/geocode/json?address={requests.utils.quote(full_address)}&key={google_api_key}'
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                self.latitude = location['lat']
                self.longitude = location['lng']
                self.formatted_address = data['results'][0]['formatted_address']
                self.place_id = data['results'][0]['place_id']
                print(f"✅ Geocoded: {self.title} → {self.latitude}, {self.longitude}")
            else:
                print(f"❌ Geocoding failed for: {full_address}")
        except Exception as e:
            print(f"❌ Geocoding error: {e}")
    
    def get_main_image_url(self):
        if self.main_image:
            return self.main_image.url
        return '/static/realestate/images/default-property.jpg'
    
    def get_custom_category(self):
        if self.custom_category_name:
            return self.custom_category_name
        return self.property_type.name if self.property_type else "Uncategorized"
    
    @property
    def is_available_for_instant_booking(self):
        return self.is_online and self.status == 'available' and self.agent_status == 'available'


# ============================================================
# PROPERTY INTERACTION
# ============================================================

class PropertyInteraction(models.Model):
    """Track likes, dislikes for properties"""
    INTERACTION_TYPES = (
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='interactions')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='property_interactions')
    interaction_type = models.CharField(max_length=10, choices=INTERACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        unique_together = ['property', 'user', 'interaction_type']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} {self.interaction_type}s {self.property.title}"


# ============================================================
# PROPERTY RATING
# ============================================================

class PropertyRating(models.Model):
    """Property ratings (1-5 stars)"""
    RATING_CHOICES = [
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_ratings')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='property_ratings')
    rating = models.IntegerField(choices=RATING_CHOICES)
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        unique_together = ['property', 'user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} rated {self.property.title} {self.rating}★"


# ============================================
# 3. ROOM/UNIT MANAGEMENT
# ============================================

class Room(models.Model):
    """Individual rooms/units within a property"""
    
    ROOM_TYPES = (
        ('single', 'Single Room'),
        ('double', 'Double Room'),
        ('twin', 'Twin Room'),
        ('triple', 'Triple Room'),
        ('suite', 'Suite'),
        ('studio', 'Studio'),
        ('apartment', 'Apartment Unit'),
        ('office', 'Office Space'),
        ('retail', 'Retail Unit'),
        ('warehouse', 'Warehouse Unit'),
        ('storage', 'Storage Unit'),
        ('common', 'Common Area'),
        ('meeting', 'Meeting Room'),
        ('conference', 'Conference Room'),
        ('function', 'Function Room'),
        ('dormitory', 'Dormitory'),
        ('other', 'Other'),
    )
    
    ROOM_STATUS = (
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('maintenance', 'Under Maintenance'),
        ('cleaning', 'Being Cleaned'),
        ('closed', 'Closed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='rooms')
    
    # Room Details
    room_number = models.CharField(max_length=20, blank=True)
    room_name = models.CharField(max_length=100, blank=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='single')
    custom_room_type = models.CharField(max_length=100, blank=True)
    room_status = models.CharField(max_length=20, choices=ROOM_STATUS, default='available')
    
    # Capacity
    capacity = models.PositiveIntegerField(default=1)
    bed_count = models.PositiveIntegerField(default=1)
    bed_types = models.JSONField(default=list, blank=True, help_text="Types of beds available")
    
    # Size
    size_sq_meters = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Pricing (override property pricing)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_per_week = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    custom_pricing = models.JSONField(default=dict, blank=True)
    
    # Amenities specific to this room
    amenities = models.JSONField(default=list, blank=True)
    
    # Features
    has_private_bathroom = models.BooleanField(default=False)
    has_kitchenette = models.BooleanField(default=False)
    has_balcony = models.BooleanField(default=False)
    has_ac = models.BooleanField(default=False)
    has_heating = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=True)
    has_tv = models.BooleanField(default=False)
    has_safe = models.BooleanField(default=False)
    is_accessible = models.BooleanField(default=False, help_text="Wheelchair accessible")
    has_window = models.BooleanField(default=True)
    
    # Room specific images
    room_image = models.ImageField(
        upload_to='rooms/%Y/%m/%d/',
        null=True, blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]
    )
    additional_images = models.JSONField(default=list, blank=True)
    
    # Description
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Availability
    is_active = models.BooleanField(default=True)
    available_from = models.DateField(null=True, blank=True)
    available_until = models.DateField(null=True, blank=True)
    
    # Custom fields
    custom_fields = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['room_number', 'room_type']
        unique_together = ['property', 'room_number']
    
    def __str__(self):
        return f"{self.room_number or self.room_name} - {self.get_room_type_display()}"


# ============================================
# 4. BOOKING SYSTEM
# ============================================

class Booking(models.Model):
    """Booking system supporting both traditional and on-demand booking"""
    
    BOOKING_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_reference = models.CharField(max_length=50, unique=True, editable=False)
    
    # Booking details
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    
    # Guest/Customer
    guest = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bookings')
    guest_details = models.JSONField(default=dict, blank=True, help_text="Guest information if not user")
    
    # Business/Company booking
    business = models.ForeignKey(BusinessProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    
    # Booking period
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    actual_check_in = models.DateTimeField(null=True, blank=True)
    actual_check_out = models.DateTimeField(null=True, blank=True)
    duration_days = models.PositiveIntegerField(default=1)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    taxes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='ZAR')
    
    # Payment
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Booking status
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='pending')
    number_of_guests = models.PositiveIntegerField(default=1)
    guest_names = models.JSONField(default=list, blank=True)
    special_requests = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Booking mode
    booking_mode = models.CharField(max_length=20, choices=Property.BOOKING_MODES, default='traditional')
    
    # Real-time tracking (OPTIONAL - for on-demand booking)
    assigned_driver = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bookings')
    driver_status = models.CharField(max_length=20, choices=[
        ('arriving', 'Arriving'),
        ('waiting', 'Waiting for Guest'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='arriving', blank=True)
    pickup_location = models.JSONField(default=dict, blank=True)
    dropoff_location = models.JSONField(default=dict, blank=True)
    current_location = models.JSONField(default=dict, blank=True)
    route_path = models.JSONField(default=list, blank=True, help_text="GPS route points")
    estimated_pickup_time = models.DateTimeField(null=True, blank=True)
    actual_pickup_time = models.DateTimeField(null=True, blank=True)
    trip_duration = models.PositiveIntegerField(default=0, help_text="Trip duration in minutes")
    trip_distance = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Distance in kilometers")
    
    # Cancellation
    cancellation_reason = models.TextField(blank=True)
    cancellation_date = models.DateTimeField(null=True, blank=True)
    cancellation_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['check_in', 'check_out']),
            models.Index(fields=['status']),
            models.Index(fields=['guest']),
            models.Index(fields=['property']),
        ]
    
    def __str__(self):
        return f"Booking {self.booking_reference} - {self.guest.username if self.guest else 'Guest'}"
    
    def save(self, *args, **kwargs):
        if not self.booking_reference:
            year = timezone.now().year
            random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            self.booking_reference = f"BK-{year}-{random_chars}"
        super().save(*args, **kwargs)


# ============================================
# 5. REAL-TIME TRACKING (OPTIONAL)
# ============================================

class DriverLocation(models.Model):
    """Real-time driver/agent location tracking - ONLY for on-demand mode"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='driver_locations')
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy = models.PositiveIntegerField(default=0, help_text="Accuracy in meters")
    speed = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Speed in km/h")
    heading = models.PositiveIntegerField(default=0, help_text="Heading in degrees")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['driver', 'updated_at']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"{self.driver.username} - {self.latitude}, {self.longitude}"


# ============================================
# 6. AVAILABILITY CALENDAR
# ============================================

class AvailabilityCalendar(models.Model):
    """Availability calendar for properties and rooms"""
    
    AVAILABILITY_TYPES = (
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('blocked', 'Blocked'),
        ('maintenance', 'Maintenance'),
        ('seasonal', 'Seasonal Availability'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='availability_calendar', null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='availability_calendar', null=True, blank=True)
    
    start_date = models.DateField()
    end_date = models.DateField()
    availability_type = models.CharField(max_length=20, choices=AVAILABILITY_TYPES, default='available')
    special_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    special_price_note = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['start_date']
        unique_together = ['property', 'start_date', 'end_date']
    
    def __str__(self):
        return f"{self.availability_type} - {self.start_date} to {self.end_date}"


# ============================================
# 7. BOOKING INQUIRIES
# ============================================

class BookingInquiry(models.Model):
    """Booking inquiries and requests"""
    
    INQUIRY_TYPES = (
        ('availability', 'Check Availability'),
        ('pricing', 'Pricing Inquiry'),
        ('booking', 'Booking Request'),
        ('special', 'Special Request'),
        ('group_booking', 'Group/Corporate Booking'),
    )
    
    INQUIRY_STATUS = (
        ('new', 'New'),
        ('responded', 'Responded'),
        ('follow_up', 'Follow Up'),
        ('booked', 'Booked'),
        ('closed', 'Closed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='inquiries')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='inquiries')
    
    # Contact information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    company = models.CharField(max_length=200, blank=True)
    
    # User reference
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='property_inquiries')
    
    # Inquiry details
    inquiry_type = models.CharField(max_length=20, choices=INQUIRY_TYPES, default='availability')
    message = models.TextField()
    preferred_date_from = models.DateField(null=True, blank=True)
    preferred_date_to = models.DateField(null=True, blank=True)
    number_of_guests = models.PositiveIntegerField(default=1)
    
    # Status
    status = models.CharField(max_length=20, choices=INQUIRY_STATUS, default='new')
    response = models.TextField(blank=True)
    responded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='inquiry_responses')
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Follow up
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Inquiry from {self.first_name} {self.last_name} - {self.inquiry_type}"


# ============================================
# 8. REVIEWS AND RATINGS
# ============================================

class PropertyReview(models.Model):
    """Reviews and ratings for properties"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='property_reviews')
    
    # Ratings (1-5)
    overall_rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    cleanliness = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    communication = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    location = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    value_for_money = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    amenities = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    
    review_title = models.CharField(max_length=200, blank=True)
    review_text = models.TextField()
    
    # Pros and Cons
    pros = models.JSONField(default=list, blank=True)
    cons = models.JSONField(default=list, blank=True)
    
    # Images
    review_images = models.JSONField(default=list, blank=True)
    
    # Flags
    is_verified = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    
    # Admin moderation
    is_approved = models.BooleanField(default=False)
    is_reported = models.BooleanField(default=False)
    report_reason = models.TextField(blank=True)
    
    # Response from property owner
    owner_response = models.TextField(blank=True)
    owner_response_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['-created_at']
        unique_together = ['user', 'property']
    
    def __str__(self):
        return f"Review by {self.user.username} - {self.overall_rating} stars"


# ============================================
# 9. WISHLIST / FAVORITES
# ============================================

class Wishlist(models.Model):
    """User wishlist for properties and rooms"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wishlists')
    name = models.CharField(max_length=100, default='Default Wishlist')
    description = models.TextField(blank=True)
    properties = models.ManyToManyField(Property, related_name='wishlists', blank=True)
    rooms = models.ManyToManyField(Room, related_name='wishlists', blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s {self.name}"


# ============================================
# 10. PROPERTY ANALYTICS
# ============================================

class PropertyAnalytics(models.Model):
    """Analytics for property performance"""
    
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='analytics')
    
    # Views
    total_views = models.PositiveIntegerField(default=0)
    unique_views = models.PositiveIntegerField(default=0)
    views_by_device = models.JSONField(default=dict, blank=True)
    views_by_country = models.JSONField(default=dict, blank=True)
    
    # Inquiries
    total_inquiries = models.PositiveIntegerField(default=0)
    inquiry_conversion_rate = models.FloatField(default=0.0)
    
    # Bookings
    total_bookings = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_occupancy_rate = models.FloatField(default=0.0)
    
    # Engagement
    favorites_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    
    # Time metrics
    days_on_market = models.PositiveIntegerField(default=0)
    average_booking_duration = models.FloatField(default=0.0)
    
    # Last 30 days metrics
    views_last_30_days = models.PositiveIntegerField(default=0)
    inquiries_last_30_days = models.PositiveIntegerField(default=0)
    bookings_last_30_days = models.PositiveIntegerField(default=0)
    revenue_last_30_days = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Seasonal analytics
    seasonal_data = models.JSONField(default=dict, blank=True)
    
    # Updated timestamp
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
    
    def __str__(self):
        return f"Analytics for {self.property.title}"


# ============================================
# 11. MAINTENANCE
# ============================================

class MaintenanceCategory(models.Model):
    """Simple category model - user can add, edit, delete"""
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)  # FontAwesome icon class
    color = models.CharField(max_length=20, default='#c62828')  # Hex color
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
     
    class Meta:
        app_label = 'realestate'
        ordering = ['name']
        verbose_name_plural = "Maintenance Categories"
    
    def __str__(self):
        return self.name


class MaintenanceRequest(models.Model):
    """Simple maintenance request model"""
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    # Relationships
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='maintenance_requests')
    tenant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='maintenance_requests', null=True, blank=True)
    category = models.ForeignKey(MaintenanceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='requests')
    
    # Core fields - simple and clean
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Location info - optional
    location = models.CharField(max_length=100, blank=True, null=True)
    
    # Scheduling - optional
    preferred_date = models.DateField(null=True, blank=True)
    
    # Cost tracking - optional
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Media - optional
    image = models.ImageField(upload_to='maintenance/', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        return f"#{self.id} - {self.title[:50]}"
    
    def save(self, *args, **kwargs):
        if self.status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)


class MaintenanceComment(models.Model):
    """Simple comments for maintenance requests"""
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='maintenance_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment on #{self.request.id} by {self.author.username}"


# ============================================
# 12. AGENT PROFILE - With Complete Social Links
# ============================================

class AgentProfile(models.Model):
    """
    Agent Profile with global support using Country model
    """
    
    # ===== AGENT TYPES =====
    AGENT_TYPES = (
        ('independent', 'Independent Agent'),
        ('agency', 'Agency Agent'),
        ('broker', 'Broker'),
        ('property_manager', 'Property Manager'),
        ('developer', 'Developer'),
        ('consultant', 'Real Estate Consultant'),
        ('commercial', 'Commercial Agent'),
        ('residential', 'Residential Agent'),
        ('student_housing', 'Student Housing Specialist'),
        ('luxury', 'Luxury Property Specialist'),
        ('international', 'International Property Specialist'),
        ('corporate', 'Corporate Real Estate'),
        ('investment', 'Investment Property Specialist'),
        ('custom', 'Custom (Specify Below)'),
    )
    
    # ===== SPECIALIZATIONS =====
    SPECIALIZATIONS = (
        # Residential
        ('residential', 'Residential Sales'),
        ('luxury', 'Luxury Homes'),
        ('first_time', 'First-Time Buyers'),
        ('foreclosure', 'Foreclosure/Short Sale'),
        ('new_construction', 'New Construction'),
        
        # Commercial
        ('commercial', 'Commercial Sales'),
        ('retail', 'Retail Space'),
        ('office', 'Office Space'),
        ('industrial', 'Industrial'),
        ('warehouse', 'Warehouse/Logistics'),
        ('hospitality', 'Hospitality/Hotels'),
        
        # Land & Development
        ('land', 'Land & Farms'),
        ('development', 'New Developments'),
        ('zoning', 'Zoning & Permits'),
        
        # Rental & Management
        ('rentals', 'Rentals & Leasing'),
        ('property_management', 'Property Management'),
        ('vacation_rentals', 'Vacation Rentals'),
        ('student_housing', 'Student Housing'),
        
        # Investment
        ('investment', 'Investment Properties'),
        ('investment_1031', '1031 Exchange'),
        ('commercial_investment', 'Commercial Investment'),
        
        # International
        ('international', 'International Real Estate'),
        ('expat', 'Expat/Relocation Specialist'),
        ('dual_citizenship', 'Dual Citizenship Properties'),
        
        # Special
        ('auctions', 'Auctions'),
        ('green', 'Green/Eco-Friendly Properties'),
        ('historic', 'Historic Properties'),
        ('waterfront', 'Waterfront Properties'),
        ('golf', 'Golf Course Properties'),
        ('ranch', 'Ranch/Farm Properties'),
        ('custom', 'Custom (Specify Below)'),
    )
    
    # ===== LINK TO CUSTOMUSER =====
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='agent_profile'
    )
    
    # ===== BASIC INFO =====
    display_name = models.CharField(max_length=100, blank=True, help_text="Name shown to clients")
    agent_type = models.CharField(max_length=20, choices=AGENT_TYPES, default='independent')
    custom_agent_type = models.CharField(max_length=100, blank=True, help_text="If 'Custom' selected, specify your agent type")
    agency_name = models.CharField(max_length=200, blank=True, help_text="Name of agency/company")
    agency_logo = models.ImageField(
        upload_to='agent_logos/%Y/%m/',
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'svg'])]
    )
    
    # ===== CONTACT DETAILS =====
    phone_primary = models.CharField(max_length=30, blank=True, help_text="Primary phone (any format, smart detection)")
    phone_secondary = models.CharField(max_length=30, blank=True, help_text="Secondary phone")
    email_primary = models.EmailField(blank=True, help_text="Primary email address")
    email_secondary = models.EmailField(blank=True, help_text="Secondary email address")
    website = models.CharField(max_length=500, blank=True, help_text="Website (any format, we'll clean it)")
    
    # ===== LOCATION =====
    business_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name='agents')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # ============================================================
    # SOCIAL MEDIA - GLOBAL PLATFORMS
    # ============================================================
    
    # ---- MAJOR GLOBAL PLATFORMS ----
    linkedin_url = models.CharField(max_length=500, blank=True, help_text="LinkedIn URL")
    twitter_url = models.CharField(max_length=500, blank=True, help_text="Twitter/X URL")
    facebook_url = models.CharField(max_length=500, blank=True, help_text="Facebook URL")
    instagram_url = models.CharField(max_length=500, blank=True, help_text="Instagram URL")
    youtube_url = models.CharField(max_length=500, blank=True, help_text="YouTube URL")
    tiktok_url = models.CharField(max_length=500, blank=True, help_text="TikTok URL")
    pinterest_url = models.CharField(max_length=500, blank=True, help_text="Pinterest URL")
    snapchat_url = models.CharField(max_length=500, blank=True, help_text="Snapchat URL")
    reddit_url = models.CharField(max_length=500, blank=True, help_text="Reddit URL")
    
    # ---- MESSAGING APPS ----
    whatsapp_number = models.CharField(max_length=30, blank=True, help_text="WhatsApp number (any format)")
    telegram_username = models.CharField(max_length=100, blank=True, help_text="Telegram @username")
    wechat_id = models.CharField(max_length=100, blank=True, help_text="WeChat ID")
    signal_number = models.CharField(max_length=30, blank=True, help_text="Signal number")
    viber_number = models.CharField(max_length=30, blank=True, help_text="Viber number")
    line_id = models.CharField(max_length=100, blank=True, help_text="LINE ID")
    kakao_id = models.CharField(max_length=100, blank=True, help_text="KakaoTalk ID")
    discord_username = models.CharField(max_length=100, blank=True, help_text="Discord username#tag")
    
    # ---- REGION-SPECIFIC REAL ESTATE PLATFORMS ----
    # USA/Canada
    zillow_url = models.CharField(max_length=500, blank=True, help_text="Zillow Profile URL")
    realtor_url = models.CharField(max_length=500, blank=True, help_text="Realtor.com Profile URL")
    trulia_url = models.CharField(max_length=500, blank=True, help_text="Trulia Profile URL")
    redfin_url = models.CharField(max_length=500, blank=True, help_text="Redfin Profile URL")
    homescom_url = models.CharField(max_length=500, blank=True, help_text="Homes.com Profile URL")
    
    # UK/Europe
    rightmove_url = models.CharField(max_length=500, blank=True, help_text="Rightmove Profile URL")
    zoopla_url = models.CharField(max_length=500, blank=True, help_text="Zoopla Profile URL")
    onthemarket_url = models.CharField(max_length=500, blank=True, help_text="OnTheMarket Profile URL")
    primelocation_url = models.CharField(max_length=500, blank=True, help_text="PrimeLocation Profile URL")
    
    # South Africa
    property24_url = models.CharField(max_length=500, blank=True, help_text="Property24 Profile URL")
    privateproperty_url = models.CharField(max_length=500, blank=True, help_text="PrivateProperty Profile URL")
    
    # Australia/NZ
    realestatecomau_url = models.CharField(max_length=500, blank=True, help_text="realestate.com.au URL")
    domaincomau_url = models.CharField(max_length=500, blank=True, help_text="domain.com.au URL")
    
    # Middle East
    propertyfinder_url = models.CharField(max_length=500, blank=True, help_text="Property Finder URL")
    bayut_url = models.CharField(max_length=500, blank=True, help_text="Bayut URL")
    dubizzle_url = models.CharField(max_length=500, blank=True, help_text="Dubizzle URL")
    
    # Asia
    propertyguru_url = models.CharField(max_length=500, blank=True, help_text="PropertyGuru URL")
    rumah123_url = models.CharField(max_length=500, blank=True, help_text="Rumah123 URL")
    ninety_nine_co_url = models.CharField(max_length=500, blank=True, help_text="99.co URL")
    
    # Latin America
    vivareal_url = models.CharField(max_length=500, blank=True, help_text="VivaReal URL")
    properati_url = models.CharField(max_length=500, blank=True, help_text="Properati URL")
    
    # ---- BUSINESS PROFESSIONAL ----
    indeed_url = models.CharField(max_length=500, blank=True, help_text="Indeed Profile URL")
    glassdoor_url = models.CharField(max_length=500, blank=True, help_text="Glassdoor Profile URL")
    angellist_url = models.CharField(max_length=500, blank=True, help_text="AngelList Profile URL")
    crunchbase_url = models.CharField(max_length=500, blank=True, help_text="Crunchbase Profile URL")
    
    # ============================================================
    # PROFESSIONAL DETAILS
    # ============================================================
    license_number = models.CharField(max_length=100, blank=True, help_text="Real Estate License Number")
    license_country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name='licensed_agents')
    ffc_number = models.CharField(max_length=50, blank=True, help_text="FFC Number (South Africa)")
    years_experience = models.PositiveIntegerField(default=0)
    
    # ===== SPECIALIZATIONS =====
    specializations = models.JSONField(default=list, blank=True)
    custom_specializations = models.TextField(blank=True, help_text="Custom specializations, comma-separated")
    languages_spoken = models.JSONField(default=list, blank=True)
    
    # ===== BIO =====
    bio = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    services_offered = models.TextField(blank=True)
    areas_served = models.TextField(blank=True)
    
    # ===== MEDIA =====
    profile_image = models.ImageField(
        upload_to='agent_profiles/%Y/%m/',
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]
    )
    cover_image = models.ImageField(
        upload_to='agent_covers/%Y/%m/',
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]
    )
    
    # ===== PROPERTY FOCUS =====
    property_focus = models.JSONField(default=list, blank=True)
    min_price_focus = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    max_price_focus = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    service_areas = models.JSONField(default=list, blank=True)
    
    # ===== RATINGS & REVIEWS =====
    average_rating = models.FloatField(default=0.0)
    total_reviews = models.PositiveIntegerField(default=0)
    response_time = models.CharField(max_length=50, blank=True)
    response_rate = models.CharField(max_length=20, blank=True)
    
    # ===== VERIFICATION =====
    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    verification_documents = models.JSONField(default=list, blank=True)
    
    # ===== AVAILABILITY =====
    working_hours = models.JSONField(default=dict, blank=True)
    timezone = models.CharField(max_length=50, blank=True, default='Africa/Johannesburg')
    
    # ===== STATS =====
    properties_sold = models.PositiveIntegerField(default=0)
    properties_rented = models.PositiveIntegerField(default=0)
    properties_listed = models.PositiveIntegerField(default=0)
    total_deals = models.PositiveIntegerField(default=0)
    total_volume = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    # ===== SETTINGS =====
    show_social_links = models.BooleanField(default=True)
    show_contact_details = models.BooleanField(default=True)
    auto_accept_messages = models.BooleanField(default=True)
    receive_notifications = models.BooleanField(default=True)
    
    # ===== TIMESTAMPS =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_verified', 'is_featured']),
            models.Index(fields=['city', 'state_province']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['country']),
        ]
    
    def __str__(self):
        return f"{self.display_name or self.user.username}'s Agent Profile"
    
    # ============================================================
    # SMART HELPER METHODS
    # ============================================================
    
    def clean_phone_number(self, number):
        """Clean and format phone number - Smart detection using Country model"""
        if not number:
            return None
        
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, number))
        
        if not cleaned:
            return None
        
        # Detect country using Country model
        country = Country.detect_country(cleaned)
        
        if country:
            # Remove country code
            local_number = cleaned[len(country.calling_code):]
            
            # Format local number with proper spacing
            if len(local_number) == 9:
                formatted_local = f"{local_number[:3]} {local_number[3:6]} {local_number[6:]}"
            elif len(local_number) == 10:
                formatted_local = f"{local_number[:3]} {local_number[3:6]} {local_number[6:]}"
            elif len(local_number) == 8:
                formatted_local = f"{local_number[:4]} {local_number[4:]}"
            else:
                formatted_local = local_number
            
            return f"+{country.calling_code} {formatted_local}"
        
        # If no country detected, return as is
        return number
    
    def clean_url(self, url):
        """Clean and format URL"""
        if not url:
            return None
        
        url = url.strip()
        
        # If it's already a valid URL with protocol
        if url.startswith('http://') or url.startswith('https://'):
            return url
        
        # Handle domain without protocol
        if '.' in url and not url.startswith('http'):
            if not url.startswith('www.'):
                url = 'www.' + url
            return 'https://' + url
        
        # Handle username formats
        if url.startswith('@'):
            return url[1:]
        
        return url
    
    def detect_country_from_number(self, number):
        """Detect country from phone number using Country model"""
        if not number:
            return None
        
        cleaned = ''.join(filter(str.isdigit, number))
        if not cleaned:
            return None
        
        return Country.detect_country(cleaned)
    
    def get_whatsapp_link(self):
        """Generate WhatsApp link with smart country detection"""
        if not self.whatsapp_number:
            return None
        
        # Clean the number
        cleaned = ''.join(filter(str.isdigit, self.whatsapp_number))
        
        if not cleaned:
            return None
        
        # Detect country
        country = Country.detect_country(cleaned)
        
        if country:
            # Use detected country code
            return f"https://wa.me/{country.calling_code}{cleaned[len(country.calling_code):]}"
        
        # If no country detected, return as is
        return f"https://wa.me/{cleaned}"
    
    def get_phone_display(self):
        """Get formatted phone number for display"""
        if not self.phone_primary:
            return None
        
        cleaned = self.clean_phone_number(self.phone_primary)
        if cleaned:
            return cleaned
        
        return self.phone_primary
    
    def get_telegram_link(self):
        """Generate Telegram link"""
        if not self.telegram_username:
            return None
        
        username = self.telegram_username.strip()
        if username.startswith('@'):
            username = username[1:]
        return f"https://t.me/{username}"
    
    def get_signal_link(self):
        """Generate Signal link"""
        if not self.signal_number:
            return None
        
        cleaned = ''.join(filter(str.isdigit, self.signal_number))
        if cleaned:
            return f"https://signal.me/#p/{cleaned}"
        return None
    
    def get_viber_link(self):
        """Generate Viber link"""
        if not self.viber_number:
            return None
        
        cleaned = ''.join(filter(str.isdigit, self.viber_number))
        if cleaned:
            return f"viber://add?number={cleaned}"
        return None
    
    def get_line_link(self):
        """Generate LINE link"""
        if not self.line_id:
            return None
        return f"https://line.me/ti/p/@{self.line_id}" if not self.line_id.startswith('@') else f"https://line.me/ti/p/{self.line_id}"
    
    def get_kakao_link(self):
        """Generate KakaoTalk link"""
        if not self.kakao_id:
            return None
        return f"https://open.kakao.com/o/{self.kakao_id}"
    
    def get_active_social_links(self):
        """Get only social links that have values"""
        links = {
            # Major Global
            'linkedin': self.clean_url(self.linkedin_url),
            'twitter': self.clean_url(self.twitter_url),
            'facebook': self.clean_url(self.facebook_url),
            'instagram': self.clean_url(self.instagram_url),
            'youtube': self.clean_url(self.youtube_url),
            'tiktok': self.clean_url(self.tiktok_url),
            'pinterest': self.clean_url(self.pinterest_url),
            'snapchat': self.clean_url(self.snapchat_url),
            'reddit': self.clean_url(self.reddit_url),
            
            # Messaging
            'whatsapp': self.get_whatsapp_link(),
            'telegram': self.get_telegram_link(),
            'wechat': self.wechat_id,
            'signal': self.get_signal_link(),
            'viber': self.get_viber_link(),
            'line': self.get_line_link(),
            'kakao': self.get_kakao_link(),
            'discord_username': self.discord_username,
            
            # Real Estate Platforms
            'zillow': self.clean_url(self.zillow_url),
            'realtor': self.clean_url(self.realtor_url),
            'trulia': self.clean_url(self.trulia_url),
            'redfin': self.clean_url(self.redfin_url),
            'homescom': self.clean_url(self.homescom_url),
            'rightmove': self.clean_url(self.rightmove_url),
            'zoopla': self.clean_url(self.zoopla_url),
            'onthemarket': self.clean_url(self.onthemarket_url),
            'primelocation': self.clean_url(self.primelocation_url),
            'property24': self.clean_url(self.property24_url),
            'privateproperty': self.clean_url(self.privateproperty_url),
            'realestatecomau': self.clean_url(self.realestatecomau_url),
            'domaincomau': self.clean_url(self.domaincomau_url),
            'propertyfinder': self.clean_url(self.propertyfinder_url),
            'bayut': self.clean_url(self.bayut_url),
            'dubizzle': self.clean_url(self.dubizzle_url),
            'propertyguru': self.clean_url(self.propertyguru_url),
            'rumah123': self.clean_url(self.rumah123_url),
            'ninety_nine_co': self.clean_url(self.ninety_nine_co_url),
            'vivareal': self.clean_url(self.vivareal_url),
            'properati': self.clean_url(self.properati_url),
            
            # Business
            'indeed': self.clean_url(self.indeed_url),
            'glassdoor': self.clean_url(self.glassdoor_url),
            'angellist': self.clean_url(self.angellist_url),
            'crunchbase': self.clean_url(self.crunchbase_url),
        }
        
        # Remove None values
        return {k: v for k, v in links.items() if v}
    
    def get_agent_type_display(self):
        if self.agent_type == 'custom' and self.custom_agent_type:
            return self.custom_agent_type
        return dict(self.AGENT_TYPES).get(self.agent_type, self.agent_type)
    
    def get_all_specializations(self):
        result = list(self.specializations) if self.specializations else []
        if self.custom_specializations:
            custom_items = [s.strip() for s in self.custom_specializations.split(',') if s.strip()]
            for item in custom_items:
                if item not in result:
                    result.append(item)
        return result
    
    def get_specialization_display(self):
        specializations = self.get_all_specializations()
        display_names = []
        for spec in specializations:
            for choice in self.SPECIALIZATIONS:
                if choice[0] == spec:
                    display_names.append(choice[1])
                    break
            else:
                display_names.append(spec)
        return display_names
    
    def get_profile_image_url(self):
        if self.profile_image:
            return self.profile_image.url
        return '/static/realestate/images/default-agent.jpg'
    
    def get_rating_stars(self):
        full = int(self.average_rating)
        half = self.average_rating % 1 >= 0.5
        stars = ''
        for i in range(full):
            stars += '★'
        if half:
            stars += '½'
        for i in range(5 - full - (1 if half else 0)):
            stars += '☆'
        return stars
    
    def get_rating_stars_html(self):
        full = int(self.average_rating)
        half = self.average_rating % 1 >= 0.5
        html = ''
        for i in range(full):
            html += '<i class="fas fa-star text-warning"></i>'
        if half:
            html += '<i class="fas fa-star-half-alt text-warning"></i>'
        for i in range(5 - full - (1 if half else 0)):
            html += '<i class="far fa-star text-muted"></i>'
        return html
    
    def get_contact_methods(self):
        """Get all contact methods - Internal Messaging FIRST"""
        methods = []
        
        # 1. INTERNAL MESSAGING - ALWAYS FIRST
        if self.user and self.user.id:
            methods.append({
                'type': 'message',
                'label': f'Message {self.display_name or self.user.username}',
                'value': str(self.user.id),
                'icon': 'fas fa-comment',
                'priority': 1,
                'is_primary': True,
                'internal': True,
                'action': 'message_property_owner',
                'description': 'Chat directly on OppoGlobe'
            })
        
        # 2. WhatsApp
        whatsapp_link = self.get_whatsapp_link()
        if whatsapp_link:
            methods.append({
                'type': 'whatsapp',
                'label': 'WhatsApp',
                'value': whatsapp_link,
                'icon': 'fab fa-whatsapp',
                'priority': 2,
                'is_primary': False,
                'internal': False,
                'action': 'external_link'
            })
        
        # 3. Phone Call
        if self.phone_primary:
            methods.append({
                'type': 'phone',
                'label': 'Call',
                'value': self.phone_primary,
                'icon': 'fas fa-phone',
                'priority': 3,
                'is_primary': False,
                'internal': False,
                'action': 'phone_call',
                'description': self.get_phone_display() or self.phone_primary
            })
        
        # 4. Email
        if self.email_primary:
            methods.append({
                'type': 'email',
                'label': 'Email',
                'value': self.email_primary,
                'icon': 'fas fa-envelope',
                'priority': 4,
                'is_primary': False,
                'internal': False,
                'action': 'email',
                'description': self.email_primary
            })
        
        # 5. Telegram
        telegram_link = self.get_telegram_link()
        if telegram_link:
            methods.append({
                'type': 'telegram',
                'label': 'Telegram',
                'value': telegram_link,
                'icon': 'fab fa-telegram',
                'priority': 5,
                'is_primary': False,
                'internal': False,
                'action': 'external_link'
            })
        
        # 6. Signal
        signal_link = self.get_signal_link()
        if signal_link:
            methods.append({
                'type': 'signal',
                'label': 'Signal',
                'value': signal_link,
                'icon': 'fas fa-lock',
                'priority': 6,
                'is_primary': False,
                'internal': False,
                'action': 'external_link'
            })
        
        # 7. Viber
        viber_link = self.get_viber_link()
        if viber_link:
            methods.append({
                'type': 'viber',
                'label': 'Viber',
                'value': viber_link,
                'icon': 'fab fa-viber',
                'priority': 7,
                'is_primary': False,
                'internal': False,
                'action': 'external_link'
            })
        
        # 8. WeChat
        if self.wechat_id:
            methods.append({
                'type': 'wechat',
                'label': 'WeChat',
                'value': self.wechat_id,
                'icon': 'fab fa-weixin',
                'priority': 8,
                'is_primary': False,
                'internal': False,
                'action': 'external_link'
            })
        
        # 9. LINE
        line_link = self.get_line_link()
        if line_link:
            methods.append({
                'type': 'line',
                'label': 'LINE',
                'value': line_link,
                'icon': 'fab fa-line',
                'priority': 9,
                'is_primary': False,
                'internal': False,
                'action': 'external_link'
            })
        
        # 10. KakaoTalk
        kakao_link = self.get_kakao_link()
        if kakao_link:
            methods.append({
                'type': 'kakao',
                'label': 'KakaoTalk',
                'value': kakao_link,
                'icon': 'fas fa-comment',
                'priority': 10,
                'is_primary': False,
                'internal': False,
                'action': 'external_link'
            })
        
        # Sort by priority
        methods.sort(key=lambda x: x['priority'])
        
        return methods
    
    def has_social_links(self):
        active = self.get_active_social_links()
        return bool(active)


# ============================================================
# AGENT SOCIAL SHARE MODEL
# ============================================================

class AgentSocialShare(models.Model):
    """Track shares to social platforms"""
    
    PLATFORM_CHOICES = (
        ('whatsapp', 'WhatsApp'),
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('linkedin', 'LinkedIn'),
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('youtube', 'YouTube'),
        ('telegram', 'Telegram'),
        ('signal', 'Signal'),
        ('viber', 'Viber'),
        ('wechat', 'WeChat'),
        ('line', 'LINE'),
        ('email', 'Email'),
        ('copy', 'Copy Link'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(AgentProfile, on_delete=models.CASCADE, related_name='social_shares')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, null=True, blank=True, related_name='agent_shares')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    shared_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='agent_shares')
    shared_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['-shared_at']
    
    def __str__(self):
        return f"{self.agent.display_name or self.agent.user.username} shared on {self.platform}"


# ============================================================
# AGENT REVIEW MODEL
# ============================================================

class AgentReview(models.Model):
    """Reviews for agents"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(AgentProfile, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='agent_reviews')
    
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    professionalism = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    communication = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    knowledge = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    responsiveness = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    negotiation = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    
    review_text = models.TextField()
    review_title = models.CharField(max_length=200, blank=True)
    
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    
    is_verified = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    
    agent_response = models.TextField(blank=True)
    agent_response_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        ordering = ['-created_at']
        unique_together = ['agent', 'user']
    
    def __str__(self):
        return f"Review for {self.agent.display_name or self.agent.user.username} by {self.user.username}"
    
    def get_stars(self):
        html = ''
        for i in range(self.rating):
            html += '★'
        for i in range(5 - self.rating):
            html += '☆'
        return html


# ============================================================
# AGENT CONNECTION MODEL
# ============================================================

class AgentConnection(models.Model):
    """Users following or connecting with agents"""
    
    CONNECTION_TYPES = (
        ('follower', 'Follower'),
        ('saved', 'Saved Agent'),
        ('client', 'Client'),
        ('past_client', 'Past Client'),
        ('referral', 'Referral Partner'),
        ('collaborator', 'Collaborator'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(AgentProfile, on_delete=models.CASCADE, related_name='connections')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='agent_connections')
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPES, default='follower')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'realestate'
        unique_together = ['agent', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.connection_type} - {self.agent.display_name or self.agent.user.username}"