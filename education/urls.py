# education/urls.py
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

# HTML View URLs (for the education pages)
html_urlpatterns = [
    # Education Hub - main page
    path('', views.education_home, name='education_home'),
    
    # Detail pages
    path('bursary/<int:pk>/', views.bursary_detail, name='education_bursary_detail'),
    path('university/<int:pk>/', views.university_detail, name='education_university_detail'),
    path('school/<int:pk>/', views.school_detail, name='education_school_detail'),
    path('paper/<int:pk>/', views.paper_detail, name='education_paper_detail'),
    path('news/<int:pk>/', views.news_detail, name='education_news_detail'),
]

# API URLs
urlpatterns = [
    path('', include(router.urls)),
]