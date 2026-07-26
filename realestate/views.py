from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.views.decorators.csrf import csrf_exempt 
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from notifications.models import *
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import re
import json
import requests
from datetime import datetime, timedelta
from decimal import Decimal

# ===== IMPORTS FROM HIRING APP =====
from hiring.models import (
    Post, 
    Comment, 
    Video, 
    VideoComment,
    JobListing,
    Application,
    CustomUser,
    ApplicantProfile,
    BusinessProfile,
    Alert,
    BusinessAlert,
)
from hiring.serializers import (
    PostSerializer,
    VideoSerializer,
    VideoCommentSerializer,
    JobListingSerializer,
    CustomUserSerializer,
)

# ===== IMPORTS FROM REALESTATE APP =====
from .models import (
    PropertyCategory,
    PropertyType,
    PropertyFeature,
    Property,
    Room,
    Booking,
    AvailabilityCalendar,
    BookingInquiry,
    PropertyReview,
    Wishlist,
    PropertyAnalytics,
    MaintenanceCategory,
    MaintenanceRequest,
    MaintenanceComment,
    DriverLocation,
)

from .serializers import (
    PropertyCategorySerializer,
    PropertyTypeSerializer,
    PropertyFeatureSerializer,
    PropertySerializer,
    PropertyListSerializer,
    PropertyCreateSerializer,
    PropertyDetailSerializer,
    PropertyUpdateSerializer,
    RoomSerializer,
    BookingSerializer,
    AvailabilityCalendarSerializer,
    BookingInquirySerializer,
    PropertyReviewSerializer,
    WishlistSerializer,
    PropertyAnalyticsSerializer,
    MaintenanceCategorySerializer,
    MaintenanceRequestSerializer,
    MaintenanceCommentSerializer,
    DriverLocationSerializer,
)


# ============================================================
# ROOM VIEWSET
# ============================================================
class RoomViewSet(viewsets.ModelViewSet):
    """Room management"""
    queryset = Room.objects.filter(is_active=True)
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['property', 'room_type', 'room_status']
    search_fields = ['room_number', 'room_name', 'description']


# ============================================================
# PROPERTY CATEGORY VIEWSET
# ============================================================
class PropertyCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for dynamic property categories"""
    queryset = PropertyCategory.objects.filter(is_active=True)
    serializer_class = PropertyCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category_type', 'is_system']
    search_fields = ['name', 'description']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ============================================================
# PROPERTY TYPE VIEWSET
# ============================================================
class PropertyTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for property types"""
    queryset = PropertyType.objects.filter(is_active=True)
    serializer_class = PropertyTypeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'size_classification', 'is_system']
    search_fields = ['name', 'description']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ============================================================
# PROPERTY FEATURE VIEWSET
# ============================================================
class PropertyFeatureViewSet(viewsets.ModelViewSet):
    """ViewSet for property features"""
    queryset = PropertyFeature.objects.filter(is_active=True)
    serializer_class = PropertyFeatureSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'is_custom']
    search_fields = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, is_custom=True)


