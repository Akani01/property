# education/views.py - COMPLETE (Original + New Functions)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.urls import reverse
from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from datetime import datetime
from django.contrib.auth import get_user_model
import pandas as pd
import os
import re
import json
from django import template
from django.template import Library

register = template.Library()

from .models import (
    Grade, Subject, University, School, Bursary, QuestionPaper,
    BursaryApplication, UniversityApplication, SchoolApplication, EducationNews
)
from .serializers import (
    GradeSerializer, SubjectSerializer, UniversitySerializer, SchoolSerializer,
    BursarySerializer, QuestionPaperSerializer, BursaryApplicationSerializer,
    UniversityApplicationSerializer, SchoolApplicationSerializer, EducationNewsSerializer
)

User = get_user_model()


# ============================================
# API VIEWSETS
# ============================================

class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.filter(is_active=True)
    serializer_class = GradeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.filter(is_active=True)
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    @action(detail=False, methods=['get'])
    def by_grade(self, request):
        grade_id = request.query_params.get('grade_id')
        if grade_id:
            subjects = self.queryset.filter(grade_id=grade_id)
            serializer = self.get_serializer(subjects, many=True)
            return Response({'success': True, 'subjects': serializer.data})
        return Response({'success': False, 'error': 'grade_id required'})


class UniversityViewSet(viewsets.ModelViewSet):
    queryset = University.objects.filter(is_active=True)
    serializer_class = UniversitySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    
    @action(detail=False, methods=['get'])
    def by_province(self, request):
        province = request.query_params.get('province')
        if province:
            universities = self.queryset.filter(province=province)
            serializer = self.get_serializer(universities, many=True)
            return Response({'success': True, 'universities': serializer.data})
        return Response({'success': False, 'error': 'province required'})
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if query:
            universities = self.queryset.filter(
                Q(name__icontains=query) | 
                Q(city__icontains=query) |
                Q(province__icontains=query)
            )
            serializer = self.get_serializer(universities, many=True)
            return Response({'success': True, 'universities': serializer.data})


class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.filter(is_active=True)
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    
    @action(detail=False, methods=['post'])
    def upload_excel(self, request):
        if not request.user.is_superuser and not request.user.user_type == 'admin':
            return Response({'success': False, 'error': 'Admin access required'}, status=403)
        
        file = request.FILES.get('file')
        if not file:
            return Response({'success': False, 'error': 'No file uploaded'})
        
        try:
            df = pd.read_excel(file)
        except Exception as e:
            return Response({'success': False, 'error': f'Invalid Excel file: {str(e)}'})
        
        required_columns = ['name']
        for col in required_columns:
            if col not in df.columns:
                return Response({'success': False, 'error': f'Missing column: {col}'})
        
        created_count = 0
        updated_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                school_type = row.get('school_type', 'secondary')
                valid_types = ['primary', 'secondary', 'combined', 'special', 'early_childhood', 'other']
                if school_type not in valid_types:
                    school_type = 'secondary'
                
                school_data = {
                    'name': str(row['name'])[:200],
                    'emis_number': str(row.get('emis_number', ''))[:20] if pd.notna(row.get('emis_number')) else None,
                    'school_type': school_type,
                    'province': str(row.get('province', ''))[:100] if pd.notna(row.get('province')) else '',
                    'district': str(row.get('district', ''))[:100] if pd.notna(row.get('district')) else '',
                    'city': str(row.get('city', ''))[:100] if pd.notna(row.get('city')) else '',
                    'address': str(row.get('address', '')) if pd.notna(row.get('address')) else '',
                    'phone': str(row.get('phone', ''))[:20] if pd.notna(row.get('phone')) else '',
                    'email': str(row.get('email', ''))[:254] if pd.notna(row.get('email')) else '',
                    'website': str(row.get('website', ''))[:200] if pd.notna(row.get('website')) else '',
                    'principal_name': str(row.get('principal_name', ''))[:200] if pd.notna(row.get('principal_name')) else '',
                    'is_public': True if row.get('is_public', True) in [True, 'True', 'true', 'Yes', 'yes', '1'] else False,
                    'is_active': True,
                }
                
                if school_data['emis_number']:
                    school, created = School.objects.update_or_create(
                        emis_number=school_data['emis_number'],
                        defaults=school_data
                    )
                else:
                    school, created = School.objects.update_or_create(
                        name=school_data['name'],
                        defaults=school_data
                    )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                    
            except Exception as e:
                errors.append(f'Row {index + 2}: {str(e)}')
        
        return Response({
            'success': True,
            'message': f'Successfully processed {created_count + updated_count} schools',
            'created': created_count,
            'updated': updated_count,
            'errors': errors
        })
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        province = request.query_params.get('province', '')
        school_type = request.query_params.get('school_type', '')
        
        schools = self.queryset
        if query:
            schools = schools.filter(
                Q(name__icontains=query) | 
                Q(city__icontains=query) |
                Q(district__icontains=query) |
                Q(emis_number__icontains=query)
            )
        if province:
            schools = schools.filter(province=province)
        if school_type:
            schools = schools.filter(school_type=school_type)
        
        serializer = self.get_serializer(schools[:100], many=True)
        return Response({'success': True, 'schools': serializer.data})


class BursaryViewSet(viewsets.ModelViewSet):
    queryset = Bursary.objects.filter(is_active=True)
    serializer_class = BursarySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        bursaries = self.queryset.filter(is_featured=True)
        serializer = self.get_serializer(bursaries, many=True)
        return Response({'success': True, 'bursaries': serializer.data})
    
    @action(detail=False, methods=['get'])
    def filter(self, request):
        level = request.query_params.get('level', '')
        field = request.query_params.get('field', '')
        
        bursaries = self.queryset
        if level:
            bursaries = bursaries.filter(level=level)
        if field:
            bursaries = bursaries.filter(field_of_study=field)
        
        bursaries = bursaries.filter(closing_date__gte=timezone.now().date())
        
        serializer = self.get_serializer(bursaries, many=True)
        return Response({'success': True, 'bursaries': serializer.data})


class QuestionPaperViewSet(viewsets.ModelViewSet):
    queryset = QuestionPaper.objects.all()
    serializer_class = QuestionPaperSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return super().get_queryset()
        return self.queryset.filter(is_public=True)
    
    @action(detail=False, methods=['post'])
    def upload_multiple(self, request):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': 'Authentication required'}, status=401)
        
        files = request.FILES.getlist('files')
        if not files:
            return Response({'success': False, 'error': 'No files uploaded'})
        
        grade_id = request.data.get('grade_id')
        subject_id = request.data.get('subject_id')
        year = request.data.get('year')
        
        if not all([grade_id, subject_id, year]):
            return Response({'success': False, 'error': 'grade_id, subject_id, and year are required'})
        
        try:
            grade = Grade.objects.get(id=grade_id)
            subject = Subject.objects.get(id=subject_id)
        except (Grade.DoesNotExist, Subject.DoesNotExist):
            return Response({'success': False, 'error': 'Invalid grade or subject'})
        
        created = []
        errors = []
        
        for file in files:
            try:
                base_name = os.path.splitext(file.name)[0]
                title = base_name.replace('_', ' ').replace('-', ' ').title()
                
                paper = QuestionPaper.objects.create(
                    title=title,
                    grade=grade,
                    subject=subject,
                    year=int(year),
                    file=file,
                    file_name=file.name,
                    uploaded_by=request.user,
                    is_public=True
                )
                created.append(paper)
            except Exception as e:
                errors.append(f'{file.name}: {str(e)}')
        
        serializer = self.get_serializer(created, many=True)
        return Response({
            'success': True,
            'message': f'Uploaded {len(created)} papers',
            'papers': serializer.data,
            'errors': errors
        })
    
    @action(detail=False, methods=['get'])
    def by_grade_subject(self, request):
        grade_id = request.query_params.get('grade_id')
        subject_id = request.query_params.get('subject_id')
        
        papers = self.get_queryset()
        if grade_id:
            papers = papers.filter(grade_id=grade_id)
        if subject_id:
            papers = papers.filter(subject_id=subject_id)
        
        serializer = self.get_serializer(papers, many=True)
        return Response({'success': True, 'papers': serializer.data})


