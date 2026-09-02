from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from django.db.models import Count, Avg
from django.core.cache import cache
from .models import *
from hiring.models import BusinessProfile, CustomUser, ApplicantProfile
from decimal import Decimal
# Import your cleaning function from models
from .models import Property, clean_price_string  # ensure clean_price_string is defined at module level


# ============================================
# 1. CATEGORY SERIALIZERS
# ============================================

class PropertyCategorySerializer(serializers.ModelSerializer):
    property_type_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default=None)
    
    class Meta:
        model = PropertyCategory
        fields = [
            'id', 'name', 'category_type', 'description', 
            'icon', 'custom_fields', 'is_system', 'is_active',
            'created_by', 'created_by_name', 'property_type_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_property_type_count(self, obj):
        return obj.property_types.count()


class PropertyTypeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default=None)
    
    class Meta:
        model = PropertyType
        fields = [
            'id', 'name', 'category', 'category_name', 'description',
            'icon', 'size_classification', 'is_commercial', 'is_residential',
            'is_hospitality', 'is_student_housing', 'min_occupancy',
            'max_occupancy', 'min_booking_duration', 'max_booking_duration',
            'booking_period', 'pricing_model', 'custom_attributes',
            'is_system', 'is_active', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PropertyFeatureSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default=None)
    
    class Meta:
        model = PropertyFeature
        fields = [
            'id', 'name', 'icon', 'category', 'is_custom',
            'is_active', 'created_by', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ============================================
# 2. ROOM SERIALIZERS
# ============================================

class RoomSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source='property.title', read_only=True)
    room_type_display = serializers.CharField(source='get_room_type_display', read_only=True)
    room_status_display = serializers.CharField(source='get_room_status_display', read_only=True)
    
    class Meta:
        model = Room
        fields = [
            'id', 'property', 'property_title', 'room_number', 'room_name',
            'room_type', 'room_type_display', 'custom_room_type',
            'room_status', 'room_status_display', 'capacity', 'bed_count',
            'bed_types', 'size_sq_meters', 'price_per_night', 'price_per_week',
            'price_per_month', 'custom_pricing', 'amenities',
            'has_private_bathroom', 'has_kitchenette', 'has_balcony',
            'has_ac', 'has_heating', 'has_wifi', 'has_tv', 'has_safe',
            'is_accessible', 'has_window', 'room_image', 'additional_images',
            'description', 'notes', 'is_active', 'available_from',
            'available_until', 'custom_fields', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================
# 3. PROPERTY SERIALIZERS - FIXED WITH OWNER
# ============================================

class PropertyListSerializer(serializers.ModelSerializer):
    """List view serializer with user interactions and OWNER data"""
    
    likes_count = serializers.IntegerField(read_only=True, default=0)
    dislikes_count = serializers.IntegerField(read_only=True, default=0)
    average_rating = serializers.FloatField(read_only=True, default=0.0)
    rating_count = serializers.IntegerField(read_only=True, default=0)
    
    main_image_url = serializers.SerializerMethodField()
    uploader_name = serializers.SerializerMethodField()
    user_interaction = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    
    # ===== OWNER FIELD - Returns full object =====
    owner = serializers.SerializerMethodField()
    
    class Meta:
        model = Property
        fields = [
            'id', 'property_reference', 'title', 'description',
            'city', 'country', 'address',
            'base_price', 'price_currency', 'listing_type',
            'status', 'is_featured', 'is_premium', 'is_bookable',
            'bedrooms', 'bathrooms', 'garages', 'parking_spaces',
            'total_area',
            'main_image_url', 'additional_images',
            'likes_count', 'dislikes_count',
            'average_rating', 'rating_count',
            'uploader_name', 'user_interaction', 'user_rating',
            'owner',  # Full owner object
            'created_at', 'updated_at'
        ]
    
    def get_main_image_url(self, obj):
        return obj.get_main_image_url()
    
    def get_uploader_name(self, obj):
        if obj.owner:
            return obj.owner.get_full_name() or obj.owner.username
        elif obj.company:
            return obj.company.company_name
        return "Unknown"
    
    def get_owner(self, obj):
        """Return owner as a full object for JavaScript"""
        if obj.owner:
            return {
                'id': obj.owner.id,
                'username': obj.owner.username,
                'first_name': obj.owner.first_name,
                'last_name': obj.owner.last_name,
                'full_name': obj.owner.get_full_name() or obj.owner.username,
                'email': obj.owner.email,
                'user_type': getattr(obj.owner, 'user_type', 'user'),
            }
        elif obj.company:
            return {
                'id': obj.company.id,
                'username': obj.company.company_name,
                'first_name': obj.company.company_name,
                'last_name': '',
                'full_name': obj.company.company_name,
                'email': getattr(obj.company, 'email', ''),
                'user_type': 'business',
            }
        return None
    
    def get_user_interaction(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if hasattr(obj, 'user_interaction'):
                return obj.user_interaction
            try:
                interaction = PropertyInteraction.objects.get(
                    property=obj,
                    user=request.user
                )
                return interaction.interaction_type
            except PropertyInteraction.DoesNotExist:
                return None
        return None
    
    def get_user_rating(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if hasattr(obj, 'user_rating'):
                return obj.user_rating
            try:
                rating = PropertyRating.objects.get(
                    property=obj,
                    user=request.user
                )
                return rating.rating
            except PropertyRating.DoesNotExist:
                return None
        return None


class PropertySerializer(serializers.ModelSerializer):
    """Main Property Serializer with nested relationships and OWNER data"""
    
    property_type_name = serializers.CharField(source='property_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    listing_type_display = serializers.CharField(source='get_listing_type_display', read_only=True)
    company_name = serializers.CharField(source='company.company_name', read_only=True, default=None)
    agent_name = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    
    # ===== OWNER FIELD =====
    owner = serializers.SerializerMethodField()
    
    main_image_url = serializers.SerializerMethodField()
    features = PropertyFeatureSerializer(many=True, read_only=True)
    room_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Property
        fields = [
            'id', 'property_reference', 'title', 'description',
            'property_type', 'property_type_name', 'custom_category_name',
            'custom_category_description', 'features',
            'address', 'city', 'state', 'country', 'postal_code',
            'latitude', 'longitude', 'formatted_address', 'place_id',
            'neighborhood', 'landmark', 'map_zoom_level', 'location_data',
            'total_area', 'land_area', 'floor_area', 'total_rooms',
            'total_floors', 'max_occupancy', 'room_count',
            'bedrooms', 'bathrooms', 'garages', 'parking_spaces',
            'amenities', 'base_price', 'price_per_unit', 'price_per_sqm',
            'price_currency', 'booking_unit', 'pricing_structure',
            'pricing_details', 'listing_type', 'listing_type_display',
            'transaction_type', 'listing_date', 'expiry_date',
            'status', 'status_display', 'is_bookable', 'booking_mode',
            'available_from', 'available_until', 'minimum_stay',
            'maximum_stay', 
            'owner', 'owner_name',
            'listing_agent', 'agent_name', 
            'company', 'company_name',
            'is_online', 'agent_status', 'assigned_agent',
            'main_image', 'main_image_url', 'virtual_tour_url',
            'additional_images', 'is_featured', 'is_premium',
            'views_count', 'is_verified', 'is_active',
            'custom_fields', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'property_reference', 'views_count', 
            'listing_date', 'created_at', 'updated_at'
        ]
    
    def get_main_image_url(self, obj):
        return obj.get_main_image_url()
    
    def get_agent_name(self, obj):
        if obj.listing_agent:
            return obj.listing_agent.get_full_name() or obj.listing_agent.username
        return None
    
    def get_owner_name(self, obj):
        if obj.owner:
            return obj.owner.get_full_name() or obj.owner.username
        return None
    
    def get_owner(self, obj):
        """Return owner as a full object"""
        if obj.owner:
            return {
                'id': obj.owner.id,
                'username': obj.owner.username,
                'first_name': obj.owner.first_name,
                'last_name': obj.owner.last_name,
                'full_name': obj.owner.get_full_name() or obj.owner.username,
                'email': obj.owner.email,
                'user_type': getattr(obj.owner, 'user_type', 'user'),
                'is_staff': obj.owner.is_staff,
                'is_superuser': obj.owner.is_superuser,
            }
        elif obj.company:
            return {
                'id': obj.company.id,
                'username': obj.company.company_name,
                'first_name': obj.company.company_name,
                'last_name': '',
                'full_name': obj.company.company_name,
                'email': getattr(obj.company, 'email', ''),
                'user_type': 'business',
            }
        return None
    
    def get_room_count(self, obj):
        return obj.rooms.count()

class PropertyDetailSerializer(PropertySerializer):
    """Detailed serializer with additional analytics"""
    
    analytics = serializers.SerializerMethodField()
    favorite_count = serializers.SerializerMethodField()
    inquiry_count = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    rooms = RoomSerializer(many=True, read_only=True)
    available_dates = serializers.SerializerMethodField()
    
    class Meta(PropertySerializer.Meta):
        fields = PropertySerializer.Meta.fields + [
            'analytics', 'favorite_count', 'inquiry_count', 
            'is_favorited', 'reviews', 'rooms', 'available_dates'
        ]
    
    def get_analytics(self, obj):
        try:
            analytics = obj.analytics
            return {
                'total_views': analytics.total_views,
                'unique_views': analytics.unique_views,
                'total_inquiries': analytics.total_inquiries,
                'total_bookings': analytics.total_bookings,
                'favorites_count': analytics.favorites_count,
                'average_rating': analytics.average_rating,
                'days_on_market': analytics.days_on_market,
                'average_booking_duration': analytics.average_booking_duration
            }
        except PropertyAnalytics.DoesNotExist:
            return None
    
    # ===== FIX THIS METHOD =====
    def get_favorite_count(self, obj):
        # Use wishlists instead of favorited_by
        return obj.wishlists.count()
    
    def get_inquiry_count(self, obj):
        return obj.inquiries.count()
    
    # ===== FIX THIS METHOD =====
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Wishlist.objects.filter(
                user=request.user,
                properties=obj
            ).exists()
        return False
    
    def get_reviews(self, obj):
        reviews = obj.reviews.filter(is_approved=True)[:5]
        return PropertyReviewSerializer(reviews, many=True).data
    
    def get_available_dates(self, obj):
        availability = obj.availability_calendar.filter(
            availability_type='available',
            end_date__gte=timezone.now().date()
        )[:10]
        return [
            {
                'start_date': a.start_date,
                'end_date': a.end_date,
                'special_price': a.special_price
            }
            for a in availability
        ]
    


# ============================================================
# 1. CUSTOM DRF FIELD FOR FLEXIBLE PRICES
# ============================================================
class FlexiblePriceField(serializers.DecimalField):
    """
    A DecimalField that accepts human‑friendly price strings
    (currency symbols, thousand separators, comma decimals, etc.)
    and converts them to a clean Decimal.
    """
    def to_internal_value(self, data):
        if data is None:
            return None
        if isinstance(data, str):
            try:
                data = clean_price_string(data)   # your existing cleaning function
            except Exception:
                raise serializers.ValidationError(
                    f"'{data}' is not a valid price format."
                )
        # If data is already a number, pass through
        return super().to_internal_value(data)


# ============================================================
# 2. PROPERTY CREATE SERIALIZER (FIXED)
# ============================================================
class PropertyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating properties"""
    
    features = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )
    
    # ✅ Explicitly declare price fields with custom field
    base_price = FlexiblePriceField(max_digits=12, decimal_places=2)
    price_per_unit = FlexiblePriceField(
        max_digits=12, decimal_places=2,
        required=False, allow_null=True
    )
    price_per_sqm = FlexiblePriceField(
        max_digits=12, decimal_places=2,
        required=False, allow_null=True
    )
    
    class Meta:
        model = Property
        fields = [
            'title', 'description', 'property_type', 'custom_category_name',
            'custom_category_description', 'features',
            'address', 'city', 'state', 'country', 'postal_code',
            'latitude', 'longitude', 'formatted_address', 'place_id',
            'neighborhood', 'landmark',
            'total_area', 'land_area', 'floor_area', 'total_rooms',
            'total_floors', 'max_occupancy', 'bedrooms', 'bathrooms',
            'garages', 'parking_spaces', 'amenities',
            'base_price', 'price_per_unit', 'price_per_sqm',
            'price_currency', 'booking_unit', 'pricing_structure',
            'pricing_details', 'listing_type', 'transaction_type',
            'expiry_date', 'status', 'is_bookable', 'booking_mode',
            'available_from', 'available_until', 'minimum_stay',
            'maximum_stay', 'main_image', 'virtual_tour_url',
            'additional_images', 'is_featured', 'is_premium',
            'is_active', 'custom_fields'
        ]
    
    def create(self, validated_data):
        features = validated_data.pop('features', [])
        property_obj = Property.objects.create(**validated_data)
        if features:
            property_obj.features.set(features)
        return property_obj


# ============================================================
# 3. PROPERTY UPDATE SERIALIZER (FIXED)
# ============================================================
class PropertyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating properties"""
    
    features = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )
    main_image_url = serializers.SerializerMethodField()
    property_type_name = serializers.CharField(source='property_type.name', read_only=True)
    
    # ✅ Explicitly declare price fields with custom field
    base_price = FlexiblePriceField(max_digits=12, decimal_places=2)
    price_per_unit = FlexiblePriceField(
        max_digits=12, decimal_places=2,
        required=False, allow_null=True
    )
    price_per_sqm = FlexiblePriceField(
        max_digits=12, decimal_places=2,
        required=False, allow_null=True
    )
    
    class Meta:
        model = Property
        fields = [
            'id', 'property_reference', 'title', 'description',
            'property_type', 'property_type_name', 'custom_category_name',
            'custom_category_description', 'features',
            'address', 'city', 'state', 'country', 'postal_code',
            'latitude', 'longitude', 'formatted_address', 'place_id',
            'neighborhood', 'landmark',
            'total_area', 'land_area', 'floor_area', 'total_rooms',
            'total_floors', 'max_occupancy', 'bedrooms', 'bathrooms',
            'garages', 'parking_spaces', 'amenities',
            'base_price', 'price_per_unit', 'price_per_sqm',
            'price_currency', 'booking_unit', 'pricing_structure',
            'pricing_details', 'listing_type', 'transaction_type',
            'expiry_date', 'status', 'is_bookable', 'booking_mode',
            'available_from', 'available_until', 'minimum_stay',
            'maximum_stay', 'main_image', 'main_image_url', 'virtual_tour_url',
            'additional_images', 'is_featured', 'is_premium',
            'is_active', 'custom_fields', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'property_reference', 'views_count', 
            'listing_date', 'created_at', 'updated_at'
        ]
    
    def get_main_image_url(self, obj):
        return obj.get_main_image_url()
    
    def update(self, instance, validated_data):
        features = validated_data.pop('features', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if features is not None:
            instance.features.set(features)
        return instance


# ============================================
# 4. BOOKING SERIALIZERS
# ============================================

class BookingSerializer(serializers.ModelSerializer):
    guest_name = serializers.SerializerMethodField()
    property_title = serializers.CharField(source='property.title', read_only=True)
    property_reference = serializers.CharField(source='property.property_reference', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True, default=None)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_reference', 'property', 'property_title',
            'property_reference', 'room', 'room_number', 'guest',
            'guest_name', 'guest_details', 'business',
            'check_in', 'check_out', 'actual_check_in', 'actual_check_out',
            'duration_days', 'subtotal', 'taxes', 'fees', 'discount',
            'total_amount', 'currency', 'payment_status',
            'payment_status_display', 'payment_method', 'payment_reference',
            'status', 'status_display', 'number_of_guests', 'guest_names',
            'special_requests', 'notes', 'booking_mode',
            'assigned_driver', 'driver_status', 'pickup_location',
            'dropoff_location', 'current_location', 'route_path',
            'estimated_pickup_time', 'actual_pickup_time',
            'trip_duration', 'trip_distance', 'cancellation_reason',
            'cancellation_date', 'cancellation_fee', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'booking_reference', 'created_at', 'updated_at']
    
    def get_guest_name(self, obj):
        if obj.guest:
            return obj.guest.get_full_name() or obj.guest.username
        return 'Guest'


class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bookings"""
    
    class Meta:
        model = Booking
        fields = [
            'property', 'room', 'guest_details', 'business',
            'check_in', 'check_out', 'number_of_guests', 'guest_names',
            'special_requests', 'notes', 'booking_mode',
            'pickup_location', 'dropoff_location'
        ]
    
    def validate(self, data):
        if data['check_in'] >= data['check_out']:
            raise serializers.ValidationError("Check-out must be after check-in")
        
        property_obj = data['property']
        if not property_obj.is_bookable:
            raise serializers.ValidationError("This property is not available for booking")
        
        overlapping = Booking.objects.filter(
            property=data['property'],
            status__in=['pending', 'confirmed', 'checked_in'],
            check_in__lt=data['check_out'],
            check_out__gt=data['check_in']
        )
        if data.get('room'):
            overlapping = overlapping.filter(room=data['room'])
        
        if overlapping.exists():
            raise serializers.ValidationError("This property/room is already booked for the selected dates")
        
        return data
    
    def create(self, validated_data):
        property_obj = validated_data['property']
        check_in = validated_data['check_in']
        check_out = validated_data['check_out']
        
        duration = (check_out - check_in).days
        if duration <= 0:
            duration = 1
        validated_data['duration_days'] = duration
        
        base_price = property_obj.base_price or 0
        subtotal = base_price * duration
        
        if validated_data.get('room') and validated_data['room'].price_per_night:
            room_price = validated_data['room'].price_per_night
            subtotal = room_price * duration
        
        validated_data['subtotal'] = subtotal
        validated_data['total_amount'] = subtotal
        
        return super().create(validated_data)


# ============================================
# 5. DRIVER LOCATION SERIALIZER
# ============================================

class DriverLocationSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.username', read_only=True)
    
    class Meta:
        model = DriverLocation
        fields = [
            'id', 'driver', 'driver_name', 'latitude', 'longitude',
            'accuracy', 'speed', 'heading', 'is_active',
            'updated_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================
# 6. AVAILABILITY CALENDAR SERIALIZER
# ============================================

class AvailabilityCalendarSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source='property.title', read_only=True, default=None)
    room_number = serializers.CharField(source='room.room_number', read_only=True, default=None)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default=None)
    availability_type_display = serializers.CharField(source='get_availability_type_display', read_only=True)
    
    class Meta:
        model = AvailabilityCalendar
        fields = [
            'id', 'property', 'property_title', 'room', 'room_number',
            'start_date', 'end_date', 'availability_type',
            'availability_type_display', 'special_price',
            'special_price_note', 'notes', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================
# 7. BOOKING INQUIRY SERIALIZER
# ============================================

class BookingInquirySerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source='property.title', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True, default=None)
    full_name = serializers.SerializerMethodField()
    inquiry_type_display = serializers.CharField(source='get_inquiry_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = BookingInquiry
        fields = [
            'id', 'property', 'property_title', 'room', 'room_number',
            'first_name', 'last_name', 'full_name', 'email', 'phone',
            'company', 'user', 'inquiry_type', 'inquiry_type_display',
            'message', 'preferred_date_from', 'preferred_date_to',
            'number_of_guests', 'status', 'status_display', 'response',
            'responded_by', 'responded_at', 'follow_up_date',
            'follow_up_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


# ============================================
# 8. PROPERTY REVIEW SERIALIZER
# ============================================

class PropertyReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    property_title = serializers.CharField(source='property.title', read_only=True)
    booking_reference = serializers.CharField(source='booking.booking_reference', read_only=True, default=None)
    
    class Meta:
        model = PropertyReview
        fields = [
            'id', 'property', 'property_title', 'booking', 'booking_reference',
            'user', 'user_name', 'overall_rating', 'cleanliness',
            'communication', 'location', 'value_for_money', 'amenities',
            'review_title', 'review_text', 'pros', 'cons', 'review_images',
            'is_verified', 'is_public', 'is_approved', 'is_reported',
            'report_reason', 'owner_response', 'owner_response_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================
# 9. WISHLIST SERIALIZER
# ============================================

class WishlistSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    property_count = serializers.SerializerMethodField()
    room_count = serializers.SerializerMethodField()
    properties = PropertyListSerializer(many=True, read_only=True)
    rooms = RoomSerializer(many=True, read_only=True)
    
    class Meta:
        model = Wishlist
        fields = [
            'id', 'user', 'user_name', 'name', 'description',
            'properties', 'rooms', 'property_count', 'room_count',
            'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_property_count(self, obj):
        return obj.properties.count()
    
    def get_room_count(self, obj):
        return obj.rooms.count()


# ============================================
# 10. PROPERTY ANALYTICS SERIALIZER
# ============================================

class PropertyAnalyticsSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source='property.title', read_only=True)
    property_reference = serializers.CharField(source='property.property_reference', read_only=True)
    
    class Meta:
        model = PropertyAnalytics
        fields = [
            'id', 'property', 'property_title', 'property_reference',
            'total_views', 'unique_views', 'views_by_device',
            'views_by_country', 'total_inquiries',
            'inquiry_conversion_rate', 'total_bookings',
            'total_revenue', 'average_occupancy_rate',
            'favorites_count', 'shares_count', 'reviews_count',
            'average_rating', 'days_on_market',
            'average_booking_duration', 'views_last_30_days',
            'inquiries_last_30_days', 'bookings_last_30_days',
            'revenue_last_30_days', 'seasonal_data', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']


# ============================================
# 11. MAINTENANCE SERIALIZERS
# ============================================

class MaintenanceCategorySerializer(serializers.ModelSerializer):
    request_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MaintenanceCategory
        fields = ['id', 'name', 'icon', 'color', 'description', 'is_active', 'request_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_request_count(self, obj):
        return obj.requests.count()


class MaintenanceCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = MaintenanceComment
        fields = ['id', 'request', 'author', 'author_name', 'content', 'time_ago', 'created_at']
        read_only_fields = ['author', 'created_at']
    
    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username
    
    def get_time_ago(self, obj):
        diff = timezone.now() - obj.created_at
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds // 3600 > 0:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds // 60 > 0:
            return f"{diff.seconds // 60}m ago"
        return "Just now"


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    tenant_name = serializers.SerializerMethodField()
    comments = MaintenanceCommentSerializer(many=True, read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = MaintenanceRequest
        fields = [
            'id', 'property', 'tenant', 'tenant_name',
            'category', 'category_name', 'category_color', 'category_icon',
            'title', 'description', 'priority', 'priority_display',
            'status', 'status_display', 'location',
            'preferred_date', 'estimated_cost', 'actual_cost',
            'notes', 'image', 'comments', 'comments_count',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'completed_at']
    
    def get_tenant_name(self, obj):
        if obj.tenant:
            return obj.tenant.get_full_name() or obj.tenant.username
        return None


# ============================================
# 12. USER MINIMAL SERIALIZER
# ============================================

class UserMinimalSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'full_name']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


# ============================================
# 13. PROPERTY INTERACTION SERIALIZER
# ============================================

class PropertyInteractionSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    interaction_type_display = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyInteraction
        fields = [
            'id', 'property', 'user', 'interaction_type',
            'interaction_type_display', 'created_at', 'time_ago'
        ]
        read_only_fields = ['id', 'user', 'created_at']
    
    def get_interaction_type_display(self, obj):
        return dict(PropertyInteraction.INTERACTION_TYPES).get(obj.interaction_type, obj.interaction_type)
    
    def get_time_ago(self, obj):
        diff = timezone.now() - obj.created_at
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        return "Just now"


# ============================================
# 14. PROPERTY RATING SERIALIZER
# ============================================

class PropertyRatingSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    user_avatar = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    rating_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyRating
        fields = [
            'id', 'property', 'user', 'user_avatar',
            'rating', 'rating_display', 'review',
            'created_at', 'time_ago'
        ]
        read_only_fields = ['id', 'user', 'created_at']
    
    def get_user_avatar(self, obj):
        if obj.user:
            return obj.user.username[0].upper()
        return 'U'
    
    def get_time_ago(self, obj):
        diff = timezone.now() - obj.created_at
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        return "Just now"
    
    def get_rating_display(self, obj):
        return dict(PropertyRating.RATING_CHOICES).get(obj.rating, str(obj.rating))


# ============================================
# 15. COUNTRY SERIALIZER
# ============================================

class CountrySerializer(serializers.ModelSerializer):
    """Serializer for Country model"""
    
    class Meta:
        model = Country
        fields = [
            'id', 'name', 'code', 'code3', 'calling_code', 'flag', 'is_active'
        ]
        read_only_fields = ['created_at', 'updated_at']


# ============================================
# 16. AGENT PROFILE SERIALIZER - COMPLETE
# ============================================

class AgentProfileSerializer(serializers.ModelSerializer):
    """
    Complete Agent Profile Serializer with smart URL/phone handling
    and internal messaging priority
    """
    
    # User related fields
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    # Country fields
    country = CountrySerializer(read_only=True)
    country_id = serializers.PrimaryKeyRelatedField(
        source='country',
        queryset=Country.objects.filter(is_active=True),
        write_only=True,
        required=False,
        allow_null=True
    )
    license_country = CountrySerializer(read_only=True)
    license_country_id = serializers.PrimaryKeyRelatedField(
        source='license_country',
        queryset=Country.objects.filter(is_active=True),
        write_only=True,
        required=False,
        allow_null=True
    )
    
    # Display fields with smart formatting
    profile_image_url = serializers.SerializerMethodField()
    rating_stars = serializers.SerializerMethodField()
    rating_stars_html = serializers.SerializerMethodField()
    
    # Smart contact methods (ALWAYS includes internal messaging first)
    contact_methods = serializers.SerializerMethodField()
    
    # Smart social links
    active_social_links = serializers.SerializerMethodField()
    whatsapp_link = serializers.SerializerMethodField()
    telegram_link = serializers.SerializerMethodField()
    signal_link = serializers.SerializerMethodField()
    viber_link = serializers.SerializerMethodField()
    line_link = serializers.SerializerMethodField()
    kakao_link = serializers.SerializerMethodField()
    phone_display = serializers.SerializerMethodField()
    detected_country = serializers.SerializerMethodField()
    
    # Agent type and specializations
    agent_type_display = serializers.SerializerMethodField()
    all_specializations = serializers.SerializerMethodField()
    specialization_display = serializers.SerializerMethodField()
    
    # Share data for social sharing
    share_data = serializers.SerializerMethodField()
    
    class Meta:
        model = AgentProfile
        fields = [
            # IDs and User
            'id', 'user', 'user_id', 'username', 'email', 'full_name',
            
            # Basic Info
            'display_name', 'agent_type', 'custom_agent_type', 'agent_type_display',
            'agency_name', 'agency_logo',
            
            # Contact (Raw)
            'phone_primary', 'phone_secondary', 'email_primary', 'email_secondary', 'website',
            'business_address', 'city', 'state_province', 'postal_code',
            
            # Country
            'country', 'country_id', 'detected_country',
            
            # Contact (Formatted/Smart)
            'phone_display', 'whatsapp_link', 'telegram_link',
            'signal_link', 'viber_link', 'line_link', 'kakao_link',
            
            # Social Media (Raw URLs)
            'linkedin_url', 'twitter_url', 'facebook_url', 'instagram_url', 
            'youtube_url', 'tiktok_url', 'pinterest_url', 'snapchat_url',
            'reddit_url', 'whatsapp_number', 'telegram_username', 'wechat_id',
            'signal_number', 'viber_number', 'line_id', 'kakao_id',
            'discord_username',
            
            # Real Estate Platforms
            'zillow_url', 'realtor_url', 'trulia_url', 'redfin_url', 'homescom_url',
            'rightmove_url', 'zoopla_url', 'onthemarket_url', 'primelocation_url',
            'property24_url', 'privateproperty_url',
            'realestatecomau_url', 'domaincomau_url',
            'propertyfinder_url', 'bayut_url', 'dubizzle_url',
            'propertyguru_url', 'rumah123_url', 'ninety_nine_co_url',
            'vivareal_url', 'properati_url',
            'indeed_url', 'glassdoor_url', 'angellist_url', 'crunchbase_url',
            
            # Social Media (Formatted)
            'active_social_links',
            
            # Contact Methods (Smart - Internal Messaging First)
            'contact_methods',
            
            # Professional
            'license_number', 'license_country', 'license_country_id',
            'ffc_number', 'years_experience',
            'specializations', 'custom_specializations', 
            'all_specializations', 'specialization_display',
            'languages_spoken',
            'bio', 'achievements', 'services_offered', 'areas_served',
            
            # Media
            'profile_image', 'cover_image', 'profile_image_url',
            
            # Ratings
            'average_rating', 'total_reviews', 
            'rating_stars', 'rating_stars_html',
            'response_time', 'response_rate',
            
            # Status
            'is_verified', 'is_featured', 'is_online',
            
            # Stats
            'properties_sold', 'properties_rented', 'properties_listed',
            'total_deals', 'total_volume',
            
            # Settings
            'show_social_links', 'show_contact_details', 
            'auto_accept_messages', 'receive_notifications',
            'timezone',
            
            # Share Data
            'share_data',
            
            # Timestamps
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return None
    
    def get_profile_image_url(self, obj):
        return obj.get_profile_image_url()
    
    def get_rating_stars(self, obj):
        return obj.get_rating_stars()
    
    def get_rating_stars_html(self, obj):
        return obj.get_rating_stars_html()
    
    def get_phone_display(self, obj):
        return obj.get_phone_display()
    
    def get_whatsapp_link(self, obj):
        return obj.get_whatsapp_link()
    
    def get_telegram_link(self, obj):
        return obj.get_telegram_link()
    
    def get_signal_link(self, obj):
        return obj.get_signal_link()
    
    def get_viber_link(self, obj):
        return obj.get_viber_link()
    
    def get_line_link(self, obj):
        return obj.get_line_link()
    
    def get_kakao_link(self, obj):
        return obj.get_kakao_link()
    
    def get_detected_country(self, obj):
        if obj.phone_primary:
            country = obj.detect_country_from_number(obj.phone_primary)
            if country:
                return CountrySerializer(country).data
        return None
    
    def get_active_social_links(self, obj):
        return obj.get_active_social_links()
    
    def get_agent_type_display(self, obj):
        return obj.get_agent_type_display()
    
    def get_all_specializations(self, obj):
        return obj.get_all_specializations()
    
    def get_specialization_display(self, obj):
        return obj.get_specialization_display()
    
    def get_contact_methods(self, obj):
        return obj.get_contact_methods()
    
    def get_share_data(self, obj):
        return obj.get_social_share_data()
    
    def validate_phone_number(self, value):
        if not value:
            return value
        cleaned = ''.join(filter(str.isdigit, value))
        if not cleaned:
            return value
        country = Country.detect_country(cleaned)
        if not country:
            if len(cleaned) < 7:
                raise serializers.ValidationError("Phone number is too short. Please enter a valid number with country code.")
        return value
    
    def validate_url(self, value):
        if not value:
            return value
        value = value.strip()
        if '.' in value and not value.startswith(('http://', 'https://')):
            if not value.startswith('www.'):
                value = 'www.' + value
            value = 'https://' + value
        return value
    
    def validate(self, data):
        if data.get('agent_type') == 'custom' and not data.get('custom_agent_type'):
            raise serializers.ValidationError({
                'custom_agent_type': 'Please specify your custom agent type.'
            })
        specializations = data.get('specializations', [])
        if 'custom' in specializations and not data.get('custom_specializations'):
            raise serializers.ValidationError({
                'custom_specializations': 'Please specify your custom specializations.'
            })
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['user'] = request.user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Clean phone numbers
        if 'phone_primary' in validated_data:
            validated_data['phone_primary'] = instance.clean_phone_number(
                validated_data['phone_primary']
            ) or validated_data['phone_primary']
        
        if 'phone_secondary' in validated_data:
            validated_data['phone_secondary'] = instance.clean_phone_number(
                validated_data['phone_secondary']
            ) or validated_data['phone_secondary']
        
        if 'whatsapp_number' in validated_data:
            validated_data['whatsapp_number'] = instance.clean_phone_number(
                validated_data['whatsapp_number']
            ) or validated_data['whatsapp_number']
        
        if 'signal_number' in validated_data:
            validated_data['signal_number'] = instance.clean_phone_number(
                validated_data['signal_number']
            ) or validated_data['signal_number']
        
        if 'viber_number' in validated_data:
            validated_data['viber_number'] = instance.clean_phone_number(
                validated_data['viber_number']
            ) or validated_data['viber_number']
        
        # Clean URLs
        url_fields = [
            'website', 'linkedin_url', 'twitter_url', 'facebook_url', 
            'instagram_url', 'youtube_url', 'tiktok_url', 'pinterest_url',
            'snapchat_url', 'reddit_url',
            'zillow_url', 'realtor_url', 'trulia_url', 'redfin_url', 'homescom_url',
            'rightmove_url', 'zoopla_url', 'onthemarket_url', 'primelocation_url',
            'property24_url', 'privateproperty_url',
            'realestatecomau_url', 'domaincomau_url',
            'propertyfinder_url', 'bayut_url', 'dubizzle_url',
            'propertyguru_url', 'rumah123_url', 'ninety_nine_co_url',
            'vivareal_url', 'properati_url',
            'indeed_url', 'glassdoor_url', 'angellist_url', 'crunchbase_url'
        ]
        
        for field in url_fields:
            if field in validated_data:
                validated_data[field] = instance.clean_url(
                    validated_data[field]
                ) or validated_data[field]
        
        # Clean Telegram username
        if 'telegram_username' in validated_data:
            username = validated_data['telegram_username'].strip()
            if username.startswith('@'):
                username = username[1:]
            validated_data['telegram_username'] = username
        
        # Clean LINE ID
        if 'line_id' in validated_data:
            line_id = validated_data['line_id'].strip()
            if line_id.startswith('@'):
                line_id = line_id[1:]
            validated_data['line_id'] = line_id
        
        # Detect country from phone
        if not validated_data.get('country') and validated_data.get('phone_primary'):
            country = instance.detect_country_from_number(
                validated_data['phone_primary']
            )
            if country:
                validated_data['country'] = country
        
        return super().update(instance, validated_data)


class AgentProfileListSerializer(serializers.ModelSerializer):
    """Minimal serializer for agent listings (search results)"""
    
    profile_image_url = serializers.SerializerMethodField()
    rating_stars = serializers.SerializerMethodField()
    agent_type_display = serializers.SerializerMethodField()
    specialization_display = serializers.SerializerMethodField()
    contact_methods = serializers.SerializerMethodField()
    country_name = serializers.CharField(source='country.name', read_only=True, default='')
    country_flag = serializers.CharField(source='country.flag', read_only=True, default='')
    
    class Meta:
        model = AgentProfile
        fields = [
            'id', 'display_name', 'agency_name', 'agent_type_display',
            'city', 'state_province', 'country_name', 'country_flag',
            'profile_image_url', 'average_rating', 'total_reviews',
            'rating_stars', 'specialization_display',
            'total_deals', 'years_experience',
            'is_verified', 'is_featured', 'is_online',
            'contact_methods'
        ]
    
    def get_profile_image_url(self, obj):
        return obj.get_profile_image_url()
    
    def get_rating_stars(self, obj):
        return obj.get_rating_stars()
    
    def get_agent_type_display(self, obj):
        return obj.get_agent_type_display()
    
    def get_specialization_display(self, obj):
        return obj.get_specialization_display()
    
    def get_contact_methods(self, obj):
        methods = []
        if obj.user and obj.user.id:
            methods.append({
                'type': 'message',
                'label': 'Message',
                'value': str(obj.user.id),
                'icon': 'fas fa-comment',
                'is_primary': True,
                'internal': True
            })
        whatsapp_link = obj.get_whatsapp_link()
        if whatsapp_link:
            methods.append({
                'type': 'whatsapp',
                'label': 'WhatsApp',
                'value': whatsapp_link,
                'icon': 'fab fa-whatsapp',
                'is_primary': False,
                'internal': False
            })
        if obj.phone_primary:
            methods.append({
                'type': 'phone',
                'label': 'Call',
                'value': obj.phone_primary,
                'icon': 'fas fa-phone',
                'is_primary': False,
                'internal': False
            })
        return methods


class AgentProfileDetailSerializer(AgentProfileSerializer):
    """Full detail serializer with all social links and reviews"""
    
    reviews = serializers.SerializerMethodField()
    review_summary = serializers.SerializerMethodField()
    recent_properties = serializers.SerializerMethodField()
    connection_status = serializers.SerializerMethodField()
    all_countries = serializers.SerializerMethodField()
    
    class Meta(AgentProfileSerializer.Meta):
        fields = AgentProfileSerializer.Meta.fields + [
            'reviews', 'review_summary', 'recent_properties', 
            'connection_status', 'all_countries'
        ]
    
    def get_reviews(self, obj):
        request = self.context.get('request')
        reviews = obj.reviews.filter(is_public=True, is_approved=True)[:5]
        return AgentReviewSerializer(reviews, many=True, context={'request': request}).data
    
    def get_review_summary(self, obj):
        reviews = obj.reviews.filter(is_public=True, is_approved=True)
        total = reviews.count()
        if total == 0:
            return {
                'total': 0,
                'average': 0,
                'distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        distribution = {}
        for i in range(1, 6):
            distribution[i] = reviews.filter(rating=i).count()
        return {
            'total': total,
            'average': obj.average_rating,
            'distribution': distribution
        }
    
    def get_recent_properties(self, obj):
        properties = Property.objects.filter(
            owner=obj.user,
            is_active=True
        ).order_by('-created_at')[:3]
        return [{
            'id': str(p.id),
            'title': p.title,
            'price': f"{p.price_currency} {p.base_price}" if p.base_price else None,
            'image': p.get_main_image_url(),
            'city': p.city,
            'country': p.country,
            'status': p.status
        } for p in properties]
    
    def get_connection_status(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        try:
            connection = AgentConnection.objects.get(agent=obj, user=request.user)
            return {
                'is_connected': True,
                'connection_type': connection.connection_type,
                'since': connection.created_at
            }
        except AgentConnection.DoesNotExist:
            return {
                'is_connected': False,
                'connection_type': None
            }
    
    def get_all_countries(self, obj):
        countries = Country.objects.filter(is_active=True)
        return CountrySerializer(countries, many=True).data


class AgentReviewSerializer(serializers.ModelSerializer):
    """Serializer for Agent Reviews"""
    
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    agent_name = serializers.CharField(source='agent.display_name', read_only=True)
    stars_display = serializers.SerializerMethodField()
    rating_display = serializers.SerializerMethodField()
    
    class Meta:
        model = AgentReview
        fields = [
            'id', 'agent', 'agent_name', 'user', 'user_id', 'user_avatar',
            'rating', 'professionalism', 'communication', 
            'knowledge', 'responsiveness', 'negotiation',
            'review_text', 'review_title',
            'property', 'booking',
            'is_verified', 'is_public', 'is_approved',
            'agent_response', 'agent_response_at',
            'stars_display', 'rating_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_user_avatar(self, obj):
        if obj.user:
            return obj.user.username[0].upper() if obj.user.username else 'U'
        return 'U'
    
    def get_stars_display(self, obj):
        return obj.get_stars()
    
    def get_rating_display(self, obj):
        rating_map = {
            1: 'Poor',
            2: 'Fair',
            3: 'Good',
            4: 'Very Good',
            5: 'Excellent'
        }
        return rating_map.get(obj.rating, '')
    
    def validate(self, data):
        if 'rating' not in data and not self.instance:
            raise serializers.ValidationError({
                'rating': 'Rating is required.'
            })
        return data


class AgentConnectionSerializer(serializers.ModelSerializer):
    """Serializer for Agent Connections"""
    
    user = serializers.StringRelatedField(read_only=True)
    agent_name = serializers.CharField(source='agent.display_name', read_only=True)
    agent_avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = AgentConnection
        fields = [
            'id', 'agent', 'agent_name', 'agent_avatar',
            'user', 'connection_type', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_agent_avatar(self, obj):
        if obj.agent:
            return obj.agent.get_profile_image_url()
        return None


class AgentSocialShareSerializer(serializers.ModelSerializer):
    """Serializer for tracking social shares"""
    
    agent_name = serializers.CharField(source='agent.display_name', read_only=True)
    shared_by_name = serializers.CharField(source='shared_by.username', read_only=True)
    property_title = serializers.CharField(source='property.title', read_only=True, default=None)
    platform_display = serializers.SerializerMethodField()
    country_name = serializers.CharField(source='country.name', read_only=True, default='')
    
    class Meta:
        model = AgentSocialShare
        fields = [
            'id', 'agent', 'agent_name', 'property', 'property_title',
            'platform', 'platform_display',
            'shared_by', 'shared_by_name',
            'shared_at', 'ip_address', 'user_agent',
            'country', 'country_name'
        ]
        read_only_fields = ['shared_at']
    
    def get_platform_display(self, obj):
        platform_map = dict(AgentSocialShare.PLATFORM_CHOICES)
        return platform_map.get(obj.platform, obj.platform)


# ============================================
# 17. HELPER FUNCTIONS
# ============================================

def get_rating_distribution(property_obj):
    cache_key = f'rating_dist_{property_obj.id}'
    distribution = cache.get(cache_key)
    if distribution is None:
        distribution = {}
        counts = PropertyRating.objects.filter(
            property=property_obj
        ).values('rating').annotate(
            count=Count('id')
        ).order_by('rating')
        for item in counts:
            distribution[str(item['rating'])] = item['count']
        for i in range(1, 6):
            if str(i) not in distribution:
                distribution[str(i)] = 0
        cache.set(cache_key, distribution, 300)
    return distribution


def get_user_interaction(property_obj, user):
    if user and user.is_authenticated:
        try:
            interaction = PropertyInteraction.objects.get(
                property=property_obj,
                user=user
            )
            return interaction.interaction_type
        except PropertyInteraction.DoesNotExist:
            pass
    return None


def get_user_rating(property_obj, user):
    if user and user.is_authenticated:
        try:
            rating = PropertyRating.objects.get(
                property=property_obj,
                user=user
            )
            return rating.rating
        except PropertyRating.DoesNotExist:
            pass
    return None


# ============================================
# 18. REQUEST SERIALIZERS
# ============================================

class ToggleInteractionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=['like', 'dislike', 'unlike', 'undislike'],
        required=True
    )


class RatePropertySerializer(serializers.Serializer):
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=True
    )
    review = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class BatchInteractionSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True
    )
    action = serializers.ChoiceField(
        choices=['like', 'dislike', 'unlike', 'undislike'],
        required=True
    )
    
    def validate_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one property ID is required")
        if len(value) > 100:
            raise serializers.ValidationError("Maximum 100 properties per batch request")
        return value