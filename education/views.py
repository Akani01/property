from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib.auth import get_user_model
import pandas as pd
from django.shortcuts import get_object_or_404, render, redirect
import os
from django import template

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
        return Response({'success': False, 'error': 'search query required'})


class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.filter(is_active=True)
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    
    @action(detail=False, methods=['post'])
    def upload_excel(self, request):
        """Upload Excel file with school data"""
        if not request.user.is_superuser and not request.user.user_type == 'admin':
            return Response({'success': False, 'error': 'Admin access required'}, status=403)
        
        file = request.FILES.get('file')
        if not file:
            return Response({'success': False, 'error': 'No file uploaded'})
        
        try:
            df = pd.read_excel(file)
        except Exception as e:
            return Response({'success': False, 'error': f'Invalid Excel file: {str(e)}'})
        
        # Expected columns: name, emis_number, school_type, province, district, city, address, phone, email, website, principal_name
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
                # Validate school_type
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
        
        # Filter by closing date (only show open bursaries)
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
        """Upload multiple question papers at once"""
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
                # Auto-extract title from filename
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


# education/views.py - Make sure these are at the bottom

def education_home(request):
    """Single unified education page for all education content"""
    from django.db.models import Q
    from django.utils import timezone
    
    # Get all active data
    grades = Grade.objects.filter(is_active=True).order_by('order')
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    universities = University.objects.filter(is_active=True).order_by('name')
    schools = School.objects.filter(is_active=True).order_by('name')
    
    # Get active bursaries
    bursaries = Bursary.objects.filter(
        is_active=True, 
        closing_date__gte=timezone.now().date()
    ).order_by('-created_at')[:50]
    
    # Get question papers
    papers = QuestionPaper.objects.filter(is_public=True).select_related('grade', 'subject').order_by('-year', 'subject__name')[:50]
    
    # Get education news
    news = EducationNews.objects.filter(is_published=True).order_by('-published_at')[:10]
    
    # Get field choices for filters
    field_choices = dict(Bursary.FIELD_CHOICES)
    level_choices = dict(Bursary.LEVEL_CHOICES)
    
    # Get distinct fields and levels from database
    available_fields = Bursary.objects.filter(is_active=True).values_list('field_of_study', flat=True).distinct()
    available_levels = Bursary.objects.filter(is_active=True).values_list('level', flat=True).distinct()
    
    # Check if user is admin/business
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
    """View bursary details"""
    from django.utils import timezone
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



@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key"""
    if dictionary is None:
        return None
    return dictionary.get(key, key)



# education/views.py - Add this function

def news_list(request):
    """View all education news articles"""
    from django.core.paginator import Paginator
    
    # Get all published news
    news_items = EducationNews.objects.filter(is_published=True).order_by('-published_at')
    
    # Paginate
    paginator = Paginator(news_items, 20)
    page = request.GET.get('page', 1)
    news_page = paginator.get_page(page)
    
    # Get categories for filter
    categories = EducationNews.objects.filter(is_published=True).values_list('category', flat=True).distinct()
    category_choices = dict(EducationNews.CATEGORY_CHOICES)
    
    # Check if user is admin
    is_admin = request.user.is_authenticated and (request.user.is_superuser or getattr(request.user, 'user_type', '') == 'admin')
    
    context = {
        'news_items': news_page,
        'categories': categories,
        'category_choices': category_choices,
        'is_admin': is_admin,
    }
    
    return render(request, 'education/news_list.html', context)   