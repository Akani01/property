import uuid

from decimal import Decimal



from django.conf import settings

from django.core.validators import MinValueValidator, MaxValueValidator

from django.db import models

from django.utils import timezone





class TimeStampedModel(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)



    class Meta:

        abstract = True





class CarWashBusiness(TimeStampedModel):

    FULFILMENT_CHOICES = [

        ('mobile', 'Mobile only'),

        ('onsite', 'On-site only'),

        ('both', 'Mobile and on-site'),

    ]



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey(

        settings.AUTH_USER_MODEL,

        on_delete=models.CASCADE,

        related_name='carwash_businesses',

    )

    name = models.CharField(max_length=150)

    description = models.TextField(blank=True)

    phone = models.CharField(max_length=40, blank=True)

    email = models.EmailField(blank=True)

    logo = models.ImageField(upload_to='carwash/businesses/logos/', blank=True, null=True)



    fulfilment_mode = models.CharField(max_length=20, choices=FULFILMENT_CHOICES, default='both')

    is_active = models.BooleanField(default=True)

    is_verified = models.BooleanField(default=False)

    is_accepting_jobs = models.BooleanField(default=True)



    # Fixed-site location for traditional car washes.

    address = models.CharField(max_length=255, blank=True)

    formatted_address = models.CharField(max_length=255, blank=True)

    place_id = models.CharField(max_length=255, blank=True)

    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, editable=False)

    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, editable=False)



    # Mobile service controls.

    service_radius_km = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('20.00'))

    free_travel_km = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('5.00'))

    travel_fee_per_km = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))



    # OppoGlobe commercial settings. Snapshot is copied onto each quote/payment.

    commission_rate = models.DecimalField(

        max_digits=5,

        decimal_places=2,

        default=Decimal('15.00'),

        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],

    )

    cash_commission_limit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('500.00'))



    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))

    rating_count = models.PositiveIntegerField(default=0)



    class Meta:

        ordering = ['-is_verified', '-average_rating', 'name']



    def __str__(self):

        return self.name



    @property

    def supports_mobile(self):

        return self.fulfilment_mode in {'mobile', 'both'}



    @property

    def supports_onsite(self):

        return self.fulfilment_mode in {'onsite', 'both'}



class CarWashPayoutProfile(TimeStampedModel):
    """Bank account OppoGlobe admins use to pay a car-wash business."""

    ACCOUNT_TYPES = [
        ('cheque', 'Cheque / Current'),
        ('savings', 'Savings'),
        ('business', 'Business'),
        ('transmission', 'Transmission'),
    ]

    business = models.OneToOneField(
        CarWashBusiness,
        on_delete=models.CASCADE,
        related_name='payout_profile',
    )
    bank_name = models.CharField(max_length=120, blank=True)
    account_holder = models.CharField(max_length=160, blank=True)
    account_number = models.CharField(max_length=40, blank=True)
    branch_code = models.CharField(max_length=20, blank=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='cheque')
    payout_reference = models.CharField(max_length=120, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_complete(self):
        return bool(self.bank_name and self.account_holder and self.account_number and self.branch_code)

    @property
    def masked_account_number(self):
        value = self.account_number or ''
        if not value:
            return ''
        return ('•' * max(0, len(value) - 4)) + value[-4:]

    def __str__(self):
        return f'{self.business.name} payout account'




class VehicleType(TimeStampedModel):

    """Business-defined vehicle option. No hard-coded vehicle catalogue required."""



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    business = models.ForeignKey(CarWashBusiness, on_delete=models.CASCADE, related_name='vehicle_types')

    name = models.CharField(max_length=100)

    description = models.CharField(max_length=255, blank=True)

    icon = models.CharField(max_length=80, blank=True, default='fas fa-car')

    sort_order = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)



    class Meta:

        ordering = ['sort_order', 'name']

        unique_together = [('business', 'name')]



    def __str__(self):

        return f'{self.business.name} - {self.name}'





class CarWashService(TimeStampedModel):

    """Business-defined service. Businesses can add/remove services dynamically."""



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    business = models.ForeignKey(CarWashBusiness, on_delete=models.CASCADE, related_name='services')

    name = models.CharField(max_length=120)

    description = models.TextField(blank=True)

    icon = models.CharField(max_length=80, blank=True, default='fas fa-soap')

    estimated_minutes = models.PositiveIntegerField(default=30)

    mobile_available = models.BooleanField(default=True)

    onsite_available = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)

    sort_order = models.PositiveIntegerField(default=0)



    class Meta:

        ordering = ['sort_order', 'name']

        unique_together = [('business', 'name')]



    def __str__(self):

        return f'{self.business.name} - {self.name}'





