from django.contrib import admin

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


admin.site.register([
    CarWashBusiness,
    VehicleType,
    CarWashService,
    ServiceVehiclePrice,
    CarWashWorker,
    CarWashProviderLocation,
    CarWashQuote,
    CarWashRequest,
    CarWashStatusHistory,
    PaymentGateway,
    BusinessPaymentGateway,
    CarWashPayment,
    PaymentAttempt,
    CarWashWallet,
    CarWashLedgerEntry,
    CarWashReview,
])
