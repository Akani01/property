from django.contrib import admin
from .models import Ad, AdCategory, AdImpression, AdClick, AdConversion, AdSchedule, AdTargetingRule

@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ['title', 'advertiser', 'status', 'is_active', 'position', 'impressions', 'clicks', 'created_at']
    list_filter = ['status', 'is_active', 'position', 'ad_type', 'created_at']
    search_fields = ['title', 'description', 'advertiser__username']
    readonly_fields = ['id', 'impressions', 'unique_impressions', 'clicks', 'unique_clicks', 'conversions', 'conversion_value', 'ctr', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Info', {'fields': ('title', 'description', 'ad_type')}),
        ('Media', {'fields': ('image', 'image_url', 'video_url', 'thumbnail_url')}),
        ('Pricing', {'fields': ('price', 'price_currency', 'display_price')}),
        ('Targeting', {'fields': ('target_audience', 'target_locations', 'target_property_types', 'target_user_types', 'target_min_age', 'target_max_age')}),
        ('Scheduling & Budget', {'fields': ('start_date', 'end_date', 'max_impressions', 'max_clicks', 'budget_total', 'budget_daily', 'cost_per_click', 'cost_per_impression', 'cost_per_conversion')}),
        ('Performance', {'fields': ('impressions', 'unique_impressions', 'clicks', 'unique_clicks', 'conversions', 'conversion_value', 'ctr')}),
        ('Placement', {'fields': ('position', 'priority', 'frequency_cap')}),
        ('Relationships', {'fields': ('advertiser', 'property', 'category')}),
        ('Status', {'fields': ('status', 'is_active', 'is_featured', 'is_verified')}),
        ('Call to Action', {'fields': ('cta_text', 'cta_link', 'cta_button_color', 'cta_button_text_color')}),
        ('Metadata', {'fields': ('approved_at', 'approved_by', 'reviewed_at', 'review_notes')}),
    )

@admin.register(AdCategory)
class AdCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']

@admin.register(AdImpression)
class AdImpressionAdmin(admin.ModelAdmin):
    list_display = ['ad', 'user', 'session_id', 'viewed_at']
    list_filter = ['viewed_at']
    readonly_fields = ['viewed_at']

@admin.register(AdClick)
class AdClickAdmin(admin.ModelAdmin):
    list_display = ['ad', 'user', 'session_id', 'clicked_at', 'converted']
    list_filter = ['clicked_at', 'converted']
    readonly_fields = ['clicked_at']

@admin.register(AdConversion)
class AdConversionAdmin(admin.ModelAdmin):
    list_display = ['ad', 'user', 'conversion_type', 'value', 'converted_at']
    list_filter = ['conversion_type', 'converted_at']
    readonly_fields = ['converted_at']

@admin.register(AdSchedule)
class AdScheduleAdmin(admin.ModelAdmin):
    list_display = ['ad', 'get_day_of_week_display', 'start_time', 'end_time', 'is_active']

@admin.register(AdTargetingRule)
class AdTargetingRuleAdmin(admin.ModelAdmin):
    list_display = ['ad', 'rule_type', 'operator', 'is_active']