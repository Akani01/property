from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from . import views

router = DefaultRouter()

# Register all viewsets
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

# ===== MAINTENANCE VIEWSETS =====
router.register(r'maintenance-requests', views.MaintenanceRequestViewSet, basename='maintenance-requests')
router.register(r'maintenance-categories', views.MaintenanceCategoryViewSet, basename='maintenance-categories')
router.register(r'maintenance-comments', views.MaintenanceCommentViewSet, basename='maintenance-comments')

# ===== JOBS, POSTS, VIDEOS =====
router.register(r'jobs', views.JobViewSet, basename='jobs')
router.register(r'posts', views.PostViewSet, basename='posts')
router.register(r'videos', views.VideoViewSet, basename='videos')

# Only register driver-locations if real-time tracking is enabled
if getattr(settings, 'REALESTATE_SETTINGS', {}).get('ENABLE_REAL_TIME_TRACKING', False):
    router.register(r'driver-locations', views.DriverLocationViewSet, basename='driverlocation')

urlpatterns = [
    path('api/', include(router.urls)),
    
    # ===== PROPERTY TYPES =====
    path('api/property-types/', views.get_property_types, name='property_types'),
    path('api/property-types/add/', views.add_property_type_api, name='add_property_type_api'),
    path('api/features/add/', views.add_feature_api, name='add_feature_api'),
    
    # ===== GEOCODE =====
    path('api/geocode/', views.geocode_view, name='geocode'),
    path('api/geocode-address/', views.geocode_address_api, name='geocode_address_api'),
    path('api/properties/nearby/', views.nearby_properties, name='nearby_properties'),
    
    # ===== PROPERTY IMAGE MANAGEMENT =====
    path('api/properties/<uuid:pk>/update-image/', views.PropertyViewSet.as_view({'post': 'update_image'}), name='property_update_image'),
    path('api/properties/<uuid:pk>/remove-image/', views.PropertyViewSet.as_view({'post': 'remove_image'}), name='property_remove_image'),
    path('api/properties/<uuid:pk>/add-additional-image/', views.PropertyViewSet.as_view({'post': 'add_additional_image'}), name='property_add_additional_image'),
    path('api/properties/<uuid:pk>/remove-additional-image/', views.PropertyViewSet.as_view({'post': 'remove_additional_image'}), name='property_remove_additional_image'),
    path('api/properties/<uuid:pk>/delete/', views.PropertyViewSet.as_view({'post': 'delete'}), name='property_delete'),
    
    # ===== MAINTENANCE EXTRA ENDPOINTS =====
    path('api/maintenance-requests/stats/', views.MaintenanceRequestViewSet.as_view({'get': 'stats'}), name='maintenance_stats'),
    
    # ===== BUSINESS BOOKINGS =====
    path('api/business-bookings/', views.api_business_bookings, name='api_business_bookings'),
    
    # Like/Dislike
    path('api/properties/<uuid:property_id>/interact/', 
         views.toggle_property_interaction, 
         name='toggle_property_interaction'),
    
    path('api/properties/batch-interact/', 
         views.batch_property_interaction, 
         name='batch_property_interaction'),
    
    path('api/user/interactions/', 
         views.get_user_property_interactions, 
         name='get_user_property_interactions'),
    
    # Ratings
    path('api/properties/<uuid:property_id>/rate/', 
         views.rate_property, 
         name='rate_property'),
    
    path('api/properties/<uuid:property_id>/ratings/', 
         views.get_property_ratings, 
         name='get_property_ratings'),
    
    path('api/properties/<uuid:property_id>/rating-summary/', 
         views.get_property_rating_summary, 
         name='get_property_rating_summary'),
]