# benta/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect
from education import views as education_views
from hiring import views as hiring_views
from django.http import FileResponse, Http404
from django.conf import settings
import os


def assetlinks(request):
    path = os.path.join(settings.BASE_DIR, "assetlinks.json")
    if not os.path.exists(path):
        raise Http404("assetlinks.json not found")
    return FileResponse(open(path, "rb"), content_type="application/json")

urlpatterns = [
    # ============================================================
    # CUSTOM PWA MANIFEST — registered FIRST so it wins
    # ============================================================
    path('manifest.json', hiring_views.pwa_manifest, name='custom_pwa_manifest'),
    path(".well-known/assetlinks.json", assetlinks),
    path('admin/', admin.site.urls),
    path('', include('hiring.urls')),
    path('', include('pwa.urls')),
    path('', include('realestate.urls')),
    path('api/', include('realestate.urls')),
    path('', include('core.urls')),

    # Education HTML pages
    path('education/', education_views.education_home, name='education_home'),
    path('education/bursary/<int:pk>/', education_views.bursary_detail, name='education_bursary_detail'),
    path('education/university/<int:pk>/', education_views.university_detail, name='education_university_detail'),
    path('education/school/<int:pk>/', education_views.school_detail, name='education_school_detail'),
    path('education/paper/<int:pk>/', education_views.paper_detail, name='education_paper_detail'),
    path('education/news/<int:pk>/', education_views.news_detail, name='education_news_detail'),

    path('accounts/', include('allauth.urls')),
    path('api/education/', include('education.urls')),

    # Redirect /api/notifications/*
    path('api/notifications/', lambda request: HttpResponseRedirect('/notifications/api/notifications/')),
    path('api/notifications/<path:path>', lambda request, path: HttpResponseRedirect(f'/notifications/api/notifications/{path}')),

    path('', include('ads.urls')),
    path('notifications/', include('notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)