class ServiceVehiclePrice(TimeStampedModel):

    """Price matrix: each business controls each service + vehicle combination."""



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    business = models.ForeignKey(CarWashBusiness, on_delete=models.CASCADE, related_name='service_prices')

    service = models.ForeignKey(CarWashService, on_delete=models.CASCADE, related_name='vehicle_prices')

    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE, related_name='service_prices')

    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])

    currency = models.CharField(max_length=10, default='ZAR')

    is_active = models.BooleanField(default=True)



    class Meta:

        unique_together = [('business', 'service', 'vehicle_type')]

        ordering = ['service__sort_order', 'vehicle_type__sort_order']



    def __str__(self):

        return f'{self.service.name} / {self.vehicle_type.name} - {self.currency} {self.price}'





class CarWashWorker(TimeStampedModel):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    business = models.ForeignKey(CarWashBusiness, on_delete=models.CASCADE, related_name='workers')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carwash_worker_profiles')

    display_name = models.CharField(max_length=120, blank=True)

    phone = models.CharField(max_length=40, blank=True)

    photo = models.ImageField(upload_to='carwash/workers/', blank=True, null=True)

    is_active = models.BooleanField(default=True)

    is_online = models.BooleanField(default=False)

    is_available = models.BooleanField(default=False)

    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))

    completed_washes = models.PositiveIntegerField(default=0)



    class Meta:

        unique_together = [('business', 'user')]



    def __str__(self):

        return self.display_name or self.user.get_username()





class CarWashProviderLocation(TimeStampedModel):

    worker = models.OneToOneField(CarWashWorker, on_delete=models.CASCADE, related_name='location')

    latitude = models.DecimalField(max_digits=10, decimal_places=7)

    longitude = models.DecimalField(max_digits=10, decimal_places=7)

    heading = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    speed_kph = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    accuracy_m = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    recorded_at = models.DateTimeField(default=timezone.now)



    def __str__(self):

        return f'{self.worker} @ {self.latitude},{self.longitude}'





class CarWashQuote(TimeStampedModel):

    FULFILMENT_CHOICES = [

        ('mobile', 'Come to me'),

        ('onsite', "I'll go there"),

    ]



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carwash_quotes')

    business = models.ForeignKey(CarWashBusiness, on_delete=models.PROTECT, related_name='quotes')

    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.PROTECT)

    service = models.ForeignKey(CarWashService, on_delete=models.PROTECT)

    fulfilment_mode = models.CharField(max_length=20, choices=FULFILMENT_CHOICES)



    service_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    service_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    service_address = models.CharField(max_length=255, blank=True)

    service_place_id = models.CharField(max_length=255, blank=True)



    route_distance_km = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))

    service_price = models.DecimalField(max_digits=10, decimal_places=2)

    travel_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    total = models.DecimalField(max_digits=10, decimal_places=2)

    currency = models.CharField(max_length=10, default='ZAR')



    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)

    platform_commission = models.DecimalField(max_digits=10, decimal_places=2)

    provider_amount = models.DecimalField(max_digits=10, decimal_places=2)



    expires_at = models.DateTimeField()

    is_used = models.BooleanField(default=False)



    def __str__(self):

        return f'Quote {self.id} - {self.total} {self.currency}'





class CarWashRequest(TimeStampedModel):

    STATUS_CHOICES = [

        ('searching', 'Searching'),

        ('requested', 'Requested'),

        ('accepted', 'Accepted'),

        ('en_route', 'En route'),

        ('arrived', 'Arrived'),

        ('washing', 'Washing'),

        ('completed', 'Completed'),

        ('cancelled', 'Cancelled'),

        ('declined', 'Declined'),

        ('expired', 'Expired'),

    ]



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carwash_requests')

    business = models.ForeignKey(CarWashBusiness, on_delete=models.PROTECT, related_name='wash_requests')

    quote = models.OneToOneField(CarWashQuote, on_delete=models.PROTECT, related_name='wash_request')

    assigned_worker = models.ForeignKey(

        CarWashWorker,

        on_delete=models.SET_NULL,

        null=True,

        blank=True,

        related_name='assigned_requests',

    )

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='requested')

    customer_notes = models.TextField(blank=True)

    requested_at = models.DateTimeField(default=timezone.now)

    accepted_at = models.DateTimeField(null=True, blank=True)

    en_route_at = models.DateTimeField(null=True, blank=True)

    arrived_at = models.DateTimeField(null=True, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)

    completed_at = models.DateTimeField(null=True, blank=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)



    class Meta:

        ordering = ['-created_at']



    def __str__(self):

        return f'Wash {self.id} - {self.status}'





class CarWashStatusHistory(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    wash_request = models.ForeignKey(CarWashRequest, on_delete=models.CASCADE, related_name='status_history')

    status = models.CharField(max_length=30, choices=CarWashRequest.STATUS_CHOICES)

    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    note = models.CharField(max_length=255, blank=True)

    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)



    class Meta:

        ordering = ['created_at']





