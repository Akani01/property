from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
import random
import string
from decimal import Decimal

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
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
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
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
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
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
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
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_properties')
    listing_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='listed_properties')
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
    assigned_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_properties')
    
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
    
    def save(self, *args, **kwargs):
        if not self.property_reference:
            year = timezone.now().year
            random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.property_reference = f"PROP-{year}-{random_chars}"
        super().save(*args, **kwargs)
    
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


# ============================================
# 3. ROOM/UNIT MANAGEMENT
# ============================================

class Room(models.Model):
    """Individual rooms/units within a property"""
    
    ROOM_TYPES = (
        ('single', 'Single Room'),
        ('double', 'Double Room'),
        ('twin', 'Twin R1oom'),
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
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
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
    assigned_driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bookings')
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
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='driver_locations')
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
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
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
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='property_inquiries')
    
    # Inquiry details
    inquiry_type = models.CharField(max_length=20, choices=INQUIRY_TYPES, default='availability')
    message = models.TextField()
    preferred_date_from = models.DateField(null=True, blank=True)
    preferred_date_to = models.DateField(null=True, blank=True)
    number_of_guests = models.PositiveIntegerField(default=1)
    
    # Status
    status = models.CharField(max_length=20, choices=INQUIRY_STATUS, default='new')
    response = models.TextField(blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inquiry_responses')
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='property_reviews')
    
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
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