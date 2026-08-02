from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pwa.urls')),
    path('', include('hiring.urls')),  # Your hiring app
    path('', include('realestate.urls')),  # Real estate app
    path('api/', include('realestate.urls')),
    path('api/auth/', include('social_auth.urls')),
    path('', include('core.urls')),
    path('api/education/', include('education.urls')),
    # Redirect /api/notifications/* to /notifications/api/notifications/*
    path('api/notifications/', lambda request: HttpResponseRedirect('/notifications/api/notifications/')),
    path('api/notifications/<path:path>', lambda request, path: HttpResponseRedirect(f'/notifications/api/notifications/{path}')),
    
    # ===== ADD NOTIFICATIONS APP =====
    path('notifications/', include('notifications.urls')),  # <-- ADD THIS LINE
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)