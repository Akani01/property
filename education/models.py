from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils import timezone
import uuid
import os

User = get_user_model()

# ============================================
# DYNAMIC MODELS FOR EDUCATION APP
# ============================================

class Grade(models.Model):
    """Dynamic grades - e.g., Grade 10, Grade 11, Grade 12, etc."""
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="e.g., G10, G11, G12")
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Grade'
        verbose_name_plural = 'Grades'
    
    def __str__(self):
        return self.name


class Subject(models.Model):
    """Dynamic subjects - can be added by admins"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    description = models.TextField(blank=True)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='subjects')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['grade__order', 'name']
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
    
    def __str__(self):
        return f"{self.name} ({self.grade.name})"


class University(models.Model):
    """Dynamic universities"""
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    province = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(
        upload_to='universities/logos/%Y/%m/%d/',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'University'
        verbose_name_plural = 'Universities'
    
    def __str__(self):
        return self.name


class School(models.Model):
    """Dynamic schools - can be uploaded via Excel"""
    SCHOOL_TYPES = (
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
        ('combined', 'Combined School'),
        ('special', 'Special Needs School'),
        ('early_childhood', 'Early Childhood Development'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=200)
    emis_number = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="EMIS number from Department of Education")
    school_type = models.CharField(max_length=20, choices=SCHOOL_TYPES, default='secondary')
    province = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    principal_name = models.CharField(max_length=200, blank=True)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
        indexes = [
            models.Index(fields=['emis_number']),
            models.Index(fields=['province']),
            models.Index(fields=['school_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_school_type_display()})"


class Bursary(models.Model):
    """Dynamic bursary opportunities"""
    LEVEL_CHOICES = (
        ('undergraduate', 'Undergraduate'),
        ('postgraduate', 'Postgraduate'),
        ('phd', 'PhD'),
        ('diploma', 'Diploma'),
        ('certificate', 'Certificate'),
        ('short_course', 'Short Course'),
        ('other', 'Other'),
    )
    
    FIELD_CHOICES = (
        ('engineering', 'Engineering'),
        ('medicine', 'Medicine'),
        ('business', 'Business'),
        ('arts', 'Arts'),
        ('science', 'Science'),
        ('education', 'Education'),
        ('law', 'Law'),
        ('technology', 'Technology'),
        ('agriculture', 'Agriculture'),
        ('health', 'Health Sciences'),
        ('social_sciences', 'Social Sciences'),
        ('humanities', 'Humanities'),
        ('other', 'Other'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    provider = models.CharField(max_length=200, help_text="Company or organization providing the bursary")
    provider_website = models.URLField(blank=True)
    provider_logo = models.ImageField(
        upload_to='bursaries/logos/%Y/%m/%d/',
        blank=True,
        null=True
    )
    
    field_of_study = models.CharField(max_length=50, choices=FIELD_CHOICES)
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES)
    
    # Dynamic many-to-many relationships
    universities = models.ManyToManyField(University, related_name='bursaries', blank=True)
    grades = models.ManyToManyField(Grade, related_name='bursaries', blank=True)
    
    amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    closing_date = models.DateField()
    application_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    requirements = models.TextField(blank=True, help_text="Eligibility requirements")
    required_documents = models.TextField(blank=True, help_text="List of required documents")
    
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bursary'
        verbose_name_plural = 'Bursaries'
        indexes = [
            models.Index(fields=['field_of_study']),
            models.Index(fields=['level']),
            models.Index(fields=['closing_date']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.provider}"
    
    def days_until_closing(self):
        if self.closing_date:
            delta = self.closing_date - timezone.now().date()
            return delta.days
        return None


class QuestionPaper(models.Model):
    """Dynamic question papers with automatic name extraction"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Dynamic relationships
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='question_papers')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='question_papers')
    
    # Paper metadata
    year = models.IntegerField(help_text="Year of the exam")
    term = models.CharField(max_length=10, blank=True, help_text="e.g., Term 1, Term 2, Mid-year")
    paper_number = models.CharField(max_length=10, blank=True, help_text="e.g., Paper 1, Paper 2")
    total_marks = models.IntegerField(blank=True, null=True)
    duration_minutes = models.IntegerField(blank=True, null=True)
    
    # File upload - multiple at once supported
    file = models.FileField(
        upload_to='question_papers/%Y/%m/%d/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])]
    )
    file_name = models.CharField(max_length=255, blank=True, help_text="Auto-extracted from file")
    file_size = models.BigIntegerField(blank=True, null=True)
    
    is_public = models.BooleanField(default=True)
    download_count = models.PositiveIntegerField(default=0)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year', 'grade__order', 'subject__name']
        verbose_name = 'Question Paper'
        verbose_name_plural = 'Question Papers'
        indexes = [
            models.Index(fields=['grade']),
            models.Index(fields=['subject']),
            models.Index(fields=['year']),
        ]
    
    def __str__(self):
        return f"{self.subject.name} - {self.grade.name} ({self.year})"
    
    def save(self, *args, **kwargs):
        # Auto-extract file name if not provided
        if self.file and not self.file_name:
            self.file_name = os.path.basename(self.file.name)
        if self.file:
            try:
                self.file_size = self.file.size
            except:
                pass
        super().save(*args, **kwargs)


