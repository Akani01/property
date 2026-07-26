from django.contrib import admin
from .models import Grade, Subject, University, School, Bursary, QuestionPaper, BursaryApplication, EducationNews

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'grade', 'is_active']
    list_filter = ['grade', 'is_active']
    search_fields = ['name', 'code']

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ['name', 'province', 'city', 'is_active']
    list_filter = ['province', 'is_active']
    search_fields = ['name', 'city']

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'emis_number', 'school_type', 'province', 'city']
    list_filter = ['school_type', 'province', 'is_active']
    search_fields = ['name', 'emis_number', 'city']

@admin.register(Bursary)
class BursaryAdmin(admin.ModelAdmin):
    list_display = ['title', 'provider', 'field_of_study', 'level', 'closing_date']
    list_filter = ['field_of_study', 'level', 'is_active']
    search_fields = ['title', 'provider']

@admin.register(QuestionPaper)
class QuestionPaperAdmin(admin.ModelAdmin):
    list_display = ['title', 'grade', 'subject', 'year']
    list_filter = ['grade', 'subject', 'year']
    search_fields = ['title']

@admin.register(BursaryApplication)
class BursaryApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant', 'bursary', 'status', 'submitted_at']
    list_filter = ['status']
    search_fields = ['applicant__username', 'bursary__title']

@admin.register(EducationNews)
class EducationNewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_published', 'published_at']
    list_filter = ['category', 'is_published']
    search_fields = ['title', 'content']