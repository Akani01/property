

from urllib.parse import urlsplit



from django.conf import settings

from rest_framework import serializers



from .models import (

    Ad,

    AdCategory,

    AdImpression,

    AdClick,

    AdConversion,

    AdSchedule,

    AdTargetingRule,

)





# ============================================================

# HELPERS

# ============================================================



def absolute_media_url(value, request=None):

    """

    Convert an image URL/path into a usable URL.



    Supports:

    - https://example.com/image.jpg

    - /media/ads/image.jpg

    - media/ads/image.jpg

    - ads/image.jpg



    Does not replace missing images with another ad's image.

    """

    if not value:

        return None



    value = str(value).strip()



    if not value:

        return None



    if value.startswith(("http://", "https://")):

        return value



    if value.startswith("//"):

        scheme = request.scheme if request else "https"

        return f"{scheme}:{value}"



    # Do not expose unsupported schemes as image sources.

    parsed = urlsplit(value)



    if parsed.scheme or parsed.netloc:

        return None



    media_url = settings.MEDIA_URL or "/media/"



    if media_url.startswith(("http://", "https://")):
        from urllib.parse import urljoin
        return urljoin(media_url, value.lstrip("/")) if not value.startswith("/") else (request.build_absolute_uri(value) if request else value)

    if not media_url.startswith("/"):

        media_url = "/" + media_url



    if not media_url.endswith("/"):

        media_url += "/"



    if not value.startswith("/"):

        media_prefix = media_url.lstrip("/")



        if value.startswith(media_prefix):

            value = "/" + value

        else:

            value = media_url + value.lstrip("/")



    if request:

        return request.build_absolute_uri(value)



    return value





def uploaded_file_url(file_field, request=None):

    """

    Resolve a Django ImageField/FileField using its storage backend.



    This also supports external storage such as S3 or Cloudinary

    when configured through Django storage.

    """

    if not file_field:

        return None



    try:

        url = file_field.url

    except (AttributeError, ValueError, OSError):

        return None



    if not url:

        return None



    if request:

        return request.build_absolute_uri(url)



    return url





# ============================================================

# AD CATEGORIES

# ============================================================



class AdCategorySerializer(serializers.ModelSerializer):



    class Meta:

        model = AdCategory



        fields = [

            "id",

            "name",

            "slug",

            "description",

            "icon",

            "parent",

            "is_active",

            "created_at",

        ]





# ============================================================

# ADVERTISEMENTS

# ============================================================



