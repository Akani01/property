from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from django.db.models import Count, Avg
from django.core.cache import cache
from .models import *
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
# realestate/serializers.py - FIXED PropertyListSerializer

class PropertyListSerializer(serializers.ModelSerializer):
    """List view serializer with user interactions"""
    
    # These are the model fields
    likes_count = serializers.IntegerField(read_only=True, default=0)
    dislikes_count = serializers.IntegerField(read_only=True, default=0)
    average_rating = serializers.FloatField(read_only=True, default=0.0)
    rating_count = serializers.IntegerField(read_only=True, default=0)
    
    # Additional fields
    main_image_url = serializers.SerializerMethodField()
    uploader_name = serializers.SerializerMethodField()
    user_interaction = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    
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
    
    def get_user_interaction(self, obj):
        """Get current user's interaction"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Check if we have the interaction from the view
            if hasattr(obj, 'user_interaction'):
                return obj.user_interaction
            
            # Fallback: direct database query
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
        """Get current user's rating"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Check if we have the rating from the view
            if hasattr(obj, 'user_rating'):
                return obj.user_rating
            
            # Fallback: direct database query
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

# serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import MaintenanceCategory, MaintenanceRequest, MaintenanceComment

User = get_user_model()

class MaintenanceCategorySerializer(serializers.ModelSerializer):
    """Simple category serializer with CRUD operations"""
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
    """Simple maintenance request serializer"""
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


class PropertyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyType
        fields = ['id', 'name', 'icon', 'created_at']


# realestate/serializers.py - Add this at the end

class PropertyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating properties with image support"""
    features = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )
    main_image_url = serializers.SerializerMethodField()
    property_type_name = serializers.CharField(source='property_type.name', read_only=True)
    
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


# ============================================================
# 1. USER MINIMAL SERIALIZER (For nested data)
# ============================================================

class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for nested responses"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'full_name']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


# ============================================================
# 2. PROPERTY INTERACTION SERIALIZER (Like/Dislike)
# ============================================================

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
        from django.utils import timezone
        diff = timezone.now() - obj.created_at
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        return "Just now"


# ============================================================
# 3. PROPERTY RATING SERIALIZER
# ============================================================

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
        from django.utils import timezone
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


# ============================================================
# 4. RATING STATISTICS SERIALIZER
# ============================================================

class RatingStatisticsSerializer(serializers.Serializer):
    """Rating statistics for a property"""
    average = serializers.FloatField()
    count = serializers.IntegerField()
    distribution = serializers.DictField(child=serializers.IntegerField())
    user_rating = serializers.IntegerField(required=False, allow_null=True)


# ============================================================
# 5. INTERACTION TOGGLE SERIALIZER (For requests)
# ============================================================

class ToggleInteractionSerializer(serializers.Serializer):
    """Serializer for like/dislike toggle requests"""
    action = serializers.ChoiceField(
        choices=['like', 'dislike', 'unlike', 'undislike'],
        required=True,
        help_text="Action to perform: like, dislike, unlike, or undislike"
    )


# ============================================================
# 6. RATE PROPERTY SERIALIZER (For requests)
# ============================================================

class RatePropertySerializer(serializers.Serializer):
    """Serializer for rating submission requests"""
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=True,
        help_text="Rating from 1 to 5 stars"
    )
    review = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional review text"
    )
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


# ============================================================
# 7. BATCH INTERACTION SERIALIZER (For bulk operations)
# ============================================================

class BatchInteractionSerializer(serializers.Serializer):
    """Serializer for batch like/dislike operations"""
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text="List of property IDs"
    )
    action = serializers.ChoiceField(
        choices=['like', 'dislike', 'unlike', 'undislike'],
        required=True,
        help_text="Action to perform on all properties"
    )
    
    def validate_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one property ID is required")
        if len(value) > 100:
            raise serializers.ValidationError("Maximum 100 properties per batch request")
        return value


# ============================================================
# 8. PROPERTY LIST SERIALIZER - FIXED WITH USER INTERACTIONS
# ============================================================

class PropertyListSerializer(serializers.ModelSerializer):
    """List view serializer with user interactions"""
    
    # These fields come from the model
    likes_count = serializers.IntegerField(read_only=True, default=0)
    dislikes_count = serializers.IntegerField(read_only=True, default=0)
    average_rating = serializers.FloatField(read_only=True, default=0.0)
    rating_count = serializers.IntegerField(read_only=True, default=0)
    
    # Additional fields
    main_image_url = serializers.SerializerMethodField()
    uploader_name = serializers.SerializerMethodField()
    user_interaction = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    
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
    
    def get_user_interaction(self, obj):
        """Get current user's interaction (if authenticated)"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                interaction = PropertyInteraction.objects.get(
                    property=obj,
                    user=request.user
                )
                return interaction.interaction_type
            except PropertyInteraction.DoesNotExist:
                pass
        return None
    
    def get_user_rating(self, obj):
        """Get current user's rating (if authenticated)"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                rating = PropertyRating.objects.get(
                    property=obj,
                    user=request.user
                )
                return rating.rating
            except PropertyRating.DoesNotExist:
                pass
        return None


# ============================================================
# 9. PROPERTY DETAIL SERIALIZER
# ============================================================

class PropertyDetailSerializer(PropertyListSerializer):
    """Detailed property serializer with all fields"""
    
    class Meta(PropertyListSerializer.Meta):
        fields = PropertyListSerializer.Meta.fields + [
            'description', 'latitude', 'longitude', 
            'formatted_address', 'neighborhood', 'landmark',
            'property_type', 'custom_category_name',
            'features', 'amenities',
            'total_area', 'land_area', 'floor_area',
            'total_rooms', 'total_floors', 'max_occupancy',
            'booking_unit', 'pricing_structure', 'pricing_details',
            'minimum_stay', 'maximum_stay',
            'available_from', 'available_until',
            'is_online', 'agent_status',
            'virtual_tour_url',
            'views_count', 'is_verified',
            'custom_fields', 'property_reference',
            'owner', 'company',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'property_reference', 'created_at', 'updated_at']


# ============================================================
# 10. PROPERTY CREATE SERIALIZER
# ============================================================

class PropertyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = '__all__'
        read_only_fields = ['id', 'property_reference', 'created_at', 'updated_at', 'likes_count', 'dislikes_count', 'average_rating', 'rating_count']


# ============================================================
# 11. PROPERTY UPDATE SERIALIZER
# ============================================================

class PropertyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = '__all__'
        read_only_fields = ['id', 'property_reference', 'created_at', 'updated_at', 'likes_count', 'dislikes_count', 'average_rating', 'rating_count']


# ============================================================
# 12. PROPERTY SERIALIZER (Base)
# ============================================================

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = '__all__'


# ============================================================
# 13. HELPER FUNCTIONS
# ============================================================

def get_rating_distribution(property_obj):
    """Get rating distribution for a property (cached)"""
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
    """Get user's interaction with a property"""
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
    """Get user's rating for a property"""
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