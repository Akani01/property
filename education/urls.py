# education/urls.py - UPDATED (Keeping ALL original routes + adding new ones)

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'grades', views.GradeViewSet, basename='education-grade')
router.register(r'subjects', views.SubjectViewSet, basename='education-subject')
router.register(r'universities', views.UniversityViewSet, basename='education-university')
router.register(r'schools', views.SchoolViewSet, basename='education-school')
router.register(r'bursaries', views.BursaryViewSet, basename='education-bursary')
router.register(r'papers', views.QuestionPaperViewSet, basename='education-paper')
router.register(r'bursary-applications', views.BursaryApplicationViewSet, basename='education-bursary-application')
router.register(r'university-applications', views.UniversityApplicationViewSet, basename='education-university-application')
router.register(r'school-applications', views.SchoolApplicationViewSet, basename='education-school-application')
router.register(r'news', views.EducationNewsViewSet, basename='education-news')

# HTML View URLs
html_urlpatterns = [
    # ===== ORIGINAL ROUTES (KEEP AS IS) =====
    # Education Hub - main page
    path('', views.education_home, name='education_home'),
    
    # Detail pages
    path('bursary/<int:pk>/', views.bursary_detail, name='education_bursary_detail'),
    path('university/<int:pk>/', views.university_detail, name='education_university_detail'),
    path('school/<int:pk>/', views.school_detail, name='education_school_detail'),
    path('paper/<int:pk>/', views.paper_detail, name='education_paper_detail'),
    path('news/<int:pk>/', views.news_detail, name='education_news_detail'),
    
    # ===== NEW APPLICATION ROUTES (ADD THESE) =====
    # Application System - Selection & Apply
    path('apply/', views.apply_selection, name='education_apply_selection'),
    path('apply/bursary/', views.apply_bursary, name='education_apply_bursary'),
    path('apply/bursary/<int:bursary_id>/', views.apply_bursary, name='education_apply_bursary_with_id'),
    path('apply/university/', views.apply_university, name='education_apply_university'),
    path('apply/university/<int:university_id>/', views.apply_university, name='education_apply_university_with_id'),
    path('apply/school/', views.apply_school, name='education_apply_school'),
    path('apply/school/<int:school_id>/', views.apply_school, name='education_apply_school_with_id'),
    
    # My Applications
    path('my-applications/', views.my_applications, name='education_my_applications'),
    path('bursary-application/<uuid:pk>/', views.bursary_application_detail, name='education_bursary_application_detail'),
    path('university-application/<uuid:pk>/', views.university_application_detail, name='education_university_application_detail'),
    path('school-application/<uuid:pk>/', views.school_application_detail, name='education_school_application_detail'),
    path('application-success/<uuid:app_id>/', views.application_success, name='education_application_success'),
]

# API URLs - KEEP YOUR ORIGINAL STRUCTURE
urlpatterns = [
    path('', include(router.urls)),
]

# ===== IMPORTANT: Add the HTML URLs to the urlpatterns =====
urlpatterns += html_urlpatterns