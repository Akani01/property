from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdViewSet, AdImpressionViewSet, 
    AdClickViewSet, AdConversionViewSet
)

router = DefaultRouter()
router.register(r'ads', AdViewSet, basename='ad')
router.register(r'impressions', AdImpressionViewSet, basename='impression')
router.register(r'clicks', AdClickViewSet, basename='click')
router.register(r'conversions', AdConversionViewSet, basename='conversion')

urlpatterns = [
    path('api/', include(router.urls)),
]