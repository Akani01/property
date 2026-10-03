from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import (
    PropertyCategory, PropertyType, PropertyFeature, Property,
    Room, Booking, DriverLocation, AvailabilityCalendar,
    BookingInquiry, PropertyReview, Wishlist, PropertyAnalytics
)


@admin.register(PropertyCategory)
class PropertyCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'icon_preview', 'is_system', 'is_active', 'property_count']
    search_fields = ['name', 'description']
    list_filter = ['category_type', 'is_system', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    def icon_preview(self, obj):
        if obj.icon:
            return format_html('<i class="{}"></i>', obj.icon)
        return '-'
    icon_preview.short_description = 'Icon'
    
    def property_count(self, obj):
        return obj.property_types.count()
    property_count.short_description = 'Property Types'


@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'size_classification', 'is_system', 'is_active']
    search_fields = ['name', 'description']
    list_filter = ['category', 'size_classification', 'is_system', 'is_active', 'is_commercial']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PropertyFeature)
class PropertyFeatureAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'icon_preview', 'is_custom', 'is_active']
    search_fields = ['name']
    list_filter = ['category', 'is_custom', 'is_active']
    
    def icon_preview(self, obj):
        if obj.icon:
            return format_html('<i class="{}"></i>', obj.icon)
        return '-'
    icon_preview.short_description = 'Icon'


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
    fields = ['room_number', 'room_name', 'room_type', 'capacity', 'price_per_night', 'room_status']
    readonly_fields = ['created_at', 'updated_at']


class AvailabilityInline(admin.TabularInline):
    model = AvailabilityCalendar
    extra = 1
    fields = ['start_date', 'end_date', 'availability_type', 'special_price']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'property_reference', 'company', 'property_type',
        'status', 'base_price', 'city', 'is_active', 'is_online'
    ]
    search_fields = ['title', 'property_reference', 'address', 'city']
    list_filter = [
        'status', 'listing_type', 'property_type', 'city', 
        'is_active', 'is_featured', 'is_online', 'is_verified'
    ]
    readonly_fields = ['property_reference', 'views_count', 'created_at', 'updated_at']
    inlines = [RoomInline, AvailabilityInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'property_reference', 'title', 'description',
                'property_type', 'custom_category_name'
            )
        }),
        ('Location', {
            'fields': (
                'address', 'city', 'state', 'country', 'postal_code',
                'latitude', 'longitude', 'formatted_address', 'place_id'
            )
        }),
        ('Pricing & Booking', {
            'fields': (
                'base_price', 'price_per_unit', 'price_per_sqm', 'price_currency',
                'listing_type', 'transaction_type', 'booking_mode',
                'minimum_stay', 'maximum_stay', 'is_bookable'
            )
        }),
        ('Real-time Tracking (Optional)', {
            'fields': ('is_online', 'agent_status', 'assigned_agent'),
            'classes': ('collapse',)
        }),
        ('Specifications', {
            'fields': (
                'total_area', 'land_area', 'floor_area', 'total_rooms',
                'total_floors', 'max_occupancy', 'bedrooms', 'bathrooms',
                'garages', 'parking_spaces'
            )
        }),
        ('Status & Features', {
            'fields': (
                'status', 'is_active', 'is_verified', 'is_featured',
                'is_premium', 'main_image', 'virtual_tour_url'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            if not obj.listing_agent:
                obj.listing_agent = request.user
            if not obj.owner:
                obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['room_number', 'room_name', 'property', 'room_type', 'capacity', 'room_status']
    search_fields = ['room_number', 'room_name', 'property__title']
    list_filter = ['room_type', 'room_status', 'property', 'is_active']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_reference', 'guest', 'property', 'check_in',
        'check_out', 'status', 'total_amount', 'payment_status'
    ]
    search_fields = ['booking_reference', 'guest__username', 'property__title']
    list_filter = ['status', 'payment_status', 'booking_mode', 'created_at']
    readonly_fields = ['booking_reference', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(DriverLocation)
class DriverLocationAdmin(admin.ModelAdmin):
    list_display = ['driver', 'latitude', 'longitude', 'is_active', 'updated_at']
    search_fields = ['driver__username']
    list_filter = ['is_active', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AvailabilityCalendar)
class AvailabilityCalendarAdmin(admin.ModelAdmin):
    list_display = ['property', 'start_date', 'end_date', 'availability_type', 'special_price']
    list_filter = ['availability_type', 'start_date']
    search_fields = ['property__title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BookingInquiry)
class BookingInquiryAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'property', 'inquiry_type', 'status', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    list_filter = ['inquiry_type', 'status', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Name'


@admin.register(PropertyReview)
class PropertyReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'property', 'overall_rating', 'is_approved', 'created_at']
    list_filter = ['overall_rating', 'is_approved', 'is_public', 'is_verified']
    search_fields = ['user__username', 'property__title', 'review_text']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'is_default', 'property_count', 'created_at']
    search_fields = ['user__username', 'name']
    list_filter = ['is_default', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def property_count(self, obj):
        return obj.properties.count()
    property_count.short_description = 'Properties'


@admin.register(PropertyAnalytics)
class PropertyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['property', 'total_views', 'total_bookings', 'total_revenue', 'average_rating']
    search_fields = ['property__title']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('Views & Engagement', {
            'fields': ('total_views', 'unique_views', 'views_by_device', 'views_by_country')
        }),
        ('Bookings & Revenue', {
            'fields': ('total_bookings', 'total_revenue', 'average_occupancy_rate')
        }),
        ('Ratings & Reviews', {
            'fields': ('reviews_count', 'average_rating', 'favorites_count', 'shares_count')
        }),
        ('Time Metrics', {
            'fields': ('days_on_market', 'average_booking_duration')
        }),
        ('Last 30 Days', {
            'fields': ('views_last_30_days', 'inquiries_last_30_days', 
                      'bookings_last_30_days', 'revenue_last_30_days')
        }),
        ('Seasonal', {
            'fields': ('seasonal_data', 'updated_at')
        })
    )