from decimal import Decimal



from rest_framework import serializers

from .identity import public_business_name, public_user_name, public_worker_name



from .models import (

    BusinessPaymentGateway,

    CarWashBusiness,

    CarWashLedgerEntry,

    CarWashPayment,

    CarWashProviderLocation,

    CarWashQuote,

    CarWashRequest,

    CarWashReview,
    CarWashSafetyReport,

    CarWashService,

    CarWashStatusHistory,

    CarWashWallet,

    CarWashWorker,

    PaymentAttempt,

    PaymentGateway,

    ServiceVehiclePrice,

    VehicleType,

)





class VehicleTypeSerializer(serializers.ModelSerializer):

    class Meta:

        model = VehicleType

        fields = ['id', 'business', 'name', 'description', 'icon', 'sort_order', 'is_active']

        read_only_fields = ['id', 'business']





class CarWashServiceSerializer(serializers.ModelSerializer):

    class Meta:

        model = CarWashService

        fields = [

            'id', 'business', 'name', 'description', 'icon', 'estimated_minutes',

            'mobile_available', 'onsite_available', 'is_active', 'sort_order',

        ]

        read_only_fields = ['id', 'business']





class ServiceVehiclePriceSerializer(serializers.ModelSerializer):

    service_name = serializers.CharField(source='service.name', read_only=True)

    vehicle_name = serializers.CharField(source='vehicle_type.name', read_only=True)



    class Meta:

        model = ServiceVehiclePrice

        fields = [

            'id', 'business', 'service', 'service_name', 'vehicle_type', 'vehicle_name',

            'price', 'currency', 'is_active',

        ]

        read_only_fields = ['id', 'business']





class CarWashBusinessSerializer(serializers.ModelSerializer):

    vehicles = VehicleTypeSerializer(source='vehicle_types', many=True, read_only=True)

    services = CarWashServiceSerializer(many=True, read_only=True)

    owner_name = serializers.SerializerMethodField()
    public_name = serializers.SerializerMethodField()



    class Meta:

        model = CarWashBusiness

        fields = [

            'id', 'owner_name', 'public_name', 'name', 'description', 'phone', 'email', 'logo',

            'fulfilment_mode', 'is_active', 'is_verified', 'is_accepting_jobs',

            'address', 'formatted_address', 'place_id', 'latitude', 'longitude',

            'service_radius_km', 'free_travel_km', 'travel_fee_per_km',

            'commission_rate', 'cash_commission_limit', 'average_rating', 'rating_count',

            'vehicles', 'services', 'created_at', 'updated_at',

        ]

        read_only_fields = [

            'id', 'owner_name', 'public_name', 'is_verified', 'average_rating', 'rating_count',

            # Google/device populated. Humans never type these.

            'place_id', 'latitude', 'longitude', 'created_at', 'updated_at',

        ]



    def get_owner_name(self, obj):

        # A business should never unexpectedly expose the owner's personal name.
        return obj.owner.get_username()

    def get_public_name(self, obj):
        return public_business_name(obj)





class CarWashWorkerSerializer(serializers.ModelSerializer):

    public_name = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)

    business_name = serializers.CharField(source='business.name', read_only=True)
    location_age_seconds = serializers.SerializerMethodField()
    live_location_state = serializers.SerializerMethodField()
    effective_online = serializers.SerializerMethodField()



    class Meta:

        model = CarWashWorker

        fields = [

            'id', 'business', 'business_name', 'user', 'username', 'public_name', 'display_name', 'phone',

            'photo', 'is_active', 'is_online', 'is_available', 'effective_online', 'live_location_state', 'location_age_seconds', 'average_rating', 'completed_washes',

        ]

        read_only_fields = ['id', 'business', 'average_rating', 'completed_washes']

    def get_public_name(self, obj):
        return public_worker_name(obj)

    def get_location_age_seconds(self, obj):
        try:
            location = obj.location
        except Exception:
            return None
        if not location.recorded_at:
            return None
        from django.utils import timezone
        return max(0, int((timezone.now() - location.recorded_at).total_seconds()))

    def get_live_location_state(self, obj):
        age = self.get_location_age_seconds(obj)
        if not obj.is_online:
            return 'offline'
        if age is None:
            return 'waiting'
        if age <= 120:
            return 'live'
        if age <= 300:
            return 'stale'
        return 'offline'

    def get_effective_online(self, obj):
        return self.get_live_location_state(obj) == 'live'





