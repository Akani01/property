from rest_framework import serializers
from .models import (
    Ad, AdCategory, AdImpression, AdClick, 
    AdConversion, AdSchedule, AdTargetingRule
)
from hiring.models import CustomUser
from realestate.models import Property


class AdCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdCategory
        fields = ['id', 'name', 'slug', 'description', 'icon', 'parent', 'is_active', 'created_at']


class AdSerializer(serializers.ModelSerializer):
    advertiser_name = serializers.SerializerMethodField()
    property_title = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Ad
        fields = [
            'id', 'title', 'description', 'ad_type', 'image', 'image_url',
            'video_url', 'thumbnail_url', 'price', 'price_currency', 'display_price',
            'target_audience', 'target_locations', 'target_property_types',
            'target_user_types', 'target_min_age', 'target_max_age',
            'start_date', 'end_date', 'max_impressions', 'max_clicks',
            'budget_total', 'budget_daily', 'cost_per_click', 'cost_per_impression',
            'cost_per_conversion', 'impressions', 'unique_impressions',
            'clicks', 'unique_clicks', 'conversions', 'conversion_value',
            'ctr', 'position', 'priority', 'frequency_cap',
            'advertiser', 'advertiser_name', 'property', 'property_title',
            'category', 'category_name', 'status', 'is_active', 'is_featured',
            'is_verified', 'cta_text', 'cta_link', 'cta_button_color',
            'cta_button_text_color', 'created_at', 'updated_at',
            'approved_at', 'review_notes'
        ]
        read_only_fields = [
            'id', 'advertiser', 'impressions', 'unique_impressions',
            'clicks', 'unique_clicks', 'conversions', 'conversion_value',
            'ctr', 'created_at', 'updated_at', 'approved_at', 'is_verified'
        ]
    
    def get_advertiser_name(self, obj):
        if obj.advertiser:
            return obj.advertiser.username
        return None
    
    def get_property_title(self, obj):
        if obj.property:
            return obj.property.title
        return None
    
    def get_category_name(self, obj):
        if obj.category:
            return obj.category.name
        return None
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['advertiser'] = request.user
        return super().create(validated_data)


class AdImpressionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdImpression
        fields = ['id', 'ad', 'user', 'session_id', 'ip_address', 'user_agent', 'referer', 'viewed_at']


class AdClickSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdClick
        fields = ['id', 'ad', 'user', 'session_id', 'ip_address', 'user_agent', 'clicked_at', 'converted']


class AdConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdConversion
        fields = ['id', 'ad', 'user', 'session_id', 'conversion_type', 'value', 'converted_at']


class AdScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdSchedule
        fields = ['id', 'ad', 'day_of_week', 'start_time', 'end_time', 'is_active']


class AdTargetingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdTargetingRule
        fields = ['id', 'ad', 'rule_type', 'operator', 'value', 'is_active']


class AdStatsSerializer(serializers.Serializer):
    total_ads = serializers.IntegerField()
    active_ads = serializers.IntegerField()
    pending_ads = serializers.IntegerField()
    rejected_ads = serializers.IntegerField()
    expired_ads = serializers.IntegerField()
    total_impressions = serializers.IntegerField()
    total_clicks = serializers.IntegerField()
    total_conversions = serializers.IntegerField()
    click_through_rate = serializers.FloatField()
    conversion_rate = serializers.FloatField()
    total_spent = serializers.FloatField()
    total_revenue = serializers.FloatField()
    roi = serializers.FloatField()
    cost_per_click = serializers.FloatField()
    cost_per_impression = serializers.FloatField()
    revenue_per_click = serializers.FloatField()