from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from . import views

router = DefaultRouter()

# Register all viewsets with explicit basenames
router.register(r'categories', views.PropertyCategoryViewSet, basename='category')
router.register(r'types', views.PropertyTypeViewSet, basename='type')
router.register(r'features', views.PropertyFeatureViewSet, basename='feature')
router.register(r'properties', views.PropertyViewSet, basename='property')
router.register(r'rooms', views.RoomViewSet, basename='room')
router.register(r'bookings', views.BookingViewSet, basename='booking')
router.register(r'availability', views.AvailabilityCalendarViewSet, basename='availability')
router.register(r'inquiries', views.BookingInquiryViewSet, basename='inquiry')
router.register(r'reviews', views.PropertyReviewViewSet, basename='review')
router.register(r'wishlists', views.WishlistViewSet, basename='wishlist')
router.register(r'analytics', views.PropertyAnalyticsViewSet, basename='analytics')

# Only register driver-locations if real-time tracking is enabled
if getattr(settings, 'REALESTATE_SETTINGS', {}).get('ENABLE_REAL_TIME_TRACKING', False):
    router.register(r'driver-locations', views.DriverLocationViewSet, basename='driverlocation')

urlpatterns = [
    path('', include(router.urls)),
]