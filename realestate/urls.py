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

# ===== AGENT PROFILE API =====
router.register(r'agent-profiles', views.AgentProfileViewSet, basename='agent-profile')

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
    path('bookings/<uuid:pk>/', views.booking_detail_view, name='booking_detail'),
    
    # Share endpoints
    path('api/share/property/<uuid:property_id>/', views.share_property, name='share_property'),
    path('api/share/post/<int:post_id>/', views.share_post, name='share_post'),
    path('api/share/job/<int:job_id>/', views.share_job, name='share_job'),
    path('api/share/education/<str:type>/<int:item_id>/', views.share_education, name='share_education'),
    
    # API Routes
    path('api/agent-for-property/<uuid:property_id>/', views.get_agent_for_property, name='agent-for-property'),
    
    # Agent Lists
    path('api/featured-agents/', views.featured_agents, name='featured-agents'),
    path('api/top-agents/', views.top_agents, name='top-agents'),
    
    # Contact Methods (Internal Messaging First)
    path('api/agent-contact-methods/<uuid:agent_id>/', views.agent_contact_methods, name='agent-contact-methods'),
    path('api/check-agent-availability/<uuid:agent_id>/', views.check_agent_availability, name='check-agent-availability'),
    
    # Country Detection
    path('api/detect-country/', views.detect_country_from_number, name='detect-country'),
    path('api/countries/', views.list_countries, name='list-countries'),
    
    # Tracking
    path('api/track-agent-contact/', views.track_agent_contact, name='track-agent-contact'),
    
    # Admin
    path('api/admin/verify-agent/<uuid:agent_id>/', views.admin_verify_agent, name='admin-verify-agent'),
    path('api/admin/feature-agent/<uuid:agent_id>/', views.admin_feature_agent, name='admin-feature-agent'),

    # ============================================================
    # AGENT PROFILE PAGES (HTML)
    # ============================================================
    path('agent/create/', views.agent_profile_create, name='agent_profile_create'),
    path('agent/edit/<int:agent_id>/', views.agent_profile_edit, name='agent_profile_edit'),
    path('agent/<int:agent_id>/', views.agent_profile_view, name='agent_profile_view'),

    # ============================================================
    # PROPERTY DETAIL PAGE - USE 'pk' to match the view
    # ============================================================
    path('properties/<uuid:pk>/', views.property_detail, name='property_detail'),
]