class CarWashProviderLocationSerializer(serializers.ModelSerializer):

    worker_name = serializers.SerializerMethodField()

    business_name = serializers.SerializerMethodField()
    location_age_seconds = serializers.SerializerMethodField()
    is_live = serializers.SerializerMethodField()
    freshness = serializers.SerializerMethodField()



    class Meta:

        model = CarWashProviderLocation

        fields = [

            'worker', 'worker_name', 'business_name', 'latitude', 'longitude', 'heading',

            'speed_kph', 'accuracy_m', 'is_active', 'recorded_at', 'updated_at',
            'location_age_seconds', 'is_live', 'freshness',

        ]

        read_only_fields = ['updated_at']



    def get_worker_name(self, obj):

        return public_worker_name(obj.worker)

    def get_business_name(self, obj):
        return public_business_name(obj.worker.business)

    def get_location_age_seconds(self, obj):
        if not obj.recorded_at:
            return None
        from django.utils import timezone
        return max(0, int((timezone.now() - obj.recorded_at).total_seconds()))

    def get_is_live(self, obj):
        age = self.get_location_age_seconds(obj)
        return bool(obj.is_active and age is not None and age <= 120)

    def get_freshness(self, obj):
        age = self.get_location_age_seconds(obj)
        if age is None:
            return 'unknown'
        if age <= 120:
            return 'live'
        if age <= 300:
            return 'stale'
        return 'offline'





class CarWashQuoteSerializer(serializers.ModelSerializer):

    business_name = serializers.CharField(source='business.name', read_only=True)

    vehicle_name = serializers.CharField(source='vehicle_type.name', read_only=True)

    service_name = serializers.CharField(source='service.name', read_only=True)



    class Meta:

        model = CarWashQuote

        fields = [

            'id', 'business', 'business_name', 'vehicle_type', 'vehicle_name', 'service',

            'service_name', 'fulfilment_mode', 'service_latitude', 'service_longitude',

            'service_address', 'service_place_id', 'route_distance_km', 'service_price',

            'travel_fee', 'discount', 'total', 'currency', 'commission_rate',

            'platform_commission', 'provider_amount', 'expires_at', 'is_used',

        ]

        read_only_fields = fields





class CarWashStatusHistorySerializer(serializers.ModelSerializer):

    changed_by_name = serializers.SerializerMethodField()



    class Meta:

        model = CarWashStatusHistory

        fields = ['id', 'status', 'changed_by', 'changed_by_name', 'note', 'latitude', 'longitude', 'created_at']

        read_only_fields = ['id', 'created_at']

    def get_changed_by_name(self, obj):
        return public_user_name(obj.changed_by) if obj.changed_by else ''





class CarWashRequestSerializer(serializers.ModelSerializer):

    customer_name = serializers.SerializerMethodField()
    business_name = serializers.SerializerMethodField()
    worker_name = serializers.SerializerMethodField()
    quote = CarWashQuoteSerializer(read_only=True)
    quote_id = serializers.UUIDField(write_only=True, required=False)
    worker = CarWashWorkerSerializer(source='assigned_worker', read_only=True)
    status_history = CarWashStatusHistorySerializer(many=True, read_only=True)
    payment_summary = serializers.SerializerMethodField()
    service_duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = CarWashRequest
        fields = [
            'id', 'customer', 'customer_name', 'business', 'business_name', 'quote', 'quote_id', 'worker', 'worker_name', 'status',
            'customer_notes', 'requested_at', 'accepted_at', 'en_route_at', 'arrived_at',
            'started_at', 'completed_at', 'cancelled_at', 'created_at', 'updated_at',
            'status_history', 'payment_summary', 'service_duration_seconds',
        ]
        read_only_fields = [
            'id', 'customer', 'business', 'status', 'requested_at', 'accepted_at',
            'en_route_at', 'arrived_at', 'started_at', 'completed_at', 'cancelled_at',
            'created_at', 'updated_at', 'payment_summary', 'service_duration_seconds',
        ]


    def get_customer_name(self, obj):
        return public_user_name(obj.customer)

    def get_business_name(self, obj):
        return public_business_name(obj.business)

    def get_worker_name(self, obj):
        return public_worker_name(obj.assigned_worker) if obj.assigned_worker else ''

    def get_payment_summary(self, obj):
        try:
            payment = obj.payment
        except CarWashPayment.DoesNotExist:
            return None

        gateway_name = ''
        if payment.gateway_id and payment.gateway:
            gateway_name = payment.gateway.name

        return {
            'id': str(payment.id),
            'payment_method': payment.payment_method,
            'gateway_name': gateway_name,
            'currency': payment.currency,
            'gross_amount': str(payment.gross_amount),
            'status': payment.status,
            'paid_at': payment.paid_at,
            'created_at': payment.created_at,
        }

    def get_service_duration_seconds(self, obj):
        if not obj.started_at:
            return None
        end = obj.completed_at or obj.cancelled_at
        if end is None:
            if obj.status != 'washing':
                return None
            from django.utils import timezone
            end = timezone.now()
        return max(0, int((end - obj.started_at).total_seconds()))





class PaymentGatewaySerializer(serializers.ModelSerializer):

    class Meta:

        model = PaymentGateway

        fields = [

            'id', 'name', 'code', 'is_active', 'priority', 'supports_card', 'supports_eft',

            'supports_wallet', 'supports_split_payments', 'supports_refunds', 'supports_payouts',

        ]