class AdSerializer(serializers.ModelSerializer):



    advertiser_name = serializers.SerializerMethodField()

    property_title = serializers.SerializerMethodField()

    category_name = serializers.SerializerMethodField()



    # Resolved image URL for the homepage and sponsored cards.

    image_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)



    class Meta:

        model = Ad



        fields = [

            "id",

            "title",

            "description",

            "ad_type",

            "image",

            "image_url",

            "video_url",

            "thumbnail_url",

            "price",

            "price_currency",

            "display_price",

            "target_audience",

            "target_locations",

            "target_property_types",

            "target_user_types",

            "target_min_age",

            "target_max_age",

            "start_date",

            "end_date",

            "max_impressions",

            "max_clicks",

            "budget_total",

            "budget_daily",

            "cost_per_click",

            "cost_per_impression",

            "cost_per_conversion",

            "impressions",

            "unique_impressions",

            "clicks",

            "unique_clicks",

            "conversions",

            "conversion_value",

            "ctr",

            "position",

            "priority",

            "frequency_cap",

            "advertiser",

            "advertiser_name",

            "property",

            "property_title",

            "category",

            "category_name",

            "status",

            "is_active",

            "is_featured",

            "is_verified",

            "cta_text",

            "cta_link",

            "cta_button_color",

            "cta_button_text_color",

            "created_at",

            "updated_at",

            "approved_at",

            "review_notes",

        ]



        read_only_fields = [

            "id",

            "advertiser",

            "impressions",

            "unique_impressions",

            "clicks",

            "unique_clicks",

            "conversions",

            "conversion_value",

            "ctr",

            "created_at",

            "updated_at",

            "approved_at",

            "is_verified",

        ]



    # --------------------------------------------------------

    # IMAGE HANDLING

    # --------------------------------------------------------



    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        uploaded = uploaded_file_url(getattr(instance, "image", None), request)
        data["image_url"] = uploaded or absolute_media_url(
            getattr(instance, "image_url", None), request
        )
        for key in ("video_url", "thumbnail_url"):
            value = data.get(key)
            if value:
                data[key] = absolute_media_url(value, request)
        return data

    # --------------------------------------------------------

    # ADVERTISER NAME

    # --------------------------------------------------------



    def get_advertiser_name(self, obj):

        advertiser = getattr(obj, "advertiser", None)



        if not advertiser:

            return None



        company_name = getattr(

            advertiser,

            "company_name",

            None

        )



        if company_name:

            return company_name



        business_profile = getattr(

            advertiser,

            "businessprofile",

            None

        )



        if business_profile:

            company_name = getattr(

                business_profile,

                "company_name",

                None

            )



            if company_name:

                return company_name



        full_name = advertiser.get_full_name() if callable(getattr(advertiser, "get_full_name", None)) else ""



        if full_name and full_name.strip():

            return full_name.strip()



        return getattr(advertiser, "username", None) or "Sponsored"



    # --------------------------------------------------------

    # PROPERTY INFORMATION

    # --------------------------------------------------------



    def get_property_title(self, obj):

        property_obj = getattr(obj, "property", None)



        if property_obj:

            return getattr(property_obj, "title", None)



        return None



    # --------------------------------------------------------

    # CATEGORY INFORMATION

    # --------------------------------------------------------



    def get_category_name(self, obj):

        category = getattr(obj, "category", None)



        if category:

            return getattr(category, "name", None)



        return None



    # --------------------------------------------------------

    # CREATE ADVERTISEMENT

    # --------------------------------------------------------



    def create(self, validated_data):

        request = self.context.get("request")



        if request and request.user.is_authenticated:

            validated_data["advertiser"] = request.user



        return super().create(validated_data)





# ============================================================

# AD IMPRESSIONS

# ============================================================



class AdImpressionSerializer(serializers.ModelSerializer):



    class Meta:

        model = AdImpression



        fields = [

            "id",

            "ad",

            "user",

            "session_id",

            "ip_address",

            "user_agent",

            "referer",

            "viewed_at",

        ]





# ============================================================

# AD CLICKS

# ============================================================



class AdClickSerializer(serializers.ModelSerializer):



    class Meta:

        model = AdClick



        fields = [

            "id",

            "ad",

            "user",

            "session_id",

            "ip_address",

            "user_agent",

            "clicked_at",

            "converted",

        ]





# ============================================================

# AD CONVERSIONS

# ============================================================



class AdConversionSerializer(serializers.ModelSerializer):



    class Meta:

        model = AdConversion



        fields = [

            "id",

            "ad",

            "user",

            "session_id",

            "conversion_type",

            "value",

            "converted_at",

        ]





# ============================================================

# AD SCHEDULES

# ============================================================



class AdScheduleSerializer(serializers.ModelSerializer):



    class Meta:

        model = AdSchedule



        fields = [

            "id",

            "ad",

            "day_of_week",

            "start_time",

            "end_time",

            "is_active",

        ]





# ============================================================

# AD TARGETING RULES

# ============================================================



class AdTargetingRuleSerializer(serializers.ModelSerializer):



    class Meta:

        model = AdTargetingRule



        fields = [

            "id",

            "ad",

            "rule_type",

            "operator",

            "value",

            "is_active",

        ]





# ============================================================

# AD STATISTICS

# ============================================================



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
