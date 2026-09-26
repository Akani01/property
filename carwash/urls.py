from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'carwash'

router = DefaultRouter()
router.register(r'businesses', views.CarWashBusinessViewSet, basename='carwash-business')
router.register(r'vehicles', views.VehicleTypeViewSet, basename='carwash-vehicle')
router.register(r'services', views.CarWashServiceViewSet, basename='carwash-service')
router.register(r'prices', views.ServiceVehiclePriceViewSet, basename='carwash-price')
router.register(r'requests', views.CarWashRequestViewSet, basename='carwash-request')
router.register(r'workers', views.CarWashWorkerViewSet, basename='carwash-worker')
router.register(r'payments', views.CarWashPaymentViewSet, basename='carwash-payment')
router.register(r'business-gateways', views.BusinessPaymentGatewayViewSet, basename='carwash-business-gateway')
router.register(r'gateways', views.PaymentGatewayViewSet, basename='carwash-gateway')
router.register(r'reviews', views.CarWashReviewViewSet, basename='carwash-review')

urlpatterns = [
    path('', views.carwash_map, name='map'),
    path('api/', include(router.urls)),
    path('api/reverse-geocode/', views.reverse_geocode, name='reverse-geocode'),
    path('api/business/location/', views.update_business_location, name='business-location'),
    path('api/nearby/', views.nearby_providers, name='nearby-providers'),
    path('api/businesses/<uuid:business_id>/catalog/', views.business_catalog, name='business-catalog'),
    path('api/quote/', views.create_quote, name='create-quote'),
    path('api/provider/location/', views.update_provider_location, name='provider-location'),
    path('api/requests/<uuid:request_id>/payment/', views.create_payment, name='create-payment'),
]
