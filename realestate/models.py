from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
import random
import string
from decimal import Decimal, InvalidOperation
import re

User = get_user_model()

# ============================================================
# IMPORT FROM HIRING APP – USE ACTUAL CLASSES
# ============================================================
try:
    from hiring.models import BusinessProfile, CustomUser, ApplicantProfile
except ImportError:
    # Fallback – only if hiring app is missing (not recommended)
    CustomUser = User
    ApplicantProfile = None
    # Dummy BusinessProfile to avoid crashes
    class BusinessProfile(models.Model):
        class Meta:
            managed = False
            app_label = 'hiring'
        company_name = models.CharField(max_length=255, blank=True)
        user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

# ============================================================
# COUNTRY MODEL (unchanged)
# ============================================================
class Country(models.Model):
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
        if not phone_number:
            return None
        cleaned = ''.join(filter(str.isdigit, phone_number))
        if not cleaned:
            return None
        from django.db.models.functions import Length
        countries = cls.objects.filter(is_active=True).annotate(
            code_length=Length('calling_code')
        ).order_by('-code_length')
        for country in countries:
            if cleaned.startswith(country.calling_code):
                return country
        return None


# ============================================================
# PROPERTY CATEGORY / TYPE / FEATURE (unchanged)
# ============================================================
class PropertyCategory(models.Model):
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
    icon = models.CharField(max_length=50, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    is_system = models.BooleanField(default=False)
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
    is_commercial = models.BooleanField(default=False)
    is_residential = models.BooleanField(default=True)
    is_hospitality = models.BooleanField(default=False)
    is_student_housing = models.BooleanField(default=False)
    min_occupancy = models.PositiveIntegerField(default=1)
    max_occupancy = models.PositiveIntegerField(default=2)
    min_booking_duration = models.PositiveIntegerField(default=1)
    max_booking_duration = models.PositiveIntegerField(null=True, blank=True)
    booking_period = models.CharField(max_length=10, choices=BOOKING_PERIOD_CHOICES, default='day')
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
    is_custom = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'realestate'
        ordering = ['name']

    def __str__(self):
        return self.name


# ============================================================
# UNIVERSAL PRICE CLEANING & FLEXIBLE PRICE FIELD
# ============================================================
def clean_price_string(raw) -> Decimal:
    if raw is None:
        return None
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, (int, float)):
        return Decimal(str(raw))
    cleaned = re.sub(r'[^\d.,]', '', str(raw).strip())
    if not cleaned:
        return None
    dots = cleaned.count('.')
    commas = cleaned.count(',')
    if dots > 0 and commas > 0:
        if cleaned.rfind(',') > cleaned.rfind('.'):
            cleaned = cleaned.replace('.', '')
            cleaned = cleaned.replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif commas > 0 and dots == 0:
        if cleaned.count(',') > 1:
            cleaned = cleaned.replace(',', '')
        else:
            cleaned = cleaned.replace(',', '.')
    elif dots > 0 and commas == 0:
        if cleaned.count('.') > 1:
            cleaned = cleaned.replace('.', '')
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        fallback = re.sub(r'[^\d.]', '', raw)
        if fallback.count('.') > 1:
            parts = fallback.split('.')
            fallback = ''.join(parts[:-1]) + '.' + parts[-1]
        return Decimal(fallback or '0')


class FlexiblePriceField(models.DecimalField):
    def to_python(self, value):
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        try:
            return clean_price_string(value)
        except (ValueError, TypeError, InvalidOperation):
            raise models.ValidationError(f"'{value}' is not a valid price format.")

    def get_prep_value(self, value):
        if value is None:
            return None
        return super().get_prep_value(value)


