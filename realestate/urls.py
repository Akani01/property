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

# ===== MAINTENANCE VIEWSETS - ADD THESE =====
router.register(r'maintenance/categories', views.MaintenanceCategoryViewSet, basename='maintenance-category')
router.register(r'maintenance/requests', views.MaintenanceRequestViewSet, basename='maintenance-request')
router.register(r'maintenance/comments', views.MaintenanceCommentViewSet, basename='maintenance-comment')

# Only register driver-locations if real-time tracking is enabled
if getattr(settings, 'REALESTATE_SETTINGS', {}).get('ENABLE_REAL_TIME_TRACKING', False):
    router.register(r'driver-locations', views.DriverLocationViewSet, basename='driverlocation')

urlpatterns = [
    path('', include(router.urls)),
    
    # ===== PROPERTY TYPES (Custom endpoint) =====
    path('property-types/', views.get_property_types, name='property_types'),
    path('api/properties/<str:pk>/', views.PropertyViewSet.as_view({'get': 'retrieve'}), name='property-detail'),
    path('api/properties/', views.PropertyViewSet.as_view({'get': 'list'}), name='property-list'),
    # ===== MAINTENANCE - Additional custom endpoints =====
    # These are for frontend compatibility with your existing JS
    path('maintenance/requests/stats/', views.MaintenanceRequestViewSet.as_view({'get': 'stats'}), name='maintenance_stats'),
    
    # For the specific endpoints your JS is calling
    path('maintenance/requests/<int:request_id>/', views.MaintenanceRequestViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='maintenance_request_detail'),
    
    path('maintenance/requests/<int:request_id>/update-status/', views.MaintenanceRequestViewSet.as_view({
        'post': 'update_status'
    }), name='maintenance_update_status'),
    
    path('maintenance/requests/<int:request_id>/add-comment/', views.MaintenanceRequestViewSet.as_view({
        'post': 'add_comment'
    }), name='maintenance_add_comment'),
    # 🗺️ Location/Geocoding endpoints
    path('api/geocode/', views.geocode_address_api, name='geocode_api'),
    path('api/properties/nearby/', views.nearby_properties, name='nearby_properties'),
    
    # ============================================
    # IMAGE MANAGEMENT ENDPOINTS
    # ============================================
    path('api/properties/<uuid:pk>/update-image/', views.PropertyViewSet.as_view({'post': 'update_image'}), name='property_update_image'),
    path('api/properties/<uuid:pk>/remove-image/', views.PropertyViewSet.as_view({'post': 'remove_image'}), name='property_remove_image'),
    path('api/properties/<uuid:pk>/add-additional-image/', views.PropertyViewSet.as_view({'post': 'add_additional_image'}), name='property_add_additional_image'),
    path('api/properties/<uuid:pk>/remove-additional-image/', views.PropertyViewSet.as_view({'post': 'remove_additional_image'}), name='property_remove_additional_image'),
    


    # ➕ Add endpoints
    path('api/property-types/add/', views.add_property_type_api, name='add_property_type_api'),
    path('api/features/add/', views.add_feature_api, name='add_feature_api'),
    
    # 🗑️ Delete property
    path('api/properties/<uuid:pk>/delete/', views.PropertyViewSet.as_view({'post': 'delete'}), name='property_delete'),
]
   