class BursaryApplicationViewSet(viewsets.ModelViewSet):
    queryset = BursaryApplication.objects.all()
    serializer_class = BursaryApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.user_type == 'admin':
            return super().get_queryset()
        return self.queryset.filter(applicant=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)
    
    @action(detail=False, methods=['post'])
    def submit(self, request):
        application_id = request.data.get('application_id')
        try:
            application = self.get_queryset().get(id=application_id)
            if application.status == 'draft':
                application.submit()
                return Response({'success': True, 'message': 'Application submitted'})
            return Response({'success': False, 'error': 'Application already submitted'})
        except BursaryApplication.DoesNotExist:
            return Response({'success': False, 'error': 'Application not found'})


class UniversityApplicationViewSet(viewsets.ModelViewSet):
    queryset = UniversityApplication.objects.all()
    serializer_class = UniversityApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.user_type == 'admin':
            return super().get_queryset()
        return self.queryset.filter(applicant=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)


class SchoolApplicationViewSet(viewsets.ModelViewSet):
    queryset = SchoolApplication.objects.all()
    serializer_class = SchoolApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.user_type == 'admin':
            return super().get_queryset()
        return self.queryset.filter(applicant=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)


class EducationNewsViewSet(viewsets.ModelViewSet):
    queryset = EducationNews.objects.filter(is_published=True)
    serializer_class = EducationNewsSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.user_type == 'admin':
            return EducationNews.objects.all()
        return self.queryset


# ============================================
# ============================================
# ORIGINAL HTML VIEWS (KEEP AS IS)
# ============================================
# ============================================

def education_home(request):
    """Single unified education page for all education content"""
    grades = Grade.objects.filter(is_active=True).order_by('order')
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    universities = University.objects.filter(is_active=True).order_by('name')
    schools = School.objects.filter(is_active=True).order_by('name')
    
    bursaries = Bursary.objects.filter(
        is_active=True, 
        closing_date__gte=timezone.now().date()
    ).order_by('-created_at')[:50]
    
    papers = QuestionPaper.objects.filter(is_public=True).select_related('grade', 'subject').order_by('-year', 'subject__name')[:50]
    news = EducationNews.objects.filter(is_published=True).order_by('-published_at')[:10]
    
    field_choices = dict(Bursary.FIELD_CHOICES)
    level_choices = dict(Bursary.LEVEL_CHOICES)
    
    available_fields = Bursary.objects.filter(is_active=True).values_list('field_of_study', flat=True).distinct()
    available_levels = Bursary.objects.filter(is_active=True).values_list('level', flat=True).distinct()
    
    is_admin = request.user.is_authenticated and (request.user.is_superuser or getattr(request.user, 'user_type', '') == 'admin')
    
    context = {
        'grades': grades,
        'subjects': subjects,
        'universities': universities,
        'schools': schools,
        'bursaries': bursaries,
        'papers': papers,
        'news': news,
        'field_choices': field_choices,
        'level_choices': level_choices,
        'available_fields': available_fields,
        'available_levels': available_levels,
        'is_admin': is_admin,
    }
    
    return render(request, 'education/education_home.html', context)


def bursary_detail(request, pk):
    bursary = get_object_or_404(Bursary, id=pk, is_active=True)
    universities = bursary.universities.filter(is_active=True)
    grades = bursary.grades.filter(is_active=True)
    
    similar = Bursary.objects.filter(
        is_active=True,
        closing_date__gte=timezone.now().date()
    ).exclude(id=pk).filter(
        Q(field_of_study=bursary.field_of_study) | 
        Q(level=bursary.level)
    ).distinct()[:5]
    
    context = {
        'bursary': bursary,
        'universities': universities,
        'grades': grades,
        'similar': similar,
        'days_left': bursary.days_until_closing(),
    }
    
    return render(request, 'education/bursary_detail.html', context)


def university_detail(request, pk):
    university = get_object_or_404(University, id=pk, is_active=True)
    bursaries = university.bursaries.filter(is_active=True, closing_date__gte=timezone.now().date())[:10]
    context = {'university': university, 'bursaries': bursaries}
    return render(request, 'education/university_detail.html', context)


def school_detail(request, pk):
    school = get_object_or_404(School, id=pk, is_active=True)
    context = {'school': school}
    return render(request, 'education/school_detail.html', context)


def paper_detail(request, pk):
    paper = get_object_or_404(QuestionPaper, id=pk, is_public=True)
    paper.download_count += 1
    paper.save()
    context = {'paper': paper}
    return render(request, 'education/paper_detail.html', context)


def news_detail(request, pk):
    news_item = get_object_or_404(EducationNews, id=pk, is_published=True)
    context = {'news': news_item}
    return render(request, 'education/news_detail.html', context)


def news_list(request):
    news_items = EducationNews.objects.filter(is_published=True).order_by('-published_at')
    paginator = Paginator(news_items, 20)
    page = request.GET.get('page', 1)
    news_page = paginator.get_page(page)
    
    categories = EducationNews.objects.filter(is_published=True).values_list('category', flat=True).distinct()
    category_choices = dict(EducationNews.CATEGORY_CHOICES)
    
    is_admin = request.user.is_authenticated and (request.user.is_superuser or getattr(request.user, 'user_type', '') == 'admin')
    
    context = {
        'news_items': news_page,
        'categories': categories,
        'category_choices': category_choices,
        'is_admin': is_admin,
    }
    
    return render(request, 'education/news_list.html', context)


# ============================================
# ============================================
# NEW HTML VIEWS (ADD THESE)
# ============================================
# ============================================