# ============================================================
# MAIN PROPERTY MODEL – FULLY FIXED ForeignKeys
# ============================================================
class Property(models.Model):
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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property_reference = models.CharField(max_length=50, unique=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()

    property_type = models.ForeignKey(PropertyType, on_delete=models.PROTECT, related_name='properties')
    custom_category_name = models.CharField(max_length=100, blank=True)
    custom_category_description = models.TextField(blank=True)
    features = models.ManyToManyField(PropertyFeature, related_name='properties', blank=True)

    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='South Africa')
    postal_code = models.CharField(max_length=20, blank=True)

    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    formatted_address = models.TextField(blank=True)
    place_id = models.CharField(max_length=255, blank=True)
    neighborhood = models.CharField(max_length=100, blank=True)
    landmark = models.CharField(max_length=200, blank=True)
    map_zoom_level = models.PositiveIntegerField(default=15)
    location_data = models.JSONField(default=dict, blank=True)

    total_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    land_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    floor_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_rooms = models.PositiveIntegerField(default=1)
    total_floors = models.PositiveIntegerField(default=1)
    max_occupancy = models.PositiveIntegerField(default=1)
    room_count = models.JSONField(default=dict, blank=True)

    bedrooms = models.PositiveIntegerField(default=0)
    bathrooms = models.PositiveIntegerField(default=0)
    garages = models.PositiveIntegerField(default=0)
    parking_spaces = models.PositiveIntegerField(default=0)
    amenities = models.JSONField(default=list, blank=True)

    # PRICE FIELDS – using FlexiblePriceField
    base_price = FlexiblePriceField(max_digits=12, decimal_places=2, help_text="Base price for booking/rent/sale")
    price_per_unit = FlexiblePriceField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Price per room/unit")
    price_per_sqm = FlexiblePriceField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_currency = models.CharField(max_length=3, default='ZAR')

    BOOKING_UNITS = (
        ('hour', 'Per Hour'),
        ('day', 'Per Day'),
        ('week', 'Per Week'),
        ('month', 'Per Month'),
        ('year', 'Per Year'),
    )
    booking_unit = models.CharField(max_length=10, choices=BOOKING_UNITS, default='day')

    PRICING_STRUCTURES = (
        ('fixed', 'Fixed Price'),
        ('tiered', 'Tiered Pricing'),
        ('dynamic', 'Dynamic Pricing'),
        ('negotiable', 'Negotiable'),
        ('per_person', 'Per Person'),
        ('per_night', 'Per Night'),
    )
    pricing_structure = models.CharField(max_length=20, choices=PRICING_STRUCTURES, default='fixed')
    pricing_details = models.JSONField(default=dict, blank=True)

    listing_type = models.CharField(max_length=10, choices=LISTING_TYPES, default='booking')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='booking')
    listing_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')

    is_bookable = models.BooleanField(default=True)
    booking_mode = models.CharField(max_length=20, choices=BOOKING_MODES, default='traditional')
    available_from = models.DateField(null=True, blank=True)
    available_until = models.DateField(null=True, blank=True)
    minimum_stay = models.PositiveIntegerField(default=1)
    maximum_stay = models.PositiveIntegerField(null=True, blank=True)

    # ===== FIXED: Use direct class references (no strings) =====
    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_properties'
    )
    listing_agent = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='listed_properties'
    )
    company = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name='properties',
        null=True,
        blank=True
    )

    is_online = models.BooleanField(default=False)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    current_occupancy = models.PositiveIntegerField(default=0)
    max_capacity = models.PositiveIntegerField(default=1)
    agent_status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('on_route', 'On Route'),
            ('booked', 'Booked'),
            ('offline', 'Offline'),
        ],
        default='offline'
    )
    assigned_agent = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_properties'
    )

    main_image = models.ImageField(
        upload_to='properties/main/%Y/%m/%d/',
        null=True, blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]
    )
    virtual_tour_url = models.URLField(blank=True)
    additional_images = models.JSONField(default=list, blank=True)

    is_featured = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    custom_fields = models.JSONField(default=dict, blank=True)

    likes_count = models.PositiveIntegerField(default=0)
    dislikes_count = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    rating_count = models.PositiveIntegerField(default=0)

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
        if self.address and (not self.latitude or not self.longitude):
            self.geocode_address()
        super().save(*args, **kwargs)

    def geocode_address(self):
        from django.conf import settings
        google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        if not google_api_key:
            print("⚠️ Google Maps API key not configured for geocoding")
            return
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
# REMAINING MODELS (unchanged, except ForeignKey fixes)
# ============================================================
class PropertyInteraction(models.Model):
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


class PropertyRating(models.Model):
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


