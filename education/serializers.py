from rest_framework import serializers
from .models import (
    Grade, Subject, University, School, Bursary, QuestionPaper,
    BursaryApplication, UniversityApplication, SchoolApplication, EducationNews
)
from django.contrib.auth import get_user_model

User = get_user_model()


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = ['id', 'name', 'code', 'description', 'order', 'is_active', 'created_at', 'updated_at']


class SubjectSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(source='grade.name', read_only=True)
    
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code', 'description', 'grade', 'grade_name', 'is_active', 'created_at', 'updated_at']


class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ['id', 'name', 'code', 'province', 'city', 'address', 'website', 'phone', 'email', 
                  'description', 'logo', 'is_active', 'created_at', 'updated_at']


class SchoolSerializer(serializers.ModelSerializer):
    school_type_display = serializers.CharField(source='get_school_type_display', read_only=True)
    
    class Meta:
        model = School
        fields = ['id', 'name', 'emis_number', 'school_type', 'school_type_display', 'province', 'district',
                  'city', 'address', 'phone', 'email', 'website', 'principal_name', 'is_public', 
                  'is_active', 'created_at', 'updated_at']


class BursarySerializer(serializers.ModelSerializer):
    universities = UniversitySerializer(many=True, read_only=True)
    grades = GradeSerializer(many=True, read_only=True)
    days_until_closing = serializers.SerializerMethodField()
    
    class Meta:
        model = Bursary
        fields = ['id', 'title', 'description', 'provider', 'provider_website', 'provider_logo',
                  'field_of_study', 'level', 'universities', 'grades', 'amount', 'closing_date', 
                  'application_fee', 'requirements', 'required_documents', 'contact_email', 
                  'contact_phone', 'is_featured', 'is_active', 'days_until_closing', 'created_at', 
                  'updated_at']
    
    def get_days_until_closing(self, obj):
        return obj.days_until_closing()


class QuestionPaperSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(source='grade.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    
    class Meta:
        model = QuestionPaper
        fields = ['id', 'title', 'description', 'grade', 'grade_name', 'subject', 'subject_name',
                  'year', 'term', 'paper_number', 'total_marks', 'duration_minutes', 'file', 
                  'file_name', 'file_size', 'is_public', 'download_count', 'uploaded_by', 
                  'uploaded_by_name', 'created_at', 'updated_at']


class BursaryApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.username', read_only=True)
    bursary_title = serializers.CharField(source='bursary.title', read_only=True)
    current_grade_name = serializers.CharField(source='current_grade.name', read_only=True)
    
    class Meta:
        model = BursaryApplication
        fields = ['id', 'applicant', 'applicant_name', 'bursary', 'bursary_title', 'status',
                  'full_name', 'email', 'phone', 'date_of_birth', 'id_number', 'current_grade',
                  'current_grade_name', 'current_institution', 'current_institution_type',
                  'academic_average', 'motivation', 'cv', 'academic_transcript', 'id_document',
                  'other_documents', 'admin_notes', 'submitted_at', 'created_at', 'updated_at']


class UniversityApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.username', read_only=True)
    university_name = serializers.CharField(source='university.name', read_only=True)
    current_grade_name = serializers.CharField(source='current_grade.name', read_only=True)
    subjects_list = SubjectSerializer(source='subjects', many=True, read_only=True)
    
    class Meta:
        model = UniversityApplication
        fields = ['id', 'applicant', 'applicant_name', 'university', 'university_name', 'status',
                  'full_name', 'email', 'phone', 'date_of_birth', 'id_number', 'current_grade',
                  'current_grade_name', 'subjects', 'subjects_list', 'academic_average',
                  'program_of_interest', 'program_code', 'motivation', 'cv', 'academic_transcript',
                  'id_document', 'admin_notes', 'submitted_at', 'created_at', 'updated_at']


class SchoolApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.username', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    current_grade_name = serializers.CharField(source='current_grade.name', read_only=True)
    
    class Meta:
        model = SchoolApplication
        fields = ['id', 'applicant', 'applicant_name', 'school', 'school_name', 'status',
                  'student_full_name', 'student_email', 'student_phone', 'date_of_birth', 
                  'id_number', 'parent_name', 'parent_phone', 'parent_email', 'current_grade',
                  'current_grade_name', 'previous_school', 'birth_certificate', 'report_card',
                  'admin_notes', 'submitted_at', 'created_at', 'updated_at']


class EducationNewsSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    
    class Meta:
        model = EducationNews
        fields = ['id', 'title', 'content', 'summary', 'image', 'author', 'author_name',
                  'category', 'is_published', 'published_at', 'created_at', 'updated_at']