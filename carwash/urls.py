from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r'businesses', views.CarWashBusinessViewSet, basename='carwash-business')
router.register(r'vehicles', views.VehicleTypeViewSet, basename='carwash-vehicle')
router.register(r'services', views.CarWashServiceViewSet, basename='carwash-service')
router.register(r'prices', views.ServiceVehiclePriceViewSet, basename='carwash-price')
router.register(r'workers', views.CarWashWorkerViewSet, basename='carwash-worker')
router.register(r'business-gateways', views.BusinessPaymentGatewayViewSet, basename='carwash-business-gateway')
router.register(r'payments', views.CarWashPaymentViewSet, basename='carwash-payment')
router.register(r'gateways', views.PaymentGatewayViewSet, basename='carwash-gateway')
router.register(r'reviews', views.CarWashReviewViewSet, basename='carwash-review')
router.register(r'requests', views.CarWashRequestViewSet, basename='carwash-request')


urlpatterns = [
    # Main map / workspace
    path('', views.carwash_map, name='carwash_map'),
    path('map/', views.carwash_map, name='carwash_map_alt'),

    # Location and discovery
    path('api/business/location/', views.update_business_location, name='carwash_business_location'),
    path('api/provider/location/', views.update_provider_location, name='carwash_provider_location'),
    path('api/reverse-geocode/', views.reverse_geocode, name='carwash_reverse_geocode'),
    path('api/nearby/', views.nearby_providers, name='carwash_nearby'),

    # Business public catalogue
    path(
        'api/businesses/<uuid:business_id>/catalog/',
        views.business_catalog,
        name='carwash_business_catalog',
    ),

    # Quote + payment
    path('api/quote/', views.create_quote, name='carwash_create_quote'),
    path(
        'api/requests/<uuid:request_id>/payment/',
        views.create_payment,
        name='carwash_create_payment',
    ),

    # Shared OppoGlobe messaging
    path(
        'api/businesses/<uuid:business_id>/message/',
        views.start_carwash_business_conversation,
        name='carwash_business_message',
    ),
    path(
        'api/requests/<uuid:request_id>/message/',
        views.start_carwash_request_conversation,
        name='carwash_request_message',
    ),

    # Provider payout bank details
    path(
        'api/payout-details/',
        views.business_payout_details,
        name='carwash_payout_details',
    ),

    path(
        'api/money-summary/',
        views.business_money_summary,
        name='carwash_money_summary',
    ),

    # DRF ViewSets / actions:
    # /api/businesses/me/
    # /api/requests/<id>/accept/
    # /api/requests/<id>/set-status/
    # /api/requests/<id>/tracking/
    # /api/gateways/
    # /api/payments/
    path('api/', include(router.urls)),
]