class BursaryApplication(models.Model):
    """User applications for bursaries"""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview Scheduled'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bursary_applications')
    bursary = models.ForeignKey(Bursary, on_delete=models.CASCADE, related_name='applications')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Personal details
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    id_number = models.CharField(max_length=20, blank=True)
    
    # Academic details
    current_grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True, blank=True, related_name='bursary_applications')
    current_institution = models.CharField(max_length=200, blank=True)
    current_institution_type = models.CharField(max_length=50, blank=True, choices=[
        ('school', 'School'),
        ('university', 'University'),
        ('college', 'College'),
        ('other', 'Other'),
    ])
    academic_average = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    # Motivation and documents
    motivation = models.TextField(blank=True)
    
    # Uploaded documents
    cv = models.FileField(
        upload_to='bursary_applications/cvs/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])]
    )
    academic_transcript = models.FileField(
        upload_to='bursary_applications/transcripts/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf'])]
    )
    id_document = models.FileField(
        upload_to='bursary_applications/id_docs/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])]
    )
    other_documents = models.FileField(
        upload_to='bursary_applications/other/%Y/%m/%d/',
        blank=True,
        null=True
    )
    
    # Admin notes
    admin_notes = models.TextField(blank=True)
    
    submitted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bursary Application'
        verbose_name_plural = 'Bursary Applications'
        unique_together = ['applicant', 'bursary']
    
    def __str__(self):
        return f"{self.applicant.username} - {self.bursary.title}"
    
    def submit(self):
        self.status = 'submitted'
        self.submitted_at = timezone.now()
        self.save()


class UniversityApplication(models.Model):
    """User applications to universities"""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('interview', 'Interview Scheduled'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='university_applications')
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='applications')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Personal details
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    id_number = models.CharField(max_length=20, blank=True)
    
    # Academic details
    current_grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True, related_name='university_applications')
    academic_average = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    # Program details
    program_of_interest = models.CharField(max_length=200, blank=True)
    program_code = models.CharField(max_length=50, blank=True)
    
    # Motivation and documents
    motivation = models.TextField(blank=True)
    
    cv = models.FileField(
        upload_to='university_applications/cvs/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])]
    )
    academic_transcript = models.FileField(
        upload_to='university_applications/transcripts/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf'])]
    )
    id_document = models.FileField(
        upload_to='university_applications/id_docs/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])]
    )
    
    admin_notes = models.TextField(blank=True)
    
    submitted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'University Application'
        verbose_name_plural = 'University Applications'
        unique_together = ['applicant', 'university']
    
    def __str__(self):
        return f"{self.applicant.username} - {self.university.name}"


class SchoolApplication(models.Model):
    """User applications to schools"""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('interview', 'Interview Scheduled'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('waitlisted', 'Waitlisted'),
        ('withdrawn', 'Withdrawn'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='school_applications')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='applications')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Student details
    student_full_name = models.CharField(max_length=200)
    student_email = models.EmailField()
    student_phone = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    id_number = models.CharField(max_length=20, blank=True)
    
    # Parent/Guardian details
    parent_name = models.CharField(max_length=200, blank=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    parent_email = models.EmailField(blank=True)
    
    # Academic details
    current_grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True, blank=True)
    previous_school = models.CharField(max_length=200, blank=True)
    
    # Documents
    birth_certificate = models.FileField(
        upload_to='school_applications/birth/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])]
    )
    report_card = models.FileField(
        upload_to='school_applications/reports/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf'])]
    )
    
    admin_notes = models.TextField(blank=True)
    
    submitted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'School Application'
        verbose_name_plural = 'School Applications'
        unique_together = ['applicant', 'school']
    
    def __str__(self):
        return f"{self.applicant.username} - {self.school.name}"


class EducationNews(models.Model):
    """News and updates for the education section"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    summary = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='education/news/%Y/%m/%d/',
        blank=True,
        null=True
    )
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=50, blank=True, choices=[
        ('bursary', 'Bursary News'),
        ('university', 'University News'),
        ('school', 'School News'),
        ('general', 'General'),
        ('exam', 'Exam Updates'),
    ])
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Education News'
        verbose_name_plural = 'Education News'
    
    def __str__(self):
        return self.title