class Room(models.Model):
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
    room_number = models.CharField(max_length=20, blank=True)
    room_name = models.CharField(max_length=100, blank=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='single')
    custom_room_type = models.CharField(max_length=100, blank=True)
    room_status = models.CharField(max_length=20, choices=ROOM_STATUS, default='available')
    capacity = models.PositiveIntegerField(default=1)
    bed_count = models.PositiveIntegerField(default=1)
    bed_types = models.JSONField(default=list, blank=True)
    size_sq_meters = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_per_week = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    custom_pricing = models.JSONField(default=dict, blank=True)
    amenities = models.JSONField(default=list, blank=True)
    has_private_bathroom = models.BooleanField(default=False)
    has_kitchenette = models.BooleanField(default=False)
    has_balcony = models.BooleanField(default=False)
    has_ac = models.BooleanField(default=False)
    has_heating = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=True)
    has_tv = models.BooleanField(default=False)
    has_safe = models.BooleanField(default=False)
    is_accessible = models.BooleanField(default=False)
    has_window = models.BooleanField(default=True)
    room_image = models.ImageField(
        upload_to='rooms/%Y/%m/%d/',
        null=True, blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]
    )
    additional_images = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    available_from = models.DateField(null=True, blank=True)
    available_until = models.DateField(null=True, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'realestate'
        ordering = ['room_number', 'room_type']
        unique_together = ['property', 'room_number']

    def __str__(self):
        return f"{self.room_number or self.room_name} - {self.get_room_type_display()}"


class Booking(models.Model):
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
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    guest = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bookings')
    guest_details = models.JSONField(default=dict, blank=True)
    business = models.ForeignKey(BusinessProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    actual_check_in = models.DateTimeField(null=True, blank=True)
    actual_check_out = models.DateTimeField(null=True, blank=True)
    duration_days = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    taxes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='ZAR')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='pending')
    number_of_guests = models.PositiveIntegerField(default=1)
    guest_names = models.JSONField(default=list, blank=True)
    special_requests = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    booking_mode = models.CharField(max_length=20, choices=Property.BOOKING_MODES, default='traditional')
    assigned_driver = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bookings')
    driver_status = models.CharField(
        max_length=20,
        choices=[
            ('arriving', 'Arriving'),
            ('waiting', 'Waiting for Guest'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='arriving',
        blank=True
    )
    pickup_location = models.JSONField(default=dict, blank=True)
    dropoff_location = models.JSONField(default=dict, blank=True)
    current_location = models.JSONField(default=dict, blank=True)
    route_path = models.JSONField(default=list, blank=True)
    estimated_pickup_time = models.DateTimeField(null=True, blank=True)
    actual_pickup_time = models.DateTimeField(null=True, blank=True)
    trip_duration = models.PositiveIntegerField(default=0)
    trip_distance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cancellation_reason = models.TextField(blank=True)
    cancellation_date = models.DateTimeField(null=True, blank=True)
    cancellation_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
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


class DriverLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='driver_locations')
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy = models.PositiveIntegerField(default=0)
    speed = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    heading = models.PositiveIntegerField(default=0)
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


class AvailabilityCalendar(models.Model):
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


class BookingInquiry(models.Model):
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
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    company = models.CharField(max_length=200, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='property_inquiries')
    inquiry_type = models.CharField(max_length=20, choices=INQUIRY_TYPES, default='availability')
    message = models.TextField()
    preferred_date_from = models.DateField(null=True, blank=True)
    preferred_date_to = models.DateField(null=True, blank=True)
    number_of_guests = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=INQUIRY_STATUS, default='new')
    response = models.TextField(blank=True)
    responded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='inquiry_responses')
    responded_at = models.DateTimeField(null=True, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'realestate'
        ordering = ['-created_at']

    def __str__(self):
        return f"Inquiry from {self.first_name} {self.last_name} - {self.inquiry_type}"


class PropertyReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='property_reviews')
    overall_rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    cleanliness = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    communication = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    location = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    value_for_money = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    amenities = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    review_title = models.CharField(max_length=200, blank=True)
    review_text = models.TextField()
    pros = models.JSONField(default=list, blank=True)
    cons = models.JSONField(default=list, blank=True)
    review_images = models.JSONField(default=list, blank=True)
    is_verified = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    is_reported = models.BooleanField(default=False)
    report_reason = models.TextField(blank=True)
    owner_response = models.TextField(blank=True)
    owner_response_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'realestate'
        ordering = ['-created_at']
        unique_together = ['user', 'property']

    def __str__(self):
        return f"Review by {self.user.username} - {self.overall_rating} stars"