class PaymentGateway(TimeStampedModel):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=80)

    code = models.SlugField(unique=True)

    is_active = models.BooleanField(default=True)

    priority = models.PositiveIntegerField(default=100)



    supports_card = models.BooleanField(default=False)

    supports_eft = models.BooleanField(default=False)

    supports_wallet = models.BooleanField(default=False)

    supports_split_payments = models.BooleanField(default=False)

    supports_refunds = models.BooleanField(default=False)

    supports_payouts = models.BooleanField(default=False)



    # Non-secret behavioural config only. Secrets belong in environment/settings.

    config = models.JSONField(default=dict, blank=True)



    class Meta:

        ordering = ['priority', 'name']



    def __str__(self):

        return self.name





class BusinessPaymentGateway(TimeStampedModel):

    business = models.ForeignKey(CarWashBusiness, on_delete=models.CASCADE, related_name='payment_gateways')

    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE, related_name='business_links')

    is_enabled = models.BooleanField(default=True)

    provider_account_reference = models.CharField(max_length=200, blank=True)

    settings = models.JSONField(default=dict, blank=True)



    class Meta:

        unique_together = [('business', 'gateway')]





class CarWashPayment(TimeStampedModel):

    METHOD_CHOICES = [

        ('card', 'Card'),

        ('eft', 'Instant EFT'),

        ('wallet', 'Wallet'),

        ('cash', 'Cash'),

    ]

    STATUS_CHOICES = [

        ('pending', 'Pending'),

        ('processing', 'Processing'),

        ('authorized', 'Authorized'),

        ('paid', 'Paid'),

        ('failed', 'Failed'),

        ('cancelled', 'Cancelled'),

        ('refunded', 'Refunded'),

        ('partially_refunded', 'Partially refunded'),

    ]

    SETTLEMENT_CHOICES = [

        ('gateway_split', 'Gateway split'),

        ('platform_collects', 'Platform collects'),

        ('provider_collects', 'Provider collects'),

        ('cash', 'Cash'),

    ]



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    wash_request = models.OneToOneField(CarWashRequest, on_delete=models.CASCADE, related_name='payment')

    gateway = models.ForeignKey(PaymentGateway, on_delete=models.PROTECT, null=True, blank=True)

    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)

    settlement_mode = models.CharField(max_length=30, choices=SETTLEMENT_CHOICES)



    currency = models.CharField(max_length=10, default='ZAR')

    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)

    platform_commission = models.DecimalField(max_digits=12, decimal_places=2)

    provider_amount = models.DecimalField(max_digits=12, decimal_places=2)

    gateway_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    tip_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))



    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')

    gateway_reference = models.CharField(max_length=200, blank=True)

    gateway_transaction_id = models.CharField(max_length=200, blank=True)

    gateway_response = models.JSONField(default=dict, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)





class PaymentAttempt(TimeStampedModel):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    payment = models.ForeignKey(CarWashPayment, on_delete=models.CASCADE, related_name='attempts')

    gateway = models.ForeignKey(PaymentGateway, on_delete=models.PROTECT)

    reference = models.CharField(max_length=200, blank=True)

    status = models.CharField(max_length=40, default='created')

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    response_data = models.JSONField(default=dict, blank=True)





class CarWashWallet(TimeStampedModel):

    business = models.OneToOneField(CarWashBusiness, on_delete=models.CASCADE, related_name='wallet')

    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    commission_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))





class CarWashLedgerEntry(TimeStampedModel):

    TYPE_CHOICES = [

        ('earning', 'Provider earning'),

        ('commission', 'Platform commission'),

        ('cash_debt', 'Cash commission debt'),

        ('payout', 'Payout'),

        ('adjustment', 'Adjustment'),

        ('refund', 'Refund'),

        ('tip', 'Tip'),

    ]



    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    business = models.ForeignKey(CarWashBusiness, on_delete=models.CASCADE, related_name='ledger_entries')

    wash_request = models.ForeignKey(CarWashRequest, on_delete=models.SET_NULL, null=True, blank=True)

    payment = models.ForeignKey(CarWashPayment, on_delete=models.SET_NULL, null=True, blank=True)

    entry_type = models.CharField(max_length=30, choices=TYPE_CHOICES)

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    description = models.CharField(max_length=255, blank=True)

    metadata = models.JSONField(default=dict, blank=True)



    class Meta:

        ordering = ['-created_at']





class CarWashReview(TimeStampedModel):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    wash_request = models.OneToOneField(CarWashRequest, on_delete=models.CASCADE, related_name='review')

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carwash_reviews')

    business = models.ForeignKey(CarWashBusiness, on_delete=models.CASCADE, related_name='reviews')

    worker = models.ForeignKey(CarWashWorker, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')

    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    comment = models.TextField(blank=True)



    class Meta:

        ordering = ['-created_at']
