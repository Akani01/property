from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from .models import (
    PropertyCategory, PropertyType, PropertyFeature, Property,
    Room, Booking, DriverLocation, AvailabilityCalendar,
    BookingInquiry, PropertyReview, Wishlist, PropertyAnalytics
)
from hiring.models import BusinessProfile, CustomUser, ApplicantProfile


# ============================================
# 1. CATEGORY SERIALIZERS
# ============================================

class PropertyCategorySerializer(serializers.ModelSerializer):
    """Serializer for dynamic property categories"""
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
    """Serializer for property types"""
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
    """Serializer for property features"""
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
    """Serializer for rooms/units"""
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
# 3. PROPERTY SERIALIZERS
# ============================================

class PropertyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing properties"""
    property_type_name = serializers.CharField(source='property_type.name', read_only=True)
    company_name = serializers.CharField(source='company.company_name', read_only=True, default=None)
    main_image_url = serializers.SerializerMethodField()
    status_color = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Property
        fields = [
            'id', 'property_reference', 'title', 'property_type_name',
            'status', 'status_color', 'city', 'base_price', 'price_currency',
            'listing_type', 'bedrooms', 'bathrooms', 'company_name',
            'main_image_url', 'is_featured', 'is_premium', 'is_online',
            'views_count', 'created_at'
        ]
    
    def get_main_image_url(self, obj):
        return obj.get_main_image_url()


class PropertySerializer(serializers.ModelSerializer):
    """Main Property Serializer with nested relationships"""
    property_type_name = serializers.CharField(source='property_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    listing_type_display = serializers.CharField(source='get_listing_type_display', read_only=True)
    company_name = serializers.CharField(source='company.company_name', read_only=True, default=None)
    agent_name = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
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
            'maximum_stay', 'owner', 'owner_name', 'listing_agent',
            'agent_name', 'company', 'company_name',
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
    
    def get_favorite_count(self, obj):
        return obj.favorited_by.count()
    
    def get_inquiry_count(self, obj):
        return obj.inquiries.count()
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Wishlist.objects.filter(
                user=request.user,
                properties=obj
            ).exists()
        return False
    
    def get_reviews(self, obj):
        from .serializers import PropertyReviewSerializer
        reviews = obj.reviews.filter(is_approved=True)[:5]
        return PropertyReviewSerializer(reviews, many=True).data
    
    def get_available_dates(self, obj):
        # Get availability calendar entries
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


class PropertyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating properties"""
    features = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
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
    """Serializer for bookings"""
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
        read_only_fields = [
            'id', 'booking_reference', 'created_at', 'updated_at'
        ]
    
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
        # Validate check_in and check_out
        if data['check_in'] >= data['check_out']:
            raise serializers.ValidationError(
                "Check-out must be after check-in"
            )
        
        # Check availability
        property_obj = data['property']
        if not property_obj.is_bookable:
            raise serializers.ValidationError(
                "This property is not available for booking"
            )
        
        # Check for overlapping bookings
        overlapping = Booking.objects.filter(
            property=data['property'],
            status__in=['pending', 'confirmed', 'checked_in'],
            check_in__lt=data['check_out'],
            check_out__gt=data['check_in']
        )
        if data.get('room'):
            overlapping = overlapping.filter(room=data['room'])
        
        if overlapping.exists():
            raise serializers.ValidationError(
                "This property/room is already booked for the selected dates"
            )
        
        return data
    
    def create(self, validated_data):
        # Calculate total amount
        property_obj = validated_data['property']
        check_in = validated_data['check_in']
        check_out = validated_data['check_out']
        
        # Calculate duration in days
        duration = (check_out - check_in).days
        if duration <= 0:
            duration = 1
        validated_data['duration_days'] = duration
        
        # Calculate pricing
        base_price = property_obj.base_price or 0
        subtotal = base_price * duration
        
        # Apply room pricing if room is specified
        if validated_data.get('room') and validated_data['room'].price_per_night:
            room_price = validated_data['room'].price_per_night
            subtotal = room_price * duration
        
        validated_data['subtotal'] = subtotal
        validated_data['total_amount'] = subtotal  # Add taxes/fees later
        
        return super().create(validated_data)


# ============================================
# 5. REAL-TIME TRACKING SERIALIZERS
# ============================================

class DriverLocationSerializer(serializers.ModelSerializer):
    """Serializer for driver locations"""
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
    """Serializer for availability calendar"""
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
    """Serializer for booking inquiries"""
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
# 8. REVIEW SERIALIZER
# ============================================

class PropertyReviewSerializer(serializers.ModelSerializer):
    """Serializer for property reviews"""
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
    """Serializer for wishlists"""
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
# 10. ANALYTICS SERIALIZER
# ============================================

class PropertyAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for property analytics"""
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