def parse_application_message(message):
    """Parse a single message input into structured data"""
    data = {}
    lines = message.split('\n')
    
    patterns = {
        'full_name': r'(?:Full[_\s]+Names?|Name[s]?|Applicant[s]?)[\s:]+([^\n]+)',
        'email': r'(?:Email|E-Mail)[\s:]+([^\n@]+@[^\n]+)',
        'phone': r'(?:Phone|Cell|Mobile|Tel|Contact)[\s:]+([^\n]+)',
        'id_number': r'(?:ID|ID Number|Identity Number)[\s:]+([^\n]+)',
        'date_of_birth': r'(?:Birth Date|Date of Birth|DOB)[\s:]+([^\n]+)',
        'current_institution': r'(?:Current School|Current Institution|School)[\s:]+([^\n]+)',
        'academic_average': r'(?:Average|Academic Average|Percentage)[\s:]+([^\n]+)',
        'motivation': r'(?:Motivation|Why|Reason)[\s:]+([^\n]+)',
        'parent_name': r'(?:Parent Name|Guardian Name|Parent Full Name)[\s:]+([^\n]+)',
        'parent_phone': r'(?:Parent Phone|Guardian Phone)[\s:]+([^\n]+)',
        'parent_email': r'(?:Parent Email|Guardian Email)[\s:]+([^\n@]+@[^\n]+)',
        'previous_school': r'(?:Previous School|Last School)[\s:]+([^\n]+)',
        'student_full_name': r'(?:Student Name|Learner Name|Full Name)[\s:]+([^\n]+)',
        'student_email': r'(?:Student Email|Learner Email)[\s:]+([^\n@]+@[^\n]+)',
        'student_phone': r'(?:Student Phone|Learner Phone)[\s:]+([^\n]+)',
        'program_of_interest': r'(?:Program|Course|Program of Interest)[\s:]+([^\n]+)',
        'program_code': r'(?:Program Code|Course Code)[\s:]+([^\n]+)',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            data[key] = match.group(1).strip()
    
    return data


@login_required
def apply_selection(request):
    """Step 1: Select what you want to apply for (Bursary, University, or School)"""
    context = {
        'bursaries': Bursary.objects.filter(is_active=True, closing_date__gte=timezone.now().date()).order_by('-created_at')[:20],
        'universities': University.objects.filter(is_active=True).order_by('name')[:20],
        'schools': School.objects.filter(is_active=True).order_by('name')[:20],
        'has_applications': BursaryApplication.objects.filter(applicant=request.user).exists() or 
                           UniversityApplication.objects.filter(applicant=request.user).exists() or
                           SchoolApplication.objects.filter(applicant=request.user).exists()
    }
    return render(request, 'education/apply_selection.html', context)


@login_required
def apply_bursary(request, bursary_id=None):
    """Complete bursary application form with selection"""
    bursary = None
    if bursary_id:
        bursary = get_object_or_404(Bursary, id=bursary_id, is_active=True)
    
    existing_app = None
    if bursary:
        existing_app = BursaryApplication.objects.filter(
            applicant=request.user,
            bursary=bursary
        ).first()
    
    available_bursaries = Bursary.objects.filter(
        is_active=True, 
        closing_date__gte=timezone.now().date()
    ).order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        data = request.POST.copy()
        
        if data.get('message_input'):
            parsed = parse_application_message(data.get('message_input'))
            for key, value in parsed.items():
                if value:
                    data[key] = value
        
        selected_bursary_id = data.get('selected_bursary')
        if selected_bursary_id:
            try:
                bursary = Bursary.objects.get(id=selected_bursary_id, is_active=True)
            except Bursary.DoesNotExist:
                messages.error(request, 'Selected bursary not found')
                bursary = None
        
        if not bursary:
            messages.error(request, 'Please select a bursary to apply for')
            return redirect('education_apply_bursary')
        
        application_data = {
            'full_name': data.get('full_name', '').strip() or data.get('full_names', '').strip(),
            'email': data.get('email', '').strip(),
            'phone': data.get('phone', '').strip(),
            'id_number': data.get('id_number', '').strip(),
            'date_of_birth': data.get('date_of_birth', '') or data.get('birth_date', ''),
            'current_institution': data.get('current_institution', '').strip(),
            'academic_average': data.get('academic_average', '').strip(),
            'motivation': data.get('motivation', '').strip(),
            'current_institution_type': data.get('current_institution_type', 'other'),
        }
        
        files = {}
        for field in ['cv', 'academic_transcript', 'id_document', 'other_documents']:
            if request.FILES.get(field):
                files[field] = request.FILES[field]
        
        try:
            if existing_app:
                for key, value in application_data.items():
                    setattr(existing_app, key, value)
                existing_app.updated_at = timezone.now()
                existing_app.save()
                app = existing_app
            else:
                app_data = {
                    'applicant': request.user,
                    'bursary': bursary,
                    'full_name': application_data['full_name'],
                    'email': application_data['email'],
                    'phone': application_data['phone'],
                    'id_number': application_data['id_number'],
                    'date_of_birth': application_data['date_of_birth'],
                    'current_institution': application_data['current_institution'],
                    'academic_average': application_data['academic_average'],
                    'motivation': application_data['motivation'],
                    'current_institution_type': application_data['current_institution_type'],
                    'status': 'draft',
                }
                app = BursaryApplication.objects.create(**app_data)
            
            for field, file_obj in files.items():
                if hasattr(app, field):
                    setattr(app, field, file_obj)
            app.save()
            
            if action == 'submit':
                app.submit()
                messages.success(request, f'🎉 Your application for {bursary.title} has been submitted successfully!')
                return redirect('education_application_success', app_id=app.id)
            else:
                messages.success(request, '✅ Your application has been saved as draft')
                return redirect('education_my_applications')
                
        except Exception as e:
            messages.error(request, f'Error saving application: {str(e)}')
            return redirect('education_apply_bursary_with_id', bursary_id=bursary.id)
    
    draft_data = {}
    if existing_app and existing_app.status == 'draft':
        draft_data = {
            'full_name': existing_app.full_name,
            'email': existing_app.email,
            'phone': existing_app.phone,
            'id_number': existing_app.id_number,
            'date_of_birth': existing_app.date_of_birth.strftime('%Y-%m-%d') if existing_app.date_of_birth else '',
            'current_institution': existing_app.current_institution,
            'academic_average': existing_app.academic_average,
            'motivation': existing_app.motivation,
            'current_institution_type': existing_app.current_institution_type,
        }
    
    context = {
        'bursary': bursary,
        'available_bursaries': available_bursaries,
        'application': existing_app,
        'draft_data': draft_data,
        'has_application': bool(existing_app),
        'can_submit': existing_app.status == 'draft' if existing_app else True,
        'academic_years': range(2020, 2027),
        'provinces': ['Gauteng', 'Western Cape', 'KwaZulu-Natal', 'Eastern Cape', 'Free State', 'Limpopo', 'Mpumalanga', 'North West', 'Northern Cape'],
        'status_choices': BursaryApplication.STATUS_CHOICES,
    }
    
    return render(request, 'education/apply_bursary.html', context)


@login_required
def apply_university(request, university_id=None):
    """Complete university application form with selection"""
    university = None
    if university_id:
        university = get_object_or_404(University, id=university_id, is_active=True)
    
    existing_app = None
    if university:
        existing_app = UniversityApplication.objects.filter(
            applicant=request.user,
            university=university
        ).first()
    
    available_universities = University.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        data = request.POST.copy()
        
        if data.get('message_input'):
            parsed = parse_application_message(data.get('message_input'))
            for key, value in parsed.items():
                if value:
                    data[key] = value
        
        selected_university_id = data.get('selected_university')
        if selected_university_id:
            try:
                university = University.objects.get(id=selected_university_id, is_active=True)
            except University.DoesNotExist:
                messages.error(request, 'Selected university not found')
                university = None
        
        if not university:
            messages.error(request, 'Please select a university to apply for')
            return redirect('education_apply_university')
        
        application_data = {
            'full_name': data.get('full_name', '').strip() or data.get('full_names', '').strip(),
            'email': data.get('email', '').strip(),
            'phone': data.get('phone', '').strip(),
            'id_number': data.get('id_number', '').strip(),
            'date_of_birth': data.get('date_of_birth', '') or data.get('birth_date', ''),
            'academic_average': data.get('academic_average', '').strip(),
            'motivation': data.get('motivation', '').strip(),
            'program_of_interest': data.get('program_of_interest', '').strip(),
            'program_code': data.get('program_code', '').strip(),
        }
        
        files = {}
        for field in ['cv', 'academic_transcript', 'id_document']:
            if request.FILES.get(field):
                files[field] = request.FILES[field]
        
        try:
            if existing_app:
                for key, value in application_data.items():
                    setattr(existing_app, key, value)
                existing_app.updated_at = timezone.now()
                existing_app.save()
                app = existing_app
            else:
                app_data = {
                    'applicant': request.user,
                    'university': university,
                    'full_name': application_data['full_name'],
                    'email': application_data['email'],
                    'phone': application_data['phone'],
                    'id_number': application_data['id_number'],
                    'date_of_birth': application_data['date_of_birth'],
                    'academic_average': application_data['academic_average'],
                    'motivation': application_data['motivation'],
                    'program_of_interest': application_data['program_of_interest'],
                    'program_code': application_data['program_code'],
                    'status': 'draft',
                }
                app = UniversityApplication.objects.create(**app_data)
            
            for field, file_obj in files.items():
                if hasattr(app, field):
                    setattr(app, field, file_obj)
            app.save()
            
            if action == 'submit':
                app.submit()
                messages.success(request, f'🎉 Your application for {university.name} has been submitted successfully!')
                return redirect('education_application_success', app_id=app.id)
            else:
                messages.success(request, '✅ Your application has been saved as draft')
                return redirect('education_my_applications')
                
        except Exception as e:
            messages.error(request, f'Error saving application: {str(e)}')
            return redirect('education_apply_university', university_id=university.id)
    
    draft_data = {}
    if existing_app and existing_app.status == 'draft':
        draft_data = {
            'full_name': existing_app.full_name,
            'email': existing_app.email,
            'phone': existing_app.phone,
            'id_number': existing_app.id_number,
            'date_of_birth': existing_app.date_of_birth.strftime('%Y-%m-%d') if existing_app.date_of_birth else '',
            'academic_average': existing_app.academic_average,
            'motivation': existing_app.motivation,
            'program_of_interest': existing_app.program_of_interest,
            'program_code': existing_app.program_code,
        }
    
    context = {
        'university': university,
        'available_universities': available_universities,
        'application': existing_app,
        'draft_data': draft_data,
        'has_application': bool(existing_app),
        'can_submit': existing_app.status == 'draft' if existing_app else True,
        'academic_years': range(2020, 2027),
        'provinces': ['Gauteng', 'Western Cape', 'KwaZulu-Natal', 'Eastern Cape', 'Free State', 'Limpopo', 'Mpumalanga', 'North West', 'Northern Cape'],
        'status_choices': UniversityApplication.STATUS_CHOICES,
    }
    
    return render(request, 'education/apply_university.html', context)


@login_required
def apply_school(request, school_id=None):
    """Complete school application form with selection"""
    school = None
    if school_id:
        school = get_object_or_404(School, id=school_id, is_active=True)
    
    existing_app = None
    if school:
        existing_app = SchoolApplication.objects.filter(
            applicant=request.user,
            school=school
        ).first()
    
    available_schools = School.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        data = request.POST.copy()
        
        if data.get('message_input'):
            parsed = parse_application_message(data.get('message_input'))
            for key, value in parsed.items():
                if value:
                    data[key] = value
        
        selected_school_id = data.get('selected_school')
        if selected_school_id:
            try:
                school = School.objects.get(id=selected_school_id, is_active=True)
            except School.DoesNotExist:
                messages.error(request, 'Selected school not found')
                school = None
        
        if not school:
            messages.error(request, 'Please select a school to apply for')
            return redirect('education_apply_school')
        
        application_data = {
            'student_full_name': data.get('student_full_name', '').strip() or data.get('full_name', '').strip(),
            'student_email': data.get('student_email', '').strip() or data.get('email', '').strip(),
            'student_phone': data.get('student_phone', '').strip() or data.get('phone', '').strip(),
            'id_number': data.get('id_number', '').strip(),
            'date_of_birth': data.get('date_of_birth', '') or data.get('birth_date', ''),
            'parent_name': data.get('parent_name', '').strip() or data.get('guardian_full_names', '').strip(),
            'parent_phone': data.get('parent_phone', '').strip() or data.get('guardian_phone', '').strip(),
            'parent_email': data.get('parent_email', '').strip() or data.get('guardian_email', '').strip(),
            'previous_school': data.get('previous_school', '').strip(),
            'motivation': data.get('motivation', '').strip(),
            'additional_notes': data.get('additional_notes', '').strip(),
        }
        
        files = {}
        for field in ['birth_certificate', 'report_card']:
            if request.FILES.get(field):
                files[field] = request.FILES[field]
        
        try:
            if existing_app:
                for key, value in application_data.items():
                    setattr(existing_app, key, value)
                existing_app.updated_at = timezone.now()
                existing_app.save()
                app = existing_app
            else:
                app_data = {
                    'applicant': request.user,
                    'school': school,
                    'student_full_name': application_data['student_full_name'],
                    'student_email': application_data['student_email'],
                    'student_phone': application_data['student_phone'],
                    'id_number': application_data['id_number'],
                    'date_of_birth': application_data['date_of_birth'],
                    'parent_name': application_data['parent_name'],
                    'parent_phone': application_data['parent_phone'],
                    'parent_email': application_data['parent_email'],
                    'previous_school': application_data['previous_school'],
                    'motivation': application_data['motivation'],
                    'status': 'draft',
                }
                app = SchoolApplication.objects.create(**app_data)
            
            for field, file_obj in files.items():
                if hasattr(app, field):
                    setattr(app, field, file_obj)
            app.save()
            
            if action == 'submit':
                app.submit()
                messages.success(request, f'🎉 Your application for {school.name} has been submitted successfully!')
                return redirect('education_application_success', app_id=app.id)
            else:
                messages.success(request, '✅ Your application has been saved as draft')
                return redirect('education_my_applications')
                
        except Exception as e:
            messages.error(request, f'Error saving application: {str(e)}')
            return redirect('education_apply_school', school_id=school.id)
    
    draft_data = {}
    if existing_app and existing_app.status == 'draft':
        draft_data = {
            'student_full_name': existing_app.student_full_name,
            'student_email': existing_app.student_email,
            'student_phone': existing_app.student_phone,
            'id_number': existing_app.id_number,
            'date_of_birth': existing_app.date_of_birth.strftime('%Y-%m-%d') if existing_app.date_of_birth else '',
            'parent_name': existing_app.parent_name,
            'parent_phone': existing_app.parent_phone,
            'parent_email': existing_app.parent_email,
            'previous_school': existing_app.previous_school,
            'motivation': existing_app.motivation,
        }
    
    context = {
        'school': school,
        'available_schools': available_schools,
        'application': existing_app,
        'draft_data': draft_data,
        'has_application': bool(existing_app),
        'can_submit': existing_app.status == 'draft' if existing_app else True,
        'status_choices': SchoolApplication.STATUS_CHOICES,
    }
    
    return render(request, 'education/apply_school.html', context)



@login_required
def bursary_application_detail(request, pk):
    application = get_object_or_404(BursaryApplication, id=pk, applicant=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in dict(BursaryApplication.STATUS_CHOICES):
                application.status = new_status
                application.save()
                messages.success(request, f'Application status updated to {application.get_status_display()}')
                return redirect('education_bursary_application_detail', pk=application.id)
        
        elif action == 'withdraw':
            application.status = 'withdrawn'
            application.save()
            messages.success(request, 'Application has been withdrawn')
            return redirect('education_bursary_application_detail', pk=application.id)
        
        elif action == 'submit':
            if application.status == 'draft':
                application.submit()
                messages.success(request, 'Application submitted successfully!')
                return redirect('education_bursary_application_detail', pk=application.id)
    
    context = {
        'application': application,
        'type': 'bursary',
        'type_display': 'Bursary',
        'status_choices': BursaryApplication.STATUS_CHOICES,
    }
    
    return render(request, 'education/application_detail.html', context)


@login_required
def university_application_detail(request, pk):
    application = get_object_or_404(UniversityApplication, id=pk, applicant=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in dict(UniversityApplication.STATUS_CHOICES):
                application.status = new_status
                application.save()
                messages.success(request, f'Application status updated to {application.get_status_display()}')
                return redirect('education_university_application_detail', pk=application.id)
        
        elif action == 'withdraw':
            application.status = 'withdrawn'
            application.save()
            messages.success(request, 'Application has been withdrawn')
            return redirect('education_university_application_detail', pk=application.id)
        
        elif action == 'submit':
            if application.status == 'draft':
                application.submit()
                messages.success(request, 'Application submitted successfully!')
                return redirect('education_university_application_detail', pk=application.id)
    
    context = {
        'application': application,
        'type': 'university',
        'type_display': 'University',
        'status_choices': UniversityApplication.STATUS_CHOICES,
    }
    
    return render(request, 'education/application_detail.html', context)


@login_required
def school_application_detail(request, pk):
    application = get_object_or_404(SchoolApplication, id=pk, applicant=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in dict(SchoolApplication.STATUS_CHOICES):
                application.status = new_status
                application.save()
                messages.success(request, f'Application status updated to {application.get_status_display()}')
                return redirect('education_school_application_detail', pk=application.id)
        
        elif action == 'withdraw':
            application.status = 'withdrawn'
            application.save()
            messages.success(request, 'Application has been withdrawn')
            return redirect('education_school_application_detail', pk=application.id)
        
        elif action == 'submit':
            if application.status == 'draft':
                application.submit()
                messages.success(request, 'Application submitted successfully!')
                return redirect('education_school_application_detail', pk=application.id)
    
    context = {
        'application': application,
        'type': 'school',
        'type_display': 'School',
        'status_choices': SchoolApplication.STATUS_CHOICES,
    }
    
    return render(request, 'education/application_detail.html', context)


@login_required
def application_success(request, app_id):
    app = get_object_or_404(BursaryApplication, id=app_id, applicant=request.user)
    
    context = {
        'application': app,
        'type': 'bursary',
    }
    
    return render(request, 'education/application_success.html', context)


# ============================================
# TEMPLATE FILTERS
# ============================================

@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return None
    return dictionary.get(key, key)


# education/views.py - ADD THESE 4 FUNCTIONS at the end of the file

# ============================================================
# LISTING VIEWS - ADD THESE FUNCTIONS
# ============================================================

def bursary_list(request):
    """List all bursaries with filters"""
    bursaries = Bursary.objects.filter(is_active=True).order_by('-created_at')
    
    # Filter by level
    level = request.GET.get('level')
    if level:
        bursaries = bursaries.filter(level=level)
    
    # Filter by field of study
    field = request.GET.get('field')
    if field:
        bursaries = bursaries.filter(field_of_study__icontains=field)
    
    # Search
    search = request.GET.get('search')
    if search:
        bursaries = bursaries.filter(
            Q(title__icontains=search) | 
            Q(provider__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(bursaries, 12)
    page = request.GET.get('page', 1)
    bursaries_page = paginator.get_page(page)
    
    context = {
        'bursaries': bursaries_page,
        'page_title': 'Bursaries',
        'page_description': 'Find bursaries and scholarships to fund your education',
        'active_page': 'bursaries',
        'levels': Bursary.LEVEL_CHOICES,
    }
    return render(request, 'education/bursary_list.html', context)


def school_list(request):
    """List all schools with filters"""
    schools = School.objects.filter(is_active=True).order_by('name')
    
    # Filter by province
    province = request.GET.get('province')
    if province:
        schools = schools.filter(province=province)
    
    # Filter by school type
    school_type = request.GET.get('school_type')
    if school_type:
        schools = schools.filter(school_type=school_type)
    
    # Search
    search = request.GET.get('search')
    if search:
        schools = schools.filter(
            Q(name__icontains=search) | 
            Q(city__icontains=search) |
            Q(province__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(schools, 12)
    page = request.GET.get('page', 1)
    schools_page = paginator.get_page(page)
    
    context = {
        'schools': schools_page,
        'page_title': 'Schools',
        'page_description': 'Find schools and educational institutions',
        'active_page': 'schools',
        'provinces': School.objects.values_list('province', flat=True).distinct(),
        'school_types': School.SCHOOL_TYPE_CHOICES,
    }
    return render(request, 'education/school_list.html', context)


def university_list(request):
    """List all universities with filters"""
    universities = University.objects.filter(is_active=True).order_by('name')
    
    # Filter by province
    province = request.GET.get('province')
    if province:
        universities = universities.filter(province=province)
    
    # Search
    search = request.GET.get('search')
    if search:
        universities = universities.filter(
            Q(name__icontains=search) | 
            Q(city__icontains=search) |
            Q(province__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(universities, 12)
    page = request.GET.get('page', 1)
    universities_page = paginator.get_page(page)
    
    context = {
        'universities': universities_page,
        'page_title': 'Universities',
        'page_description': 'Find universities and higher education institutions',
        'active_page': 'universities',
        'provinces': University.objects.values_list('province', flat=True).distinct(),
    }
    return render(request, 'education/university_list.html', context)


def paper_list(request):
    """List all question papers with filters"""
    papers = QuestionPaper.objects.filter(is_public=True, is_active=True).order_by('-year', '-created_at')
    
    # Filter by grade
    grade_id = request.GET.get('grade')
    if grade_id:
        papers = papers.filter(grade_id=grade_id)
    
    # Filter by subject
    subject_id = request.GET.get('subject')
    if subject_id:
        papers = papers.filter(subject_id=subject_id)
    
    # Filter by year
    year = request.GET.get('year')
    if year:
        papers = papers.filter(year=year)
    
    # Search
    search = request.GET.get('search')
    if search:
        papers = papers.filter(
            Q(title__icontains=search) | 
            Q(grade__name__icontains=search) |
            Q(subject__name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(papers, 12)
    page = request.GET.get('page', 1)
    papers_page = paginator.get_page(page)
    
    context = {
        'papers': papers_page,
        'page_title': 'Question Papers',
        'page_description': 'Download past question papers and study materials',
        'active_page': 'papers',
        'grades': Grade.objects.filter(is_active=True).order_by('order'),
        'subjects': Subject.objects.filter(is_active=True).order_by('name'),
        'years': QuestionPaper.objects.values_list('year', flat=True).distinct().order_by('-year'),
    }
    return render(request, 'education/paper_list.html', context)



@login_required
def business_applications(request):
    """
    Business/Admin dashboard to view, search, and filter ALL applications.
    """
    # Permission check
    if not (request.user.is_superuser or getattr(request.user, 'user_type', '') == 'admin'):
        messages.error(request, "You do not have permission to access this page.")
        return redirect('education_home')

    # --- 1. Get filter parameters from request ---
    search_query = request.GET.get('q', '').strip()
    app_type_filter = request.GET.get('type', '')  # bursary, university, school
    status_filter = request.GET.get('status', '')
    field_filter = request.GET.get('field', '')    # Field of study (Bursary) or Program (University)
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    # --- 2. Base QuerySets (select related for performance) ---
    bursary_qs = BursaryApplication.objects.select_related('bursary', 'applicant')
    university_qs = UniversityApplication.objects.select_related('university', 'applicant')
    school_qs = SchoolApplication.objects.select_related('school', 'applicant')

    # --- 3. Apply Filters (using Q for advanced search) ---
    if search_query:
        # Search across applicant names, emails, motivation, institution names, and career-specific fields
        bursary_qs = bursary_qs.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(motivation__icontains=search_query) |
            Q(current_institution__icontains=search_query) |
            Q(bursary__title__icontains=search_query) |
            Q(bursary__provider__icontains=search_query) |
            Q(bursary__field_of_study__icontains=search_query)
        )
        university_qs = university_qs.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(motivation__icontains=search_query) |
            Q(program_of_interest__icontains=search_query) |
            Q(university__name__icontains=search_query) |
            Q(university__city__icontains=search_query)
        )
        school_qs = school_qs.filter(
            Q(student_full_name__icontains=search_query) |
            Q(student_email__icontains=search_query) |
            Q(motivation__icontains=search_query) |
            Q(previous_school__icontains=search_query) |
            Q(school__name__icontains=search_query) |
            Q(school__city__icontains=search_query)
        )

    # Filter by status
    if status_filter:
        bursary_qs = bursary_qs.filter(status=status_filter)
        university_qs = university_qs.filter(status=status_filter)
        school_qs = school_qs.filter(status=status_filter)

    # Filter by specific career/field (Bursary field of study)
    if field_filter:
        bursary_qs = bursary_qs.filter(bursary__field_of_study__icontains=field_filter)
        university_qs = university_qs.filter(program_of_interest__icontains=field_filter)
        # For schools, we search the motivation or school name for that keyword (since they don't have a dedicated program field)
        school_qs = school_qs.filter(
            Q(motivation__icontains=field_filter) |
            Q(school__name__icontains=field_filter)
        )

    # Filter by date range (submitted_at)
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            bursary_qs = bursary_qs.filter(submitted_at__gte=from_dt)
            university_qs = university_qs.filter(submitted_at__gte=from_dt)
            school_qs = school_qs.filter(submitted_at__gte=from_dt)
        except ValueError:
            pass
    if to_date:
        try:
            to_dt = datetime.strptime(to_date, '%Y-%m-%d')
            bursary_qs = bursary_qs.filter(submitted_at__lte=to_dt)
            university_qs = university_qs.filter(submitted_at__lte=to_dt)
            school_qs = school_qs.filter(submitted_at__lte=to_dt)
        except ValueError:
            pass

    # Apply Type filter (if specific type is chosen)
    if app_type_filter == 'bursary':
        university_qs = UniversityApplication.objects.none()
        school_qs = SchoolApplication.objects.none()
    elif app_type_filter == 'university':
        bursary_qs = BursaryApplication.objects.none()
        school_qs = SchoolApplication.objects.none()
    elif app_type_filter == 'school':
        bursary_qs = BursaryApplication.objects.none()
        university_qs = UniversityApplication.objects.none()

    # --- 4. Convert to unified list of dicts ---
    all_apps = []

    for app in bursary_qs:
        all_apps.append({
            'id': app.id,
            'type': 'bursary',
            'type_display': 'Bursary',
            'institution_name': app.bursary.title if app.bursary else 'N/A',
            'applicant_name': app.full_name or app.applicant.get_full_name() or app.applicant.username,
            'applicant_email': app.email or app.applicant.email,
            'status': app.status,
            'status_display': app.get_status_display(),
            'submitted_at': app.submitted_at or app.created_at,
            'motivation_snippet': app.motivation[:150] + '...' if app.motivation and len(app.motivation) > 150 else app.motivation,
            'url': reverse('education_business_application_detail', kwargs={'app_type': 'bursary', 'pk': app.id})
        })

    for app in university_qs:
        all_apps.append({
            'id': app.id,
            'type': 'university',
            'type_display': 'University',
            'institution_name': app.university.name if app.university else 'N/A',
            'applicant_name': app.full_name or app.applicant.get_full_name() or app.applicant.username,
            'applicant_email': app.email or app.applicant.email,
            'status': app.status,
            'status_display': app.get_status_display(),
            'submitted_at': app.submitted_at or app.created_at,
            'motivation_snippet': app.motivation[:150] + '...' if app.motivation and len(app.motivation) > 150 else app.motivation,
            'url': reverse('education_business_application_detail', kwargs={'app_type': 'university', 'pk': app.id})
        })

    for app in school_qs:
        all_apps.append({
            'id': app.id,
            'type': 'school',
            'type_display': 'School',
            'institution_name': app.school.name if app.school else 'N/A',
            'applicant_name': app.student_full_name or app.applicant.get_full_name() or app.applicant.username,
            'applicant_email': app.student_email or app.applicant.email,
            'status': app.status,
            'status_display': app.get_status_display(),
            'submitted_at': app.submitted_at or app.created_at,
            'motivation_snippet': app.motivation[:150] + '...' if app.motivation and len(app.motivation) > 150 else app.motivation,
            'url': reverse('education_business_application_detail', kwargs={'app_type': 'school', 'pk': app.id})
        })

    # Sort by submitted_at (newest first)
    all_apps.sort(key=lambda x: x['submitted_at'], reverse=True)

    # Pagination
    paginator = Paginator(all_apps, 20)
    page = request.GET.get('page', 1)
    apps_page = paginator.get_page(page)

    # --- 5. Get distinct values for filter dropdown buttons ---
    # Get unique field_of_study from Bursaries (for career matching buttons)
    available_fields = Bursary.objects.filter(is_active=True).values_list('field_of_study', flat=True).distinct()
    # Get unique programs from UniversityApplications
    available_programs = UniversityApplication.objects.exclude(program_of_interest='').values_list('program_of_interest', flat=True).distinct()

    context = {
        'applications': apps_page,
        'total_count': len(all_apps),
        'search_query': search_query,
        'selected_type': app_type_filter,
        'selected_status': status_filter,
        'selected_field': field_filter,
        'from_date': from_date,
        'to_date': to_date,

        # Filter options for buttons/dropdowns
        'status_choices': [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('under_review', 'Under Review'),
            ('shortlisted', 'Shortlisted'),
            ('interview', 'Interview'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
            ('withdrawn', 'Withdrawn'),
        ],
        'app_type_choices': [
            ('', 'All Types'),
            ('bursary', 'Bursaries'),
            ('university', 'Universities'),
            ('school', 'Schools'),
        ],
        'available_fields': available_fields,  # For career matching buttons
        'available_programs': available_programs,  # For university program buttons
    }
    return render(request, 'education/business_applications.html', context)


@login_required
def business_application_detail(request, app_type, pk):
    """
    Business/admin view for a single application:
    - Display all details
    - Update status
    - Add/edit internal notes (visible to the applicant)
    """
    # Permission check
    if not (request.user.is_superuser or getattr(request.user, 'user_type', '') == 'admin'):
        messages.error(request, "You do not have permission to view this page.")
        return redirect('education_home')

    # Retrieve correct application based on type
    if app_type == 'bursary':
        app = get_object_or_404(BursaryApplication, id=pk)
        status_choices = BursaryApplication.STATUS_CHOICES
        type_display = 'Bursary Application'
        institution_name = app.bursary.title if app.bursary else 'N/A'
    elif app_type == 'university':
        app = get_object_or_404(UniversityApplication, id=pk)
        status_choices = UniversityApplication.STATUS_CHOICES
        type_display = 'University Application'
        institution_name = app.university.name if app.university else 'N/A'
    elif app_type == 'school':
        app = get_object_or_404(SchoolApplication, id=pk)
        status_choices = SchoolApplication.STATUS_CHOICES
        type_display = 'School Application'
        institution_name = app.school.name if app.school else 'N/A'
    else:
        messages.error(request, "Invalid application type.")
        return redirect('education_business_applications')

    # Handle POST requests (status update or notes save)
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in dict(status_choices):
                app.status = new_status
                app.save()
                messages.success(request, f"Status updated to {app.get_status_display()}.")
            else:
                messages.error(request, "Invalid status selected.")
            return redirect('education_business_application_detail', app_type=app_type, pk=pk)

        elif action == 'save_notes':
            notes = request.POST.get('admin_notes', '').strip()
            app.admin_notes = notes
            app.save()
            messages.success(request, "Notes saved successfully.")
            return redirect('education_business_application_detail', app_type=app_type, pk=pk)

        # You can add more actions here (e.g., send email to applicant)

    # Build context for the template
    context = {
        'application': app,
        'app_type': app_type,
        'type_display': type_display,
        'institution_name': institution_name,
        'status_choices': status_choices,
        'back_url': reverse('education_business_applications'),
        'applicant': app.applicant,
    }
    return render(request, 'education/business_application_detail.html', context)


@login_required
def my_applications(request):
    """View all education applications for the current user."""

    # ============================================================
    # 1. GET ALL APPLICATIONS
    # ============================================================

    bursary_apps = (
        BursaryApplication.objects
        .filter(applicant=request.user)
        .select_related('bursary')
        .order_by('-created_at')
    )

    university_apps = (
        UniversityApplication.objects
        .filter(applicant=request.user)
        .select_related('university')
        .order_by('-created_at')
    )

    school_apps = (
        SchoolApplication.objects
        .filter(applicant=request.user)
        .select_related('school')
        .order_by('-created_at')
    )

    all_applications = []

    # ============================================================
    # 2. BURSARY APPLICATIONS
    # ============================================================

    for app in bursary_apps:

        bursary_title = (
            app.bursary.title
            if app.bursary
            else "No Bursary"
        )

        bursary_provider = (
            app.bursary.provider
            if app.bursary
            else "N/A"
        )

        all_applications.append({
            'id': app.id,
            'type': 'bursary',
            'type_display': 'Bursary',

            'title': bursary_title,
            'institution': bursary_provider,

            'status': app.status,

            'created_at': app.created_at,
            'updated_at': app.updated_at,
            'submitted_at': getattr(app, 'submitted_at', None),

            'status_display': dict(
                BursaryApplication.STATUS_CHOICES
            ).get(
                app.status,
                app.status
            ),

            # IMPORTANT:
            # Pass the COMPLETE application object to the template.
            'application': app,

            # Documents
            'cv': getattr(app, 'cv', None),
            'academic_transcript': getattr(
                app,
                'academic_transcript',
                None
            ),
            'id_document': getattr(
                app,
                'id_document',
                None
            ),
            'other_documents': getattr(
                app,
                'other_documents',
                None
            ),

            # Applicant information
            'full_name': getattr(app, 'full_name', ''),
            'email': getattr(app, 'email', ''),
            'phone': getattr(app, 'phone', ''),
            'id_number': getattr(app, 'id_number', ''),
            'date_of_birth': getattr(
                app,
                'date_of_birth',
                None
            ),

            'current_institution': getattr(
                app,
                'current_institution',
                ''
            ),

            'current_institution_type': getattr(
                app,
                'current_institution_type',
                ''
            ),

            'academic_average': getattr(
                app,
                'academic_average',
                ''
            ),

            'motivation': getattr(
                app,
                'motivation',
                ''
            ),

            # Admin information
            'admin_notes': getattr(
                app,
                'admin_notes',
                ''
            ),

            # Detail page
            'url': reverse(
                'education_bursary_application_detail',
                args=[app.id]
            ),
        })

    # ============================================================
    # 3. UNIVERSITY APPLICATIONS
    # ============================================================

    for app in university_apps:

        university_name = (
            app.university.name
            if app.university
            else "No University"
        )

        all_applications.append({
            'id': app.id,
            'type': 'university',
            'type_display': 'University',

            'title': university_name,
            'institution': university_name,

            'status': app.status,

            'created_at': app.created_at,
            'updated_at': app.updated_at,
            'submitted_at': getattr(
                app,
                'submitted_at',
                None
            ),

            'status_display': dict(
                UniversityApplication.STATUS_CHOICES
            ).get(
                app.status,
                app.status
            ),

            'application': app,

            'url': reverse(
                'education_university_application_detail',
                args=[app.id]
            ),
        })

    # ============================================================
    # 4. SCHOOL APPLICATIONS
    # ============================================================

    for app in school_apps:

        school_name = (
            app.school.name
            if app.school
            else "No School"
        )

        all_applications.append({
            'id': app.id,
            'type': 'school',
            'type_display': 'School',

            'title': school_name,
            'institution': school_name,

            'status': app.status,

            'created_at': app.created_at,
            'updated_at': app.updated_at,
            'submitted_at': getattr(
                app,
                'submitted_at',
                None
            ),

            'status_display': dict(
                SchoolApplication.STATUS_CHOICES
            ).get(
                app.status,
                app.status
            ),

            'application': app,

            'url': reverse(
                'education_school_application_detail',
                args=[app.id]
            ),
        })

    # ============================================================
    # 5. SORT EVERYTHING TOGETHER
    # ============================================================

    all_applications.sort(
        key=lambda x: x['created_at'],
        reverse=True
    )

    # ============================================================
    # 6. PAGINATION
    # ============================================================

    paginator = Paginator(
        all_applications,
        20
    )

    page = request.GET.get(
        'page',
        1
    )

    applications_page = paginator.get_page(page)

    # ============================================================
    # 7. STATUS COUNTS
    # ============================================================

    status_counts = {}

    for app in all_applications:

        status = app['status']

        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )

    # ============================================================
    # 8. STATUS CHOICES
    # ============================================================

    status_choices = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview Scheduled'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]

    # ============================================================
    # 9. CONTEXT
    # ============================================================

    context = {
        'applications': applications_page,

        'total_count': len(
            all_applications
        ),

        'status_counts': status_counts,

        'status_choices': status_choices,

        # Useful if your template wants to know
        # how many of each type exist.
        'bursary_count': len(bursary_apps),
        'university_count': len(university_apps),
        'school_count': len(school_apps),

        # User
        'current_user': request.user,

        # If your template checks this.
        'is_admin': (
            request.user.is_staff
            or request.user.is_superuser
        ),
    }

    return render(
        request,
        'education/my_applications.html',
        context
    )

    

@login_required
def apply_bulk_bursary(request):
    """
    Apply to multiple bursaries using the user's latest application
    as the source of prefilled information.
    """

    user = request.user

    # ============================================================
    # 1. GET LATEST APPLICATION DATA
    # ============================================================

    latest_app = (
        BursaryApplication.objects
        .filter(applicant=user)
        .order_by('-updated_at', '-created_at')
        .first()
    )

    draft_data = {
        'full_name': '',
        'email': '',
        'phone': '',
        'id_number': '',
        'date_of_birth': '',
        'current_institution': '',
        'academic_average': '',
        'motivation': '',
        'current_institution_type': 'other',
    }

    if latest_app:
        draft_data.update({
            'full_name': latest_app.full_name or '',
            'email': latest_app.email or '',
            'phone': latest_app.phone or '',
            'id_number': latest_app.id_number or '',
            'date_of_birth': (
                latest_app.date_of_birth.strftime('%Y-%m-%d')
                if latest_app.date_of_birth
                else ''
            ),
            'current_institution': latest_app.current_institution or '',
            'academic_average': latest_app.academic_average or '',
            'motivation': latest_app.motivation or '',
            'current_institution_type': (
                latest_app.current_institution_type or 'other'
            ),
        })

    else:
        # Fallback to user profile
        draft_data['full_name'] = user.get_full_name() or ''
        draft_data['email'] = user.email or ''
        draft_data['phone'] = getattr(user, 'phone', '') or ''
        draft_data['id_number'] = getattr(user, 'id_number', '') or ''

        if getattr(user, 'date_of_birth', None):
            try:
                draft_data['date_of_birth'] = (
                    user.date_of_birth.strftime('%Y-%m-%d')
                )
            except (AttributeError, ValueError, TypeError):
                pass

    # ============================================================
    # 2. FIND BURSARIES ALREADY APPLIED FOR
    # ============================================================

    applied_ids = set(
        BursaryApplication.objects
        .filter(
            applicant=user,
            bursary__isnull=False
        )
        .values_list('bursary_id', flat=True)
        .distinct()
    )

    # ============================================================
    # 3. AVAILABLE BURSARIES
    # ============================================================

    today = timezone.now().date()

    available_bursaries = (
        Bursary.objects
        .filter(
            is_active=True,
            closing_date__gte=today
        )
        .exclude(id__in=applied_ids)
        .order_by('closing_date', '-created_at')
    )

    # ============================================================
    # 4. DYNAMIC ACADEMIC YEARS
    # ============================================================

    from datetime import datetime

    paper_years = list(
        QuestionPaper.objects
        .filter(year__isnull=False)
        .values_list('year', flat=True)
        .distinct()
        .order_by('-year')
    )

    current_year = datetime.now().year

    if paper_years:
        min_year = min(paper_years)
        max_year = max(paper_years)

        if max_year < current_year:
            max_year = current_year + 1

        if min_year > current_year - 10:
            min_year = current_year - 10

        academic_years = range(min_year, max_year + 1)

    else:
        academic_years = range(
            current_year - 10,
            current_year + 2
        )

    # ============================================================
    # 5. PROVINCES
    # ============================================================

    uni_provinces = (
        University.objects
        .filter(is_active=True)
        .exclude(province='')
        .values_list('province', flat=True)
        .distinct()
    )

    school_provinces = (
        School.objects
        .filter(is_active=True)
        .exclude(province='')
        .values_list('province', flat=True)
        .distinct()
    )

    provinces = sorted(
        set(uni_provinces).union(set(school_provinces))
    )

    if not provinces:
        provinces = [
            'Gauteng',
            'Western Cape',
            'KwaZulu-Natal',
            'Eastern Cape',
            'Free State',
            'Limpopo',
            'Mpumalanga',
            'North West',
            'Northern Cape',
        ]

    # ============================================================
    # 6. POST
    # ============================================================

    if request.method == 'POST':

        # --------------------------------------------------------
        # Selected bursaries
        # --------------------------------------------------------

        selected_ids = request.POST.getlist('selected_bursaries')

        # Remove duplicates and empty values
        selected_ids = list(
            dict.fromkeys(
                str(pk).strip()
                for pk in selected_ids
                if str(pk).strip()
            )
        )

        if not selected_ids:
            messages.error(
                request,
                'Please select at least one bursary.'
            )

            return render(
                request,
                'education/apply_bulk_bursary.html',
                {
                    'bursaries': available_bursaries,
                    'draft_data': draft_data,
                    'academic_years': academic_years,
                    'provinces': provinces,
                    'selected_ids': [],
                }
            )

        # --------------------------------------------------------
        # Validate selected bursaries AGAIN from database
        # --------------------------------------------------------

        bursaries = list(
            Bursary.objects
            .filter(
                id__in=selected_ids,
                is_active=True,
                closing_date__gte=today,
            )
            .exclude(id__in=applied_ids)
            .order_by('closing_date', '-created_at')
        )

        valid_ids = {str(b.id) for b in bursaries}
        invalid_ids = [
            pk for pk in selected_ids
            if pk not in valid_ids
        ]

        if invalid_ids:
            messages.error(
                request,
                'One or more selected bursaries are no longer available. '
                'Please refresh the page and try again.'
            )

            return redirect('education_apply_bulk_bursary')

        # --------------------------------------------------------
        # Copy POST data
        # --------------------------------------------------------

        data = request.POST.copy()

        # --------------------------------------------------------
        # Optional smart application message
        # --------------------------------------------------------

        if data.get('message_input'):
            parsed = parse_application_message(
                data.get('message_input')
            )

            for key, value in parsed.items():
                if value:
                    data[key] = value

        # --------------------------------------------------------
        # Application data
        # --------------------------------------------------------

        app_data = {
            'full_name': data.get('full_name', '').strip(),
            'email': data.get('email', '').strip(),
            'phone': data.get('phone', '').strip(),
            'id_number': data.get('id_number', '').strip(),
            'date_of_birth': data.get('date_of_birth', ''),
            'current_institution': data.get(
                'current_institution',
                ''
            ).strip(),
            'academic_average': data.get(
                'academic_average',
                ''
            ).strip(),
            'motivation': data.get(
                'motivation',
                ''
            ).strip(),
            'current_institution_type': data.get(
                'current_institution_type',
                'other'
            ),
        }

        # --------------------------------------------------------
        # Required fields
        # --------------------------------------------------------

        required_fields = {
            'full_name': 'full name',
            'email': 'email',
            'phone': 'phone',
            'date_of_birth': 'date of birth',
        }

        missing_fields = []

        for field, label in required_fields.items():
            if not app_data.get(field):
                missing_fields.append(label)

        if missing_fields:

            messages.error(
                request,
                'Please complete: ' +
                ', '.join(missing_fields) +
                '.'
            )

            return render(
                request,
                'education/apply_bulk_bursary.html',
                {
                    'bursaries': available_bursaries,
                    'draft_data': app_data,
                    'academic_years': academic_years,
                    'provinces': provinces,
                    'selected_ids': selected_ids,
                }
            )

        # --------------------------------------------------------
        # Files
        # --------------------------------------------------------

        files = {}

        for field in [
            'cv',
            'academic_transcript',
            'id_document',
            'other_documents'
        ]:
            uploaded_file = request.FILES.get(field)

            if uploaded_file:
                files[field] = uploaded_file

        # ========================================================
        # 7. CREATE APPLICATIONS
        # ========================================================

        created_apps = []
        errors = []

        for bursary in bursaries:

            try:

                # Extra duplicate protection
                already_exists = (
                    BursaryApplication.objects
                    .filter(
                        applicant=user,
                        bursary=bursary
                    )
                    .exists()
                )

                if already_exists:
                    errors.append(
                        f'{bursary.title}: already applied'
                    )
                    continue

                # Create application
                app = BursaryApplication.objects.create(
                    applicant=user,
                    bursary=bursary,
                    **app_data
                )

                # Attach uploaded documents
                for field, file_obj in files.items():

                    if hasattr(app, field):
                        setattr(
                            app,
                            field,
                            file_obj
                        )

                app.save()

                created_apps.append(app)

            except Exception as e:

                errors.append(
                    f'{bursary.title}: {str(e)}'
                )

        # ========================================================
        # 8. SUBMIT OR SAVE
        # ========================================================

        action = request.POST.get('action', 'save')

        if created_apps:

            if action == 'submit':

                submitted_count = 0

                for app in created_apps:

                    try:
                        if app.status == 'draft':
                            app.submit()

                        submitted_count += 1

                    except Exception as e:
                        errors.append(
                            f'{app.bursary.title}: '
                            f'could not submit ({str(e)})'
                        )

                if errors:

                    messages.warning(
                        request,
                        f'{submitted_count} applications submitted, '
                        f'but some applications had problems.'
                    )

                else:

                    messages.success(
                        request,
                        f'🎉 Successfully submitted '
                        f'{submitted_count} bursary applications!'
                    )

            else:

                messages.success(
                    request,
                    f'✅ {len(created_apps)} bursary applications '
                    f'saved as drafts.'
                )

            return redirect('education_my_applications')

        # ========================================================
        # 9. NOTHING CREATED
        # ========================================================

        if errors:
            messages.error(
                request,
                'No applications were created: ' +
                ' | '.join(errors)
            )
        else:
            messages.error(
                request,
                'No applications were created.'
            )

        return redirect('education_apply_bulk_bursary')

    # ============================================================
    # GET
    # ============================================================

    context = {
        'bursaries': available_bursaries,
        'draft_data': draft_data,
        'academic_years': academic_years,
        'provinces': provinces,
        'selected_ids': [],
    }

    return render(
        request,
        'education/apply_bulk_bursary.html',
        context
    )