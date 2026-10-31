from django.urls import path
from . import views
app_name = 'pricecheck'
urlpatterns = [
    path('', views.home, name='home'),
    path('api/products/', views.search, name='products'),
    path('api/products/<int:pk>/offers/', views.offers, name='offers'),
    path('api/branches/', views.branches, name='branches'),
]