# ============================================================
# PROPERTY VIEWSET
# ============================================================
class PropertyViewSet(viewsets.ModelViewSet):
    """Main Property ViewSet with all features including image management"""
    queryset = Property.objects.filter(is_active=True)
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'property_type', 'status', 'listing_type', 'booking_mode',
        'city', 'state', 'country', 'is_featured', 'is_premium',
        'is_online', 'is_verified'
    ]
    search_fields = ['title', 'description', 'address', 'city', 'property_reference']
    ordering_fields = ['base_price', 'created_at', 'views_count', 'bedrooms', 'bathrooms']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PropertyListSerializer
        elif self.action == 'create':
            return PropertyCreateSerializer
        elif self.action == 'retrieve':
            return PropertyDetailSerializer
        elif self.action in ['update', 'partial_update']:
            return PropertyUpdateSerializer
        return PropertySerializer
    
    def perform_create(self, serializer):
        company = None
        try:
            from hiring.models import BusinessProfile
            company = self.request.user.business_profile
        except:
            pass
        
        serializer.save(
            company=company,
            listing_agent=self.request.user,
            owner=self.request.user
        )
    
    @action(detail=True, methods=['post'], url_path='update-image')
    def update_image(self, request, pk=None):
        """Update property main image"""
        property_obj = self.get_object()
        
        if 'main_image' not in request.FILES:
            return Response({
                'success': False,
                'error': 'No image file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            file = request.FILES['main_image']
            valid_extensions = ['jpg', 'jpeg', 'png', 'webp', 'gif']
            ext = file.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                return Response({
                    'success': False,
                    'error': f'Invalid file type. Supported: {", ".join(valid_extensions)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if file.size > 10 * 1024 * 1024:
                return Response({
                    'success': False,
                    'error': 'File too large. Max 10MB.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if property_obj.main_image:
                try:
                    property_obj.main_image.delete(save=False)
                except:
                    pass
            
            property_obj.main_image = file
            property_obj.save(update_fields=['main_image', 'updated_at'])
            
            return Response({
                'success': True,
                'message': 'Main image updated successfully',
                'image_url': property_obj.get_main_image_url()
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='remove-image')
    def remove_image(self, request, pk=None):
        property_obj = self.get_object()
        if not property_obj.main_image:
            return Response({
                'success': False,
                'error': 'No image to remove'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            property_obj.main_image.delete(save=False)
            property_obj.main_image = None
            property_obj.save(update_fields=['main_image', 'updated_at'])
            return Response({
                'success': True,
                'message': 'Image removed successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='add-additional-image')
    def add_additional_image(self, request, pk=None):
        property_obj = self.get_object()
        if 'image' not in request.FILES:
            return Response({
                'success': False,
                'error': 'No image file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            file = request.FILES['image']
            valid_extensions = ['jpg', 'jpeg', 'png', 'webp', 'gif']
            ext = file.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                return Response({
                    'success': False,
                    'error': f'Invalid file type. Supported: {", ".join(valid_extensions)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            if file.size > 10 * 1024 * 1024:
                return Response({
                    'success': False,
                    'error': 'File too large. Max 10MB.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            additional_images = property_obj.additional_images or []
            import uuid
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            filename = f"additional_{uuid.uuid4().hex[:8]}.{ext}"
            path = f"properties/additional/{timezone.now().strftime('%Y/%m/%d')}/{filename}"
            saved_path = default_storage.save(path, ContentFile(file.read()))
            try:
                file_url = default_storage.url(saved_path)
            except:
                file_url = f"/media/{saved_path}"
            
            additional_images.append(file_url)
            property_obj.additional_images = additional_images
            property_obj.save(update_fields=['additional_images', 'updated_at'])
            
            return Response({
                'success': True,
                'message': 'Image added successfully',
                'image_url': file_url,
                'images': additional_images
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='remove-additional-image')
    def remove_additional_image(self, request, pk=None):
        property_obj = self.get_object()
        index = request.data.get('index')
        if index is None:
            return Response({
                'success': False,
                'error': 'Image index required'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            index = int(index)
            additional_images = property_obj.additional_images or []
            if 0 <= index < len(additional_images):
                removed_url = additional_images.pop(index)
                property_obj.additional_images = additional_images
                property_obj.save(update_fields=['additional_images', 'updated_at'])
                try:
                    from django.core.files.storage import default_storage
                    from urllib.parse import urlparse
                    parsed = urlparse(removed_url)
                    path = parsed.path.lstrip('/')
                    if default_storage.exists(path):
                        default_storage.delete(path)
                except:
                    pass
                return Response({
                    'success': True,
                    'message': 'Image removed successfully',
                    'images': additional_images
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid image index'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def toggle_online(self, request, pk=None):
        property_obj = self.get_object()
        property_obj.is_online = not property_obj.is_online
        property_obj.save()
        return Response({
            'is_online': property_obj.is_online,
            'agent_status': property_obj.agent_status
        })

    @action(detail=True, methods=['post'])
    def delete(self, request, pk=None):
        property_obj = self.get_object()
        property_obj.is_active = False
        property_obj.save()
        return Response({
            'success': True,
            'message': 'Property deleted successfully'
        })


# ============================================================
# BOOKING VIEWSET
# ============================================================
class BookingViewSet(viewsets.ModelViewSet):
    """ViewSet for bookings"""
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'booking_mode', 'property']
    ordering_fields = ['created_at', 'check_in', 'check_out']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return self.queryset.filter(guest=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(guest=self.request.user)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        booking.status = 'cancelled'
        booking.cancellation_date = timezone.now()
        booking.save()
        return Response({'message': 'Booking cancelled successfully'})


# ============================================================
# DRIVER LOCATION VIEWSET
# ============================================================
class DriverLocationViewSet(viewsets.ModelViewSet):
    """ViewSet for driver locations"""
    queryset = DriverLocation.objects.filter(is_active=True)
    serializer_class = DriverLocationSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def update_location(self, request):
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        if not lat or not lng:
            return Response(
                {'error': 'Latitude and longitude required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        location, created = DriverLocation.objects.update_or_create(
            driver=request.user,
            defaults={'latitude': lat, 'longitude': lng, 'is_active': True}
        )
        return Response(DriverLocationSerializer(location).data)


# ============================================================
# AVAILABILITY CALENDAR VIEWSET
# ============================================================
class AvailabilityCalendarViewSet(viewsets.ModelViewSet):
    queryset = AvailabilityCalendar.objects.all()
    serializer_class = AvailabilityCalendarSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['property', 'room', 'availability_type']


# ============================================================
# BOOKING INQUIRY VIEWSET
# ============================================================
class BookingInquiryViewSet(viewsets.ModelViewSet):
    queryset = BookingInquiry.objects.all()
    serializer_class = BookingInquirySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'inquiry_type', 'property']
    search_fields = ['first_name', 'last_name', 'email']


# ============================================================
# PROPERTY REVIEW VIEWSET
# ============================================================
class PropertyReviewViewSet(viewsets.ModelViewSet):
    queryset = PropertyReview.objects.filter(is_approved=True)
    serializer_class = PropertyReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['property', 'overall_rating']
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ============================================================
# WISHLIST VIEWSET
# ============================================================
class WishlistViewSet(viewsets.ModelViewSet):
    """ViewSet for wishlists"""
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_property(self, request, pk=None):
        wishlist = self.get_object()
        property_id = request.data.get('property_id')
        if not property_id:
            return Response(
                {'error': 'Property ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        property_obj = get_object_or_404(Property, id=property_id)
        wishlist.properties.add(property_obj)
        return Response({'message': 'Property added to wishlist'})
    
    @action(detail=True, methods=['post'])
    def remove_property(self, request, pk=None):
        wishlist = self.get_object()
        property_id = request.data.get('property_id')
        if not property_id:
            return Response(
                {'error': 'Property ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        property_obj = get_object_or_404(Property, id=property_id)
        wishlist.properties.remove(property_obj)
        return Response({'message': 'Property removed from wishlist'})


# ============================================================
# PROPERTY ANALYTICS VIEWSET
# ============================================================
class PropertyAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PropertyAnalytics.objects.all()
    serializer_class = PropertyAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            from hiring.models import BusinessProfile
            business_profile = self.request.user.business_profile
            properties = Property.objects.filter(company=business_profile)
            return PropertyAnalytics.objects.filter(property__in=properties)
        except:
            return PropertyAnalytics.objects.none()


# ============================================================
# ===== MAINTENANCE VIEWSETS =====
# ============================================================

class MaintenanceCategoryViewSet(viewsets.ModelViewSet):
    """Complete CRUD for categories - simple and clean"""
    queryset = MaintenanceCategory.objects.filter(is_active=True)
    serializer_class = MaintenanceCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.user_type == 'admin' or self.request.user.is_superuser:
            return MaintenanceCategory.objects.all()
        return MaintenanceCategory.objects.filter(is_active=True)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        category = self.get_object()
        category.is_active = not category.is_active
        category.save()
        return Response({
            'success': True,
            'is_active': category.is_active,
            'message': f"Category {'activated' if category.is_active else 'deactivated'} successfully"
        })


class MaintenanceCommentViewSet(viewsets.ModelViewSet):
    """Maintenance comments management"""
    serializer_class = MaintenanceCommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin' or user.is_superuser:
            return MaintenanceComment.objects.all()
        return MaintenanceComment.objects.filter(request__tenant=user)
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        comment = self.get_object()
        return Response({
            'success': True,
            'message': 'Comment liked',
            'likes_count': 0
        })
    
    @action(detail=True, methods=['delete'])
    def delete_comment(self, request, pk=None):
        comment = self.get_object()
        if comment.author != request.user and request.user.user_type not in ['admin']:
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response({
            'success': True,
            'message': 'Comment deleted successfully'
        })


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    """Complete maintenance management with location and natural language"""
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin' or user.is_superuser:
            return MaintenanceRequest.objects.all().select_related('category', 'tenant', 'property')
        return MaintenanceRequest.objects.filter(tenant=user).select_related('category', 'property')
    
    @action(detail=False, methods=['post'])
    def quick_create(self, request):
        """Create maintenance request from natural language text - with location support"""
        user = request.user
        text = request.data.get('text', '').strip()
        tags = request.data.get('tags', '[]')
        image = request.FILES.get('image', None)
        
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except:
                tags = []
        
        latitude = request.data.get('latitude', None)
        longitude = request.data.get('longitude', None)
        location_name = request.data.get('location_name', None)
        
        if not text and not image:
            return Response({
                'success': False,
                'error': 'Please describe the issue or add a photo'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        parsed = self.parse_natural_language(text)
        title = parsed.get('title', text[:100] if text else 'Maintenance Request')
        description = parsed.get('description', text if text else '')
        
        priority = 'medium'
        request_status = 'pending'  # CHANGED: renamed to avoid conflict with imported status
        location = location_name or None
        estimated_cost = None
        preferred_date = None
        notes = None
        
        for tag in tags:
            tag_lower = tag.lower() if isinstance(tag, str) else str(tag).lower()
            if tag_lower in ['urgent', 'high', 'medium', 'low']:
                priority = tag_lower
            elif tag_lower in ['completed', 'in_progress', 'pending', 'cancelled']:
                request_status = tag_lower
            elif tag_lower in ['💰', 'cost', '$']:
                cost_match = re.search(r'\$?(\d+\.?\d*)', text)
                if cost_match:
                    estimated_cost = float(cost_match.group(1))
            elif tag_lower in ['📅', 'date']:
                date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
                if date_match:
                    try:
                        preferred_date = self.parse_date(date_match.group(1))
                    except:
                        pass
            elif tag_lower in ['📍', 'location']:
                if not location:
                    location_match = re.search(r'(?:in|at|near)\s+([a-zA-Z\s,]+)', text, re.IGNORECASE)
                    if location_match:
                        location = location_match.group(1).strip()
            elif tag_lower in ['📝', 'note']:
                notes = description
        
        if latitude and longitude and not location:
            location = self.get_location_from_coords(float(latitude), float(longitude))
        
        try:
            # ===== FIX: Get or create a default property =====
            property_id = request.data.get('property_id', None)
            
            if not property_id:
                # Try to find an existing property for this user
                default_property = Property.objects.filter(owner=user).first()
                if not default_property:
                    # Create a default property if none exists
                    default_property = Property.objects.create(
                        title=f"{user.username}'s Property",
                        description="Default property for maintenance requests",
                        owner=user,
                        is_active=True,
                        status='available'
                    )
                property_id = default_property.id
            
            request_obj = MaintenanceRequest.objects.create(
                title=title,
                description=description,
                priority=priority,
                status=request_status,  # CHANGED: using renamed variable
                location=location,
                estimated_cost=estimated_cost,
                preferred_date=preferred_date,
                notes=notes,
                tenant=user,
                property_id=property_id  # CHANGED: using property_id directly
            )
            
            if image:
                request_obj.image = image
                request_obj.save()
            
            auto_reply = self.generate_auto_reply(request_obj, location)
            
            return Response({
                'success': True,
                'request': MaintenanceRequestSerializer(request_obj).data,
                'auto_reply': auto_reply,
                'message': 'Maintenance request created successfully!',
                'location_detected': bool(location)
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error creating maintenance request: {str(e)}")
            print(error_details)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_location_from_coords(self, lat, lng):
        try:
            api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
            if api_key:
                url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={api_key}'
                response = requests.get(url, timeout=5)
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    return data['results'][0].get('formatted_address', '')
            return f"📍 {round(lat, 4)}, {round(lng, 4)}"
        except:
            return f"📍 {round(lat, 4)}, {round(lng, 4)}"
    
    def parse_natural_language(self, text):
        parsed = {
            'title': text[:100] if text else 'Maintenance Request',
            'description': text if text else '',
            'priority': 'medium',
            'status': 'pending'
        }
        if not text:
            return parsed
        
        text_lower = text.lower()
        urgency_words = {
            'urgent': ['urgent', 'emergency', 'asap', 'immediately', 'right now', 'quick'],
            'high': ['high priority', 'important', 'critical', 'serious'],
            'low': ['low priority', 'not urgent', 'whenever', 'eventually']
        }
        for priority, words in urgency_words.items():
            if any(word in text_lower for word in words):
                parsed['priority'] = priority
                break
        
        if 'done' in text_lower or 'complete' in text_lower or 'fixed' in text_lower:
            parsed['status'] = 'completed'
        elif 'progress' in text_lower or 'working' in text_lower:
            parsed['status'] = 'in_progress'
        elif 'cancel' in text_lower:
            parsed['status'] = 'cancelled'
        
        issue_patterns = [
            r'(?:issue|problem|need|want)\s+(?:with\s+)?([\w\s]+)',
            r'(?:fix|repair|replace)\s+([\w\s]+)',
            r'([\w\s]+)\s+(?:is|are)\s+(?:broken|not\s+working|leaking)'
        ]
        for pattern in issue_patterns:
            match = re.search(pattern, text_lower)
            if match:
                parsed['title'] = match.group(1).strip().title()
                break
        return parsed
    
    def parse_date(self, date_str):
        for fmt in ['%m/%d/%Y', '%m/%d/%y', '%m-%d-%Y', '%m-%d-%y', '%Y-%m-%d']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        return None
    
    def generate_auto_reply(self, request_obj, location=None):
        priority_emojis = {'urgent': '🚨', 'high': '🔴', 'medium': '🟡', 'low': '🟢'}
        status_emojis = {'pending': '⏳', 'in_progress': '🔄', 'completed': '✅', 'cancelled': '❌'}
        
        reply = f"{priority_emojis.get(request_obj.priority, '📋')} **Request #{request_obj.id} Created!**\n\n"
        reply += f"**Issue:** {request_obj.title}\n"
        reply += f"**Priority:** {request_obj.priority.upper()}\n"
        reply += f"**Status:** {status_emojis.get(request_obj.status, '')} {request_obj.status.replace('_', ' ').title()}\n"
        if location or request_obj.location:
            reply += f"**📍 Location:** {location or request_obj.location}\n"
        if request_obj.estimated_cost:
            reply += f"**💰 Estimated Cost:** ${request_obj.estimated_cost:.2f}\n"
        if request_obj.preferred_date:
            reply += f"**📅 Preferred Date:** {request_obj.preferred_date.strftime('%b %d, %Y')}\n"
        reply += f"\n📌 I've created your maintenance request. I'll keep you updated on the progress!"
        if location:
            reply += f"\n\n📍 Location detected: {location}"
        return reply
    
    @action(detail=False, methods=['get'])
    def feed(self, request):
        queryset = self.get_queryset()
        
        status_filter = request.query_params.get('status', None)
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        priority_filter = request.query_params.get('priority', None)
        if priority_filter and priority_filter != 'all':
            queryset = queryset.filter(priority=priority_filter)
        
        search = request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search)
            )
        
        queryset = queryset.order_by('-created_at')
        
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        requests_data = queryset[start:end]
        
        data = []
        for req in requests_data:
            req_data = MaintenanceRequestSerializer(req).data
            comments = MaintenanceComment.objects.filter(request=req).order_by('-created_at')[:3]
            req_data['recent_comments'] = MaintenanceCommentSerializer(comments, many=True).data
            req_data['total_comments'] = MaintenanceComment.objects.filter(request=req).count()
            req_data['likes_count'] = 0
            data.append(req_data)
        
        return Response({
            'success': True,
            'requests': data,
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'has_next': end < total,
                'has_previous': page > 1
            }
        })
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        request_obj = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(MaintenanceRequest.Status.choices):
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        if request_obj.tenant != request.user and request.user.user_type not in ['admin']:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        request_obj.status = new_status
        if new_status == MaintenanceRequest.Status.COMPLETED:
            request_obj.completed_at = timezone.now()
        request_obj.save()
        
        return Response({
            'success': True,
            'status': request_obj.status,
            'status_display': request_obj.get_status_display()
        })
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        request_obj = self.get_object()
        content = request.data.get('content')
        
        if not content:
            return Response({'error': 'Comment content is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        comment = MaintenanceComment.objects.create(
            request=request_obj,
            author=request.user,
            content=content
        )
        
        serializer = MaintenanceCommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        request_obj = self.get_object()
        comments = MaintenanceComment.objects.filter(request=request_obj).order_by('-created_at')
        serializer = MaintenanceCommentSerializer(comments, many=True, context={'request': request})
        return Response({
            'success': True,
            'comments': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        return Response({
            'success': True,
            'likes_count': 1,
            'liked': True
        })
    
    @action(detail=True, methods=['delete'])
    def delete_request(self, request, pk=None):
        request_obj = self.get_object()
        
        if request_obj.tenant != request.user and request.user.user_type not in ['admin']:
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        request_obj.delete()
        return Response({
            'success': True,
            'message': 'Request deleted successfully'
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        user = request.user
        
        if user.user_type == 'admin' or user.is_superuser:
            queryset = MaintenanceRequest.objects.all()
        else:
            queryset = MaintenanceRequest.objects.filter(tenant=user)
        
        stats = {
            'total': queryset.count(),
            'pending': queryset.filter(status=MaintenanceRequest.Status.PENDING).count(),
            'in_progress': queryset.filter(status=MaintenanceRequest.Status.IN_PROGRESS).count(),
            'completed': queryset.filter(status=MaintenanceRequest.Status.COMPLETED).count(),
            'cancelled': queryset.filter(status=MaintenanceRequest.Status.CANCELLED).count(),
        }
        
        category_stats = []
        for category in MaintenanceCategory.objects.filter(is_active=True):
            count = queryset.filter(category=category).count()
            if count > 0:
                category_stats.append({
                    'category': category.name,
                    'count': count,
                    'color': category.color,
                    'icon': category.icon
                })
        
        stats['by_category'] = category_stats
        return Response(stats)


# ============================================================
# JOB VIEWSET - FIXED: No is_active filter
# ============================================================
class JobViewSet(viewsets.ModelViewSet):
    """Job management using JobListing from hiring app"""
    queryset = JobListing.objects.all()
    serializer_class = JobListingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin' or user.is_superuser:
            return JobListing.objects.all()
        return JobListing.objects.filter(status='published')
    
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        job = self.get_object()
        user = request.user
        
        try:
            applicant_profile = user.applicantprofile
        except:
            return Response({
                'success': False,
                'error': 'Please complete your applicant profile first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if Application.objects.filter(job_listing=job, applicant=applicant_profile).exists():
            return Response({
                'success': False,
                'error': 'You have already applied for this job'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        application = Application.objects.create(
            job_listing=job,
            applicant=applicant_profile,
            status='submitted'
        )
        
        return Response({
            'success': True,
            'message': 'Application submitted successfully',
            'application_id': str(application.id)
        })


# ============================================================
# POST VIEWSET
# ============================================================
class PostViewSet(viewsets.ModelViewSet):
    """Post management using Post from hiring app"""
    queryset = Post.objects.filter(is_published=True)
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Post.objects.filter(is_published=True).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=False, methods=['get'])
    def feed(self, request):
        posts = self.get_queryset()[:20]
        serializer = self.get_serializer(posts, many=True)
        return Response({
            'success': True,
            'posts': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def like_dislike(self, request, pk=None):
        post = self.get_object()
        action = request.data.get('action', 'like')
        
        if action == 'like':
            if request.user in post.likes.all():
                post.likes.remove(request.user)
                liked = False
            else:
                post.likes.add(request.user)
                post.dislikes.remove(request.user)
                liked = True
        elif action == 'dislike':
            if request.user in post.dislikes.all():
                post.dislikes.remove(request.user)
                liked = False
            else:
                post.dislikes.add(request.user)
                post.likes.remove(request.user)
                liked = True
        else:
            return Response({
                'success': False,
                'error': 'Invalid action'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'likes_count': post.likes.count(),
            'dislikes_count': post.dislikes.count(),
            'liked': liked
        })


# ============================================================
# VIDEO VIEWSET
# ============================================================
class VideoViewSet(viewsets.ModelViewSet):
    """Video management using Video from hiring app"""
    queryset = Video.objects.filter(is_published=True)
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin' or user.is_superuser:
            return Video.objects.all().order_by('-created_at')
        return Video.objects.filter(is_published=True, privacy='public').order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=False, methods=['get'])
    def feed(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size
        
        videos = self.get_queryset()[start:end]
        total = self.get_queryset().count()
        
        serializer = self.get_serializer(videos, many=True)
        return Response({
            'success': True,
            'videos': serializer.data,
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'has_next': end < total
            }
        })
    
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        video = self.get_object()
        
        if request.user in video.likes.all():
            video.likes.remove(request.user)
            liked = False
        else:
            video.likes.add(request.user)
            liked = True
        
        return Response({
            'success': True,
            'likes_count': video.likes.count(),
            'liked': liked
        })
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        video = self.get_object()
        video.shares += 1
        video.save(update_fields=['shares'])
        
        return Response({
            'success': True,
            'shares_count': video.shares,
            'message': 'Video shared'
        })
    
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        video = self.get_object()
        comments = VideoComment.objects.filter(
            video=video,
            is_active=True,
            parent_comment__isnull=True
        ).order_by('-created_at')
        
        serializer = VideoCommentSerializer(comments, many=True, context={'request': request})
        return Response({
            'success': True,
            'comments': serializer.data
        })


# ============================================================
# GEOCODE VIEW
# ============================================================
@csrf_exempt
def geocode_view(request):
    """Reverse geocode coordinates to address"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    
    if not lat or not lng:
        return JsonResponse({'error': 'Missing lat/lng parameters'}, status=400)
    
    try:
        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        if api_key:
            url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={api_key}'
            response = requests.get(url, timeout=5)
            data = response.json()
            if data.get('status') == 'OK' and data.get('results'):
                address = data['results'][0].get('formatted_address', '')
                return JsonResponse({
                    'success': True,
                    'address': address,
                    'lat': float(lat),
                    'lng': float(lng)
                })
        
        url = f'https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18&addressdetails=1'
        headers = {'User-Agent': 'Tolleya/1.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if 'display_name' in data:
            return JsonResponse({
                'success': True,
                'address': data['display_name'],
                'lat': float(lat),
                'lng': float(lng)
            })
        
        return JsonResponse({
            'success': True,
            'address': f"{float(lat):.4f}, {float(lng):.4f}",
            'lat': float(lat),
            'lng': float(lng)
        })
        
    except Exception:
        return JsonResponse({
            'success': True,
            'address': f"{float(lat):.4f}, {float(lng):.4f}",
            'lat': float(lat),
            'lng': float(lng)
        })


# ============================================================
# API ENDPOINTS FOR PROPERTY ADD
# ============================================================

@api_view(['GET'])
def get_property_types(request):
    """Get all property types for the frontend"""
    types = PropertyType.objects.all().order_by('name')
    serializer = PropertyTypeSerializer(types, many=True)
    return Response({
        'success': True,
        'types': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_property_type_api(request):
    """Add a new property type via AJAX"""
    name = request.data.get('name', '').strip()
    category_id = request.data.get('category')
    
    if not name:
        return Response({
            'success': False,
            'error': 'Name is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if PropertyType.objects.filter(name__iexact=name).exists():
        return Response({
            'success': False,
            'error': f'Property type "{name}" already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        type_obj = PropertyType.objects.create(
            name=name,
            category_id=category_id if category_id else None,
            is_active=True,
            created_by=request.user
        )
        
        return Response({
            'success': True,
            'message': f'Property type "{name}" created successfully',
            'type': {
                'id': str(type_obj.id),
                'name': type_obj.name,
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_feature_api(request):
    """Add a new feature via AJAX"""
    name = request.data.get('name', '').strip()
    category = request.data.get('category', 'other')
    icon = request.data.get('icon', 'fas fa-tag')
    
    if not name:
        return Response({
            'success': False,
            'error': 'Name is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if PropertyFeature.objects.filter(name__iexact=name).exists():
        return Response({
            'success': False,
            'error': f'Feature "{name}" already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        feature_obj = PropertyFeature.objects.create(
            name=name,
            icon=icon,
            category=category,
            is_custom=True,
            is_active=True,
            created_by=request.user
        )
        
        return Response({
            'success': True,
            'message': f'Feature "{name}" created successfully',
            'feature': {
                'id': str(feature_obj.id),
                'name': feature_obj.name,
                'icon': feature_obj.icon,
                'category': feature_obj.category,
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# GEOCODING & MAP ENDPOINTS
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def geocode_address_api(request):
    """Convert address to coordinates"""
    address = request.data.get('address', '').strip()
    city = request.data.get('city', '').strip()
    country = request.data.get('country', 'South Africa')
    
    if not address or not city:
        return Response({
            'success': False,
            'error': 'Street address and city are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    full_address = f"{address}, {city}, {country}"
    google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    
    if not google_api_key:
        return Response({
            'success': False,
            'error': 'Google Maps API key not configured'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    try:
        url = f'https://maps.googleapis.com/maps/api/geocode/json?address={requests.utils.quote(full_address)}&key={google_api_key}'
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            return Response({
                'success': True,
                'lat': location['lat'],
                'lng': location['lng'],
                'formatted_address': data['results'][0]['formatted_address'],
                'place_id': data['results'][0]['place_id'],
                'full_address': full_address
            })
        else:
            return Response({
                'success': False,
                'error': 'Address not found. Please check and try again.'
            }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_properties(request):
    """Get properties near a location"""
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    radius = float(request.GET.get('radius', 20))
    
    if not lat or not lng:
        return Response({
            'success': False,
            'error': 'Location not provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        return Response({
            'success': False,
            'error': 'Invalid coordinates'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    properties = Property.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('property_type')
    
    nearby = []
    user_location = (lat, lng)
    
    try:
        from geopy.distance import geodesic
        for prop in properties:
            if prop.latitude and prop.longitude:
                prop_location = (float(prop.latitude), float(prop.longitude))
                distance = geodesic(user_location, prop_location).kilometers
                if distance <= radius:
                    nearby.append({
                        'id': str(prop.id),
                        'title': prop.title,
                        'description': prop.description[:200] if prop.description else '',
                        'address': prop.address,
                        'city': prop.city,
                        'country': prop.country,
                        'price': float(prop.base_price) if prop.base_price else 0,
                        'latitude': float(prop.latitude),
                        'longitude': float(prop.longitude),
                        'distance': round(distance, 1),
                        'main_image_url': prop.get_main_image_url(),
                        'is_featured': prop.is_featured,
                        'is_premium': prop.is_premium,
                        'is_online': prop.is_online,
                        'status': prop.status,
                        'bedrooms': prop.bedrooms,
                        'bathrooms': prop.bathrooms,
                        'property_type': prop.property_type.name if prop.property_type else 'Property',
                    })
        nearby.sort(key=lambda x: x['distance'])
    except ImportError:
        for prop in properties:
            if prop.latitude and prop.longitude:
                lat_diff = abs(float(prop.latitude) - lat) * 111
                lng_diff = abs(float(prop.longitude) - lng) * 111 * 0.9
                distance = (lat_diff**2 + lng_diff**2)**0.5
                if distance <= radius:
                    nearby.append({
                        'id': str(prop.id),
                        'title': prop.title,
                        'description': prop.description[:200] if prop.description else '',
                        'address': prop.address,
                        'city': prop.city,
                        'country': prop.country,
                        'price': float(prop.base_price) if prop.base_price else 0,
                        'latitude': float(prop.latitude),
                        'longitude': float(prop.longitude),
                        'distance': round(distance, 1),
                        'main_image_url': prop.get_main_image_url(),
                        'is_featured': prop.is_featured,
                        'is_premium': prop.is_premium,
                        'is_online': prop.is_online,
                        'status': prop.status,
                        'bedrooms': prop.bedrooms,
                        'bathrooms': prop.bathrooms,
                        'property_type': prop.property_type.name if prop.property_type else 'Property',
                    })
        nearby.sort(key=lambda x: x['distance'])
    
    return Response({
        'success': True,
        'properties': nearby,
        'count': len(nearby),
        'user_location': {'lat': lat, 'lng': lng}
    })


# ============================================================
# BUSINESS BOOKINGS API
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_business_bookings(request):
    """Get bookings for business admin"""
    if request.user.user_type != 'admin':
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from hiring.models import BusinessProfile
        business_profile = BusinessProfile.objects.get(user=request.user)
        properties = Property.objects.filter(company=business_profile)
        bookings = Booking.objects.filter(property__in=properties).select_related(
            'property', 'guest'
        ).order_by('-created_at')
        
        booking_data = []
        for booking in bookings:
            booking_data.append({
                'id': str(booking.id),
                'property_title': booking.property.title,
                'guest_name': f"{booking.guest.first_name} {booking.guest.last_name}" if booking.guest else 'Guest',
                'guest_email': booking.guest.email if booking.guest else '',
                'check_in': booking.check_in,
                'check_out': booking.check_out,
                'status': booking.status,
                'total_amount': str(booking.total_amount),
                'booking_reference': booking.booking_reference
            })
        
        return Response({
            'success': True,
            'bookings': booking_data,
            'count': len(booking_data)
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)