class BusinessPaymentGatewaySerializer(serializers.ModelSerializer):

    gateway_name = serializers.CharField(source='gateway.name', read_only=True)

    gateway_code = serializers.CharField(source='gateway.code', read_only=True)



    class Meta:

        model = BusinessPaymentGateway

        fields = ['id', 'business', 'gateway', 'gateway_name', 'gateway_code', 'is_enabled', 'provider_account_reference', 'settings']

        read_only_fields = ['id', 'business']





class PaymentAttemptSerializer(serializers.ModelSerializer):

    gateway_code = serializers.CharField(source='gateway.code', read_only=True)



    class Meta:

        model = PaymentAttempt

        fields = ['id', 'gateway', 'gateway_code', 'reference', 'status', 'amount', 'created_at']





class CarWashPaymentSerializer(serializers.ModelSerializer):

    gateway_name = serializers.CharField(source='gateway.name', read_only=True, default='')

    attempts = PaymentAttemptSerializer(many=True, read_only=True)



    class Meta:

        model = CarWashPayment

        fields = [

            'id', 'wash_request', 'gateway', 'gateway_name', 'payment_method', 'settlement_mode',

            'currency', 'gross_amount', 'platform_commission', 'provider_amount', 'gateway_fee',

            'tip_amount', 'status', 'gateway_reference', 'gateway_transaction_id', 'paid_at',

            'attempts', 'created_at', 'updated_at',

        ]

        read_only_fields = fields





class CarWashReviewSerializer(serializers.ModelSerializer):

    customer_name = serializers.SerializerMethodField()



    class Meta:

        model = CarWashReview

        fields = ['id', 'wash_request', 'customer', 'customer_name', 'business', 'worker', 'rating', 'comment', 'created_at']

        read_only_fields = ['id', 'customer', 'business', 'worker', 'created_at']

    def get_customer_name(self, obj):
        return public_user_name(obj.customer)





class QuoteRequestSerializer(serializers.Serializer):

    business_id = serializers.UUIDField()

    price_id = serializers.UUIDField(required=False)

    vehicle_type_id = serializers.UUIDField(required=False)

    service_id = serializers.UUIDField(required=False)

    fulfilment_mode = serializers.ChoiceField(choices=['mobile', 'onsite'])

    latitude = serializers.DecimalField(max_digits=22, decimal_places=16, required=False, allow_null=True)

    longitude = serializers.DecimalField(max_digits=22, decimal_places=16, required=False, allow_null=True)

    address = serializers.CharField(required=False, allow_blank=True)

    place_id = serializers.CharField(required=False, allow_blank=True)

    route_distance_km = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal('0.00'))



    def validate(self, attrs):

        if not attrs.get('price_id') and not (attrs.get('vehicle_type_id') and attrs.get('service_id')):

            raise serializers.ValidationError(
                'Choose a valid vehicle and service combination.'
            )

        if attrs['fulfilment_mode'] == 'mobile':

            if attrs.get('latitude') is None or attrs.get('longitude') is None:

                raise serializers.ValidationError('Your wash location could not be detected. Please allow location access or choose a place on the map.')

        return attrs





class CreatePaymentSerializer(serializers.Serializer):

    payment_method = serializers.ChoiceField(choices=['card', 'eft', 'wallet', 'cash'])

    gateway_code = serializers.SlugField(required=False, allow_blank=True)





class ProviderLocationUpdateSerializer(serializers.Serializer):

    latitude = serializers.DecimalField(max_digits=22, decimal_places=16)

    longitude = serializers.DecimalField(max_digits=22, decimal_places=16)

    heading = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)

    speed_kph = serializers.DecimalField(max_digits=7, decimal_places=2, required=False, allow_null=True)

    accuracy_m = serializers.DecimalField(max_digits=9, decimal_places=2, required=False, allow_null=True)


class CarWashSafetyReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.SerializerMethodField()
    reported_name = serializers.SerializerMethodField()
    business_name = serializers.SerializerMethodField()
    worker_name = serializers.SerializerMethodField()

    class Meta:
        model = CarWashSafetyReport
        fields = [
            'id', 'reporter', 'reporter_name', 'reported_user', 'reported_name',
            'wash_request', 'business', 'business_name', 'worker', 'worker_name',
            'category', 'description', 'status', 'reporter_latitude',
            'reporter_longitude', 'reported_latitude', 'reported_longitude',
            'nearest_police_name', 'nearest_police_address', 'nearest_police_place_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_reporter_name(self, obj):
        return public_user_name(obj.reporter)

    def get_reported_name(self, obj):
        if obj.worker_id:
            return public_worker_name(obj.worker)
        if obj.business_id and obj.reported_user_id == getattr(obj.business, 'owner_id', None):
            return public_business_name(obj.business)
        return public_user_name(obj.reported_user) if obj.reported_user_id else ''

    def get_business_name(self, obj):
        return public_business_name(obj.business) if obj.business_id else ''

    def get_worker_name(self, obj):
        return public_worker_name(obj.worker) if obj.worker_id else ''