class Wishlist(models.Model):
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


class PropertyAnalytics(models.Model):
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='analytics')
    total_views = models.PositiveIntegerField(default=0)
    unique_views = models.PositiveIntegerField(default=0)
    views_by_device = models.JSONField(default=dict, blank=True)
    views_by_country = models.JSONField(default=dict, blank=True)
    total_inquiries = models.PositiveIntegerField(default=0)
    inquiry_conversion_rate = models.FloatField(default=0.0)
    total_bookings = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_occupancy_rate = models.FloatField(default=0.0)
    favorites_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    days_on_market = models.PositiveIntegerField(default=0)
    average_booking_duration = models.FloatField(default=0.0)
    views_last_30_days = models.PositiveIntegerField(default=0)
    inquiries_last_30_days = models.PositiveIntegerField(default=0)
    bookings_last_30_days = models.PositiveIntegerField(default=0)
    revenue_last_30_days = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    seasonal_data = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'realestate'

    def __str__(self):
        return f"Analytics for {self.property.title}"


class MaintenanceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=20, default='#c62828')
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

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='maintenance_requests')
    tenant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='maintenance_requests', null=True, blank=True)
    category = models.ForeignKey(MaintenanceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='requests')
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    location = models.CharField(max_length=100, blank=True, null=True)
    preferred_date = models.DateField(null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='maintenance/', blank=True, null=True)
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


