from decimal import Decimal



from rest_framework import serializers



from .models import (

    BusinessPaymentGateway,

    CarWashBusiness,

    CarWashLedgerEntry,

    CarWashPayment,

    CarWashProviderLocation,

    CarWashQuote,

    CarWashRequest,

    CarWashReview,

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



    class Meta:

        model = CarWashBusiness

        fields = [

            'id', 'owner_name', 'name', 'description', 'phone', 'email', 'logo',

            'fulfilment_mode', 'is_active', 'is_verified', 'is_accepting_jobs',

            'address', 'formatted_address', 'place_id', 'latitude', 'longitude',

            'service_radius_km', 'free_travel_km', 'travel_fee_per_km',

            'commission_rate', 'cash_commission_limit', 'average_rating', 'rating_count',

            'vehicles', 'services', 'created_at', 'updated_at',

        ]

        read_only_fields = [

            'id', 'owner_name', 'is_verified', 'average_rating', 'rating_count',

            # Google/device populated. Humans never type these.

            'place_id', 'latitude', 'longitude', 'created_at', 'updated_at',

        ]



    def get_owner_name(self, obj):

        return obj.owner.get_full_name() or obj.owner.get_username()





class CarWashWorkerSerializer(serializers.ModelSerializer):

    username = serializers.CharField(source='user.username', read_only=True)

    business_name = serializers.CharField(source='business.name', read_only=True)



    class Meta:

        model = CarWashWorker

        fields = [

            'id', 'business', 'business_name', 'user', 'username', 'display_name', 'phone',

            'photo', 'is_active', 'is_online', 'is_available', 'average_rating', 'completed_washes',

        ]

        read_only_fields = ['id', 'business', 'average_rating', 'completed_washes']





class CarWashProviderLocationSerializer(serializers.ModelSerializer):

    worker_name = serializers.SerializerMethodField()

    business_name = serializers.CharField(source='worker.business.name', read_only=True)



    class Meta:

        model = CarWashProviderLocation

        fields = [

            'worker', 'worker_name', 'business_name', 'latitude', 'longitude', 'heading',

            'speed_kph', 'accuracy_m', 'is_active', 'recorded_at', 'updated_at',

        ]

        read_only_fields = ['updated_at']



    def get_worker_name(self, obj):

        return obj.worker.display_name or obj.worker.user.get_username()





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

    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True, default='')



    class Meta:

        model = CarWashStatusHistory

        fields = ['id', 'status', 'changed_by', 'changed_by_name', 'note', 'latitude', 'longitude', 'created_at']

        read_only_fields = ['id', 'created_at']





class CarWashRequestSerializer(serializers.ModelSerializer):

    quote = CarWashQuoteSerializer(read_only=True)

    quote_id = serializers.UUIDField(write_only=True, required=False)

    worker = CarWashWorkerSerializer(source='assigned_worker', read_only=True)

    status_history = CarWashStatusHistorySerializer(many=True, read_only=True)



    class Meta:

        model = CarWashRequest

        fields = [

            'id', 'customer', 'business', 'quote', 'quote_id', 'worker', 'status',

            'customer_notes', 'requested_at', 'accepted_at', 'en_route_at', 'arrived_at',

            'started_at', 'completed_at', 'cancelled_at', 'created_at', 'updated_at',

            'status_history',

        ]

        read_only_fields = [

            'id', 'customer', 'business', 'status', 'requested_at', 'accepted_at',

            'en_route_at', 'arrived_at', 'started_at', 'completed_at', 'cancelled_at',

            'created_at', 'updated_at',

        ]





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

    customer_name = serializers.CharField(source='customer.username', read_only=True)



    class Meta:

        model = CarWashReview

        fields = ['id', 'wash_request', 'customer', 'customer_name', 'business', 'worker', 'rating', 'comment', 'created_at']

        read_only_fields = ['id', 'customer', 'business', 'worker', 'created_at']





class QuoteRequestSerializer(serializers.Serializer):

    business_id = serializers.UUIDField()

    vehicle_type_id = serializers.UUIDField()

    service_id = serializers.UUIDField()

    fulfilment_mode = serializers.ChoiceField(choices=['mobile', 'onsite'])

    latitude = serializers.DecimalField(max_digits=22, decimal_places=16, required=False, allow_null=True)

    longitude = serializers.DecimalField(max_digits=22, decimal_places=16, required=False, allow_null=True)

    address = serializers.CharField(required=False, allow_blank=True)

    place_id = serializers.CharField(required=False, allow_blank=True)

    route_distance_km = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, default=Decimal('0.00'))



    def validate(self, attrs):

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
