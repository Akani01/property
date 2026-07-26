from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

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

urlpatterns = [
    path('', include(router.urls)),
]