# ============================================================
# AGENT PROFILE – FULLY FIXED ForeignKeys
# ============================================================
class AgentProfile(models.Model):
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

    SPECIALIZATIONS = (
        ('residential', 'Residential Sales'),
        ('luxury', 'Luxury Homes'),
        ('first_time', 'First-Time Buyers'),
        ('foreclosure', 'Foreclosure/Short Sale'),
        ('new_construction', 'New Construction'),
        ('commercial', 'Commercial Sales'),
        ('retail', 'Retail Space'),
        ('office', 'Office Space'),
        ('industrial', 'Industrial'),
        ('warehouse', 'Warehouse/Logistics'),
        ('hospitality', 'Hospitality/Hotels'),
        ('land', 'Land & Farms'),
        ('development', 'New Developments'),
        ('zoning', 'Zoning & Permits'),
        ('rentals', 'Rentals & Leasing'),
        ('property_management', 'Property Management'),
        ('vacation_rentals', 'Vacation Rentals'),
        ('student_housing', 'Student Housing'),
        ('investment', 'Investment Properties'),
        ('investment_1031', '1031 Exchange'),
        ('commercial_investment', 'Commercial Investment'),
        ('international', 'International Real Estate'),
        ('expat', 'Expat/Relocation Specialist'),
        ('dual_citizenship', 'Dual Citizenship Properties'),
        ('auctions', 'Auctions'),
        ('green', 'Green/Eco-Friendly Properties'),
        ('historic', 'Historic Properties'),
        ('waterfront', 'Waterfront Properties'),
        ('golf', 'Golf Course Properties'),
        ('ranch', 'Ranch/Farm Properties'),
        ('custom', 'Custom (Specify Below)'),
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='agent_profile')

    display_name = models.CharField(max_length=100, blank=True)
    agent_type = models.CharField(max_length=20, choices=AGENT_TYPES, default='independent')
    custom_agent_type = models.CharField(max_length=100, blank=True)
    agency_name = models.CharField(max_length=200, blank=True)
    agency_logo = models.ImageField(
        upload_to='agent_logos/%Y/%m/',
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'svg'])]
    )

    phone_primary = models.CharField(max_length=30, blank=True)
    phone_secondary = models.CharField(max_length=30, blank=True)
    email_primary = models.EmailField(blank=True)
    email_secondary = models.EmailField(blank=True)
    website = models.CharField(max_length=500, blank=True)

    business_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name='agents')
    postal_code = models.CharField(max_length=20, blank=True)

    # Social links (all remain CharFields)
    linkedin_url = models.CharField(max_length=500, blank=True)
    twitter_url = models.CharField(max_length=500, blank=True)
    facebook_url = models.CharField(max_length=500, blank=True)
    instagram_url = models.CharField(max_length=500, blank=True)
    youtube_url = models.CharField(max_length=500, blank=True)
    tiktok_url = models.CharField(max_length=500, blank=True)
    pinterest_url = models.CharField(max_length=500, blank=True)
    snapchat_url = models.CharField(max_length=500, blank=True)
    reddit_url = models.CharField(max_length=500, blank=True)

    whatsapp_number = models.CharField(max_length=30, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True)
    wechat_id = models.CharField(max_length=100, blank=True)
    signal_number = models.CharField(max_length=30, blank=True)
    viber_number = models.CharField(max_length=30, blank=True)
    line_id = models.CharField(max_length=100, blank=True)
    kakao_id = models.CharField(max_length=100, blank=True)
    discord_username = models.CharField(max_length=100, blank=True)

    zillow_url = models.CharField(max_length=500, blank=True)
    realtor_url = models.CharField(max_length=500, blank=True)
    trulia_url = models.CharField(max_length=500, blank=True)
    redfin_url = models.CharField(max_length=500, blank=True)
    homescom_url = models.CharField(max_length=500, blank=True)
    rightmove_url = models.CharField(max_length=500, blank=True)
    zoopla_url = models.CharField(max_length=500, blank=True)
    onthemarket_url = models.CharField(max_length=500, blank=True)
    primelocation_url = models.CharField(max_length=500, blank=True)
    property24_url = models.CharField(max_length=500, blank=True)
    privateproperty_url = models.CharField(max_length=500, blank=True)
    realestatecomau_url = models.CharField(max_length=500, blank=True)
    domaincomau_url = models.CharField(max_length=500, blank=True)
    propertyfinder_url = models.CharField(max_length=500, blank=True)
    bayut_url = models.CharField(max_length=500, blank=True)
    dubizzle_url = models.CharField(max_length=500, blank=True)
    propertyguru_url = models.CharField(max_length=500, blank=True)
    rumah123_url = models.CharField(max_length=500, blank=True)
    ninety_nine_co_url = models.CharField(max_length=500, blank=True)
    vivareal_url = models.CharField(max_length=500, blank=True)
    properati_url = models.CharField(max_length=500, blank=True)
    indeed_url = models.CharField(max_length=500, blank=True)
    glassdoor_url = models.CharField(max_length=500, blank=True)
    angellist_url = models.CharField(max_length=500, blank=True)
    crunchbase_url = models.CharField(max_length=500, blank=True)

    license_number = models.CharField(max_length=100, blank=True)
    license_country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name='licensed_agents')
    ffc_number = models.CharField(max_length=50, blank=True)
    years_experience = models.PositiveIntegerField(default=0)

    specializations = models.JSONField(default=list, blank=True)
    custom_specializations = models.TextField(blank=True)
    languages_spoken = models.JSONField(default=list, blank=True)

    bio = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    services_offered = models.TextField(blank=True)
    areas_served = models.TextField(blank=True)

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

    property_focus = models.JSONField(default=list, blank=True)
    min_price_focus = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    max_price_focus = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    service_areas = models.JSONField(default=list, blank=True)

    average_rating = models.FloatField(default=0.0)
    total_reviews = models.PositiveIntegerField(default=0)
    response_time = models.CharField(max_length=50, blank=True)
    response_rate = models.CharField(max_length=20, blank=True)

    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    verification_documents = models.JSONField(default=list, blank=True)

    working_hours = models.JSONField(default=dict, blank=True)
    timezone = models.CharField(max_length=50, blank=True, default='Africa/Johannesburg')

    properties_sold = models.PositiveIntegerField(default=0)
    properties_rented = models.PositiveIntegerField(default=0)
    properties_listed = models.PositiveIntegerField(default=0)
    total_deals = models.PositiveIntegerField(default=0)
    total_volume = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    show_social_links = models.BooleanField(default=True)
    show_contact_details = models.BooleanField(default=True)
    auto_accept_messages = models.BooleanField(default=True)
    receive_notifications = models.BooleanField(default=True)

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

    # ===== All helper methods remain exactly as you had them =====
    def clean_phone_number(self, number):
        if not number:
            return None
        cleaned = ''.join(filter(str.isdigit, number))
        if not cleaned:
            return None
        country = Country.detect_country(cleaned)
        if country:
            local_number = cleaned[len(country.calling_code):]
            if len(local_number) == 9:
                formatted_local = f"{local_number[:3]} {local_number[3:6]} {local_number[6:]}"
            elif len(local_number) == 10:
                formatted_local = f"{local_number[:3]} {local_number[3:6]} {local_number[6:]}"
            elif len(local_number) == 8:
                formatted_local = f"{local_number[:4]} {local_number[4:]}"
            else:
                formatted_local = local_number
            return f"+{country.calling_code} {formatted_local}"
        return number

    def clean_url(self, url):
        if not url:
            return None
        url = url.strip()
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if '.' in url and not url.startswith('http'):
            if not url.startswith('www.'):
                url = 'www.' + url
            return 'https://' + url
        if url.startswith('@'):
            return url[1:]
        return url

    def detect_country_from_number(self, number):
        if not number:
            return None
        cleaned = ''.join(filter(str.isdigit, number))
        if not cleaned:
            return None
        return Country.detect_country(cleaned)

    def get_whatsapp_link(self):
        if not self.whatsapp_number:
            return None
        cleaned = ''.join(filter(str.isdigit, self.whatsapp_number))
        if not cleaned:
            return None
        country = Country.detect_country(cleaned)
        if country:
            return f"https://wa.me/{country.calling_code}{cleaned[len(country.calling_code):]}"
        return f"https://wa.me/{cleaned}"

    def get_phone_display(self):
        if not self.phone_primary:
            return None
        cleaned = self.clean_phone_number(self.phone_primary)
        return cleaned or self.phone_primary

    def get_telegram_link(self):
        if not self.telegram_username:
            return None
        username = self.telegram_username.strip()
        if username.startswith('@'):
            username = username[1:]
        return f"https://t.me/{username}"

    def get_signal_link(self):
        if not self.signal_number:
            return None
        cleaned = ''.join(filter(str.isdigit, self.signal_number))
        if cleaned:
            return f"https://signal.me/#p/{cleaned}"
        return None

    def get_viber_link(self):
        if not self.viber_number:
            return None
        cleaned = ''.join(filter(str.isdigit, self.viber_number))
        if cleaned:
            return f"viber://add?number={cleaned}"
        return None

    def get_line_link(self):
        if not self.line_id:
            return None
        return f"https://line.me/ti/p/@{self.line_id}" if not self.line_id.startswith('@') else f"https://line.me/ti/p/{self.line_id}"

    def get_kakao_link(self):
        if not self.kakao_id:
            return None
        return f"https://open.kakao.com/o/{self.kakao_id}"

    def get_active_social_links(self):
        links = {
            'linkedin': self.clean_url(self.linkedin_url),
            'twitter': self.clean_url(self.twitter_url),
            'facebook': self.clean_url(self.facebook_url),
            'instagram': self.clean_url(self.instagram_url),
            'youtube': self.clean_url(self.youtube_url),
            'tiktok': self.clean_url(self.tiktok_url),
            'pinterest': self.clean_url(self.pinterest_url),
            'snapchat': self.clean_url(self.snapchat_url),
            'reddit': self.clean_url(self.reddit_url),
            'whatsapp': self.get_whatsapp_link(),
            'telegram': self.get_telegram_link(),
            'wechat': self.wechat_id,
            'signal': self.get_signal_link(),
            'viber': self.get_viber_link(),
            'line': self.get_line_link(),
            'kakao': self.get_kakao_link(),
            'discord_username': self.discord_username,
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
            'indeed': self.clean_url(self.indeed_url),
            'glassdoor': self.clean_url(self.glassdoor_url),
            'angellist': self.clean_url(self.angellist_url),
            'crunchbase': self.clean_url(self.crunchbase_url),
        }
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
        methods = []
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
        methods.sort(key=lambda x: x['priority'])
        return methods

    def has_social_links(self):
        return bool(self.get_active_social_links())


# ============================================================
# AGENT SOCIAL SHARE & REVIEW & CONNECTION (unchanged)
# ============================================================
class AgentSocialShare(models.Model):
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


class AgentReview(models.Model):
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


class AgentConnection(models.Model):
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