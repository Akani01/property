from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'preferences', views.NotificationPreferenceViewSet, basename='notification-preference')
router.register(r'devices', views.NotificationDeviceViewSet, basename='notification-device')
router.register(r'sound', views.NotificationSoundViewSet, basename='notification-sound')

urlpatterns = [
    # HTML Pages
    path('', views.notifications_page, name='notifications_page'),
    path('preferences/', views.notification_preferences_page, name='notification_preferences'),
    
    # API Routes
    path('api/', include(router.urls)),
    
    # Custom actions
    path('api/notifications/realtime/', views.NotificationViewSet.as_view({'get': 'realtime'}), name='api_realtime'),
    path('api/notifications/unread/count/', views.NotificationViewSet.as_view({'get': 'unread_count'}), name='api_unread_count'),
    path('api/notifications/create_test/', views.NotificationViewSet.as_view({'post': 'create_test'}), name='api_create_test'),
]