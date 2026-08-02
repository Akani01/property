from django.urls import path
from . import views

urlpatterns = [
    path('google-login/', views.google_login, name='google_login'),
    path('google-signup/', views.google_signup, name='google_signup'),
    path('google-business-signup/', views.google_business_signup, name='google_business_signup'),
]