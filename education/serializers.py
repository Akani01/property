# education/serializers.py
from rest_framework import serializers
from .models import (
    Grade, Subject, University, School, Bursary, QuestionPaper,
    BursaryApplication, UniversityApplication, SchoolApplication, EducationNews
)
from django.contrib.auth import get_user_model
from django.utils import timezone

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
    # Read-only nested serializers for display
    universities_detail = UniversitySerializer(source='universities', many=True, read_only=True)
    grades_detail = GradeSerializer(source='grades', many=True, read_only=True)
    
    # Writeable fields for many-to-many relationships (expecting list of IDs)
    universities = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.filter(is_active=True),
        many=True,
        required=False,
        write_only=True
    )
    grades = serializers.PrimaryKeyRelatedField(
        queryset=Grade.objects.filter(is_active=True),
        many=True,
        required=False,
        write_only=True
    )
    
    days_until_closing = serializers.SerializerMethodField()
    
    class Meta:
        model = Bursary
        fields = [
            'id', 'title', 'description', 'provider', 'provider_website', 'provider_logo',
            'field_of_study', 'level', 
            'universities', 'universities_detail',  # Writeable and read-only versions
            'grades', 'grades_detail',  # Writeable and read-only versions
            'amount', 'closing_date', 'application_fee', 
            'requirements', 'required_documents', 'contact_email', 
            'contact_phone', 'is_featured', 'is_active', 
            'days_until_closing', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_days_until_closing(self, obj):
        return obj.days_until_closing()
    
    def validate_closing_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Closing date must be in the future")
        return value
    
    def create(self, validated_data):
        # Extract many-to-many fields
        universities = validated_data.pop('universities', [])
        grades = validated_data.pop('grades', [])
        
        # Create the bursary
        bursary = Bursary.objects.create(**validated_data)
        
        # Set many-to-many relationships
        if universities:
            bursary.universities.set(universities)
        if grades:
            bursary.grades.set(grades)
        
        return bursary
    
    def update(self, instance, validated_data):
        # Extract many-to-many fields
        universities = validated_data.pop('universities', None)
        grades = validated_data.pop('grades', None)
        
        # Update regular fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update many-to-many relationships
        if universities is not None:
            instance.universities.set(universities)
        if grades is not None:
            instance.grades.set(grades)
        
        return instance


class QuestionPaperSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(source='grade.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    
    class Meta:
        model = QuestionPaper
        fields = [
            'id', 'title', 'description', 'grade', 'grade_name', 
            'subject', 'subject_name', 'year', 'term', 'paper_number', 
            'total_marks', 'duration_minutes', 'file', 'file_name', 
            'file_size', 'is_public', 'download_count', 
            'uploaded_by', 'uploaded_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'download_count', 'file_size', 'file_name']


class BursaryApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.username', read_only=True)
    bursary_title = serializers.CharField(source='bursary.title', read_only=True)
    current_grade_name = serializers.CharField(source='current_grade.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = BursaryApplication
        fields = [
            'id', 'applicant', 'applicant_name', 'bursary', 'bursary_title', 
            'status', 'status_display', 'full_name', 'email', 'phone', 
            'date_of_birth', 'id_number', 'current_grade', 'current_grade_name',
            'current_institution', 'current_institution_type', 'academic_average', 
            'motivation', 'cv', 'academic_transcript', 'id_document',
            'other_documents', 'admin_notes', 'submitted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['applicant', 'applicant_name', 'created_at', 'updated_at', 'submitted_at']
    
    def validate(self, data):
        # Ensure required fields are present
        required_fields = ['full_name', 'email', 'phone', 'date_of_birth']
        for field in required_fields:
            if field not in data or not data[field]:
                raise serializers.ValidationError({field: f"{field} is required"})
        return data


class UniversityApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.username', read_only=True)
    university_name = serializers.CharField(source='university.name', read_only=True)
    current_grade_name = serializers.CharField(source='current_grade.name', read_only=True)
    subjects_list = SubjectSerializer(source='subjects', many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Writeable subjects field (expects list of IDs)
    subjects = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.filter(is_active=True),
        many=True,
        required=False,
        write_only=True
    )
    
    class Meta:
        model = UniversityApplication
        fields = [
            'id', 'applicant', 'applicant_name', 'university', 'university_name', 
            'status', 'status_display', 'full_name', 'email', 'phone', 
            'date_of_birth', 'id_number', 'current_grade', 'current_grade_name',
            'subjects', 'subjects_list', 'academic_average', 'program_of_interest', 
            'program_code', 'motivation', 'cv', 'academic_transcript',
            'id_document', 'admin_notes', 'submitted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['applicant', 'applicant_name', 'created_at', 'updated_at', 'submitted_at']
    
    def create(self, validated_data):
        subjects = validated_data.pop('subjects', [])
        application = UniversityApplication.objects.create(**validated_data)
        if subjects:
            application.subjects.set(subjects)
        return application
    
    def update(self, instance, validated_data):
        subjects = validated_data.pop('subjects', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if subjects is not None:
            instance.subjects.set(subjects)
        return instance


class SchoolApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.username', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    current_grade_name = serializers.CharField(source='current_grade.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SchoolApplication
        fields = [
            'id', 'applicant', 'applicant_name', 'school', 'school_name', 
            'status', 'status_display', 'student_full_name', 'student_email', 
            'student_phone', 'date_of_birth', 'id_number', 'parent_name', 
            'parent_phone', 'parent_email', 'current_grade', 'current_grade_name',
            'previous_school', 'birth_certificate', 'report_card',
            'admin_notes', 'submitted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['applicant', 'applicant_name', 'created_at', 'updated_at', 'submitted_at']


class EducationNewsSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = EducationNews
        fields = [
            'id', 'title', 'content', 'summary', 'image', 
            'author', 'author_name', 'category', 'category_display',
            'is_published', 'published_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'author']


# ============================================
# ADDITIONAL SERIALIZERS FOR DROPDOWNS & SIMPLE RESPONSES
# ============================================

class SimpleGradeSerializer(serializers.ModelSerializer):
    """Simplified serializer for dropdowns"""
    class Meta:
        model = Grade
        fields = ['id', 'name', 'code']


class SimpleSubjectSerializer(serializers.ModelSerializer):
    """Simplified serializer for dropdowns"""
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code', 'grade_id']


class SimpleUniversitySerializer(serializers.ModelSerializer):
    """Simplified serializer for dropdowns"""
    class Meta:
        model = University
        fields = ['id', 'name', 'city', 'province']


class SimpleSchoolSerializer(serializers.ModelSerializer):
    """Simplified serializer for dropdowns"""
    class Meta:
        model = School
        fields = ['id', 'name', 'city', 'province', 'school_type']