from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F, Count, Avg, Q
from django.core.cache import cache
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt 
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse, Http404
from django.contrib import messages
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
from .models import *
from .serializers import *

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
# PROPERTY VIEWSET - WITH PUBLIC ACCESS
# ============================================================
class PropertyViewSet(viewsets.ModelViewSet):
    """Main Property ViewSet with all features including image management and OWNER DATA"""
    queryset = Property.objects.filter(is_active=True)
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
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        if request.user.is_authenticated:
            from django.db.models import OuterRef, Subquery, Value, CharField
            
            user_interaction_subquery = PropertyInteraction.objects.filter(
                property=OuterRef('id'),
                user=request.user
            ).values('interaction_type')[:1]
            
            user_rating_subquery = PropertyRating.objects.filter(
                property=OuterRef('id'),
                user=request.user
            ).values('rating')[:1]
            
            queryset = queryset.annotate(
                user_interaction=Subquery(user_interaction_subquery, output_field=CharField()),
                user_rating=Subquery(user_rating_subquery, output_field=CharField())
            )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self._add_owner_data_to_serializer_data(serializer.data, request)
            return self.get_paginated_response(data)
        
        serializer = self.get_serializer(queryset, many=True)
        data = self._add_owner_data_to_serializer_data(serializer.data, request)
        return Response({
            'success': True,
            'properties': data,
            'count': len(data)
        })
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        if 'owner' not in data or data['owner'] is None:
            owner_data = None
            if instance.owner:
                owner_data = {
                    'id': instance.owner.id,
                    'username': instance.owner.username,
                    'first_name': instance.owner.first_name,
                    'last_name': instance.owner.last_name,
                    'full_name': instance.owner.get_full_name() or instance.owner.username,
                    'email': instance.owner.email,
                    'user_type': getattr(instance.owner, 'user_type', 'user'),
                }
            elif instance.company:
                owner_data = {
                    'id': instance.company.id,
                    'username': instance.company.company_name,
                    'first_name': instance.company.company_name,
                    'last_name': '',
                    'full_name': instance.company.company_name,
                    'email': getattr(instance.company, 'email', ''),
                    'user_type': 'business',
                }
            data['owner'] = owner_data
        
        instance.views_count = (instance.views_count or 0) + 1
        instance.save(update_fields=['views_count'])
        
        return Response(data)
    
    def _add_owner_data_to_serializer_data(self, serializer_data, request):
        result = []
        for item in serializer_data:
            property_id = item.get('id')
            
            try:
                property_obj = Property.objects.get(id=property_id)
            except Property.DoesNotExist:
                result.append(item)
                continue
            
            if 'owner' not in item or item['owner'] is None:
                owner_data = None
                if property_obj.owner:
                    owner_data = {
                        'id': property_obj.owner.id,
                        'username': property_obj.owner.username,
                        'first_name': property_obj.owner.first_name,
                        'last_name': property_obj.owner.last_name,
                        'full_name': property_obj.owner.get_full_name() or property_obj.owner.username,
                        'email': property_obj.owner.email,
                        'user_type': getattr(property_obj.owner, 'user_type', 'user'),
                    }
                elif property_obj.company:
                    owner_data = {
                        'id': property_obj.company.id,
                        'username': property_obj.company.company_name,
                        'first_name': property_obj.company.company_name,
                        'last_name': '',
                        'full_name': property_obj.company.company_name,
                        'email': getattr(property_obj.company, 'email', ''),
                        'user_type': 'business',
                    }
                item['owner'] = owner_data
            
            result.append(item)
        
        return result
    
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
# CUSTOM ENDPOINT FOR PROPERTIES WITH OWNER - PUBLIC ACCESS
# ============================================================
@api_view(['GET'])
@permission_classes([AllowAny])
def get_properties_with_owner(request):
    """Custom endpoint that returns properties with full owner data - PUBLIC ACCESS"""
    properties = Property.objects.filter(is_active=True)
    
    result = []
    for prop in properties:
        owner_data = None
        if prop.owner:
            owner_data = {
                'id': prop.owner.id,
                'username': prop.owner.username,
                'first_name': prop.owner.first_name,
                'last_name': prop.owner.last_name,
                'full_name': prop.owner.get_full_name() or prop.owner.username,
                'email': prop.owner.email,
                'user_type': getattr(prop.owner, 'user_type', 'user'),
            }
        
        result.append({
            'id': str(prop.id),
            'title': prop.title,
            'description': prop.description,
            'city': prop.city,
            'country': prop.country,
            'address': prop.address,
            'base_price': str(prop.base_price) if prop.base_price else '0',
            'price_currency': prop.price_currency,
            'listing_type': prop.listing_type,
            'status': prop.status,
            'is_featured': prop.is_featured,
            'is_premium': prop.is_premium,
            'is_bookable': prop.is_bookable,
            'bedrooms': prop.bedrooms,
            'bathrooms': prop.bathrooms,
            'garages': prop.garages,
            'parking_spaces': prop.parking_spaces,
            'total_area': str(prop.total_area) if prop.total_area else None,
            'main_image_url': prop.get_main_image_url(),
            'additional_images': prop.additional_images or [],
            'likes_count': prop.likes_count,
            'dislikes_count': prop.dislikes_count,
            'average_rating': float(prop.average_rating or 0),
            'rating_count': prop.rating_count,
            'owner': owner_data,
            'uploader_name': prop.owner.username if prop.owner else 'Unknown',
            'created_at': prop.created_at.isoformat(),
            'updated_at': prop.updated_at.isoformat(),
        })
    
    return Response({
        'success': True,
        'properties': result,
        'count': len(result)
    })


# ============================================================
# PROPERTY DETAIL VIEW - COMPLETE FIXED VERSION
# Add this to your existing views.py
# ============================================================
# views.py - Add this flexible version

def property_detail(request, pk):
    """Property detail page with agent profile integration"""
    # Use pk (not property_id)
    property_obj = get_object_or_404(Property, id=pk, is_active=True)
    # Track view (increment analytics)
    track_property_view(property_obj, request)
    
    # Get all rooms for this property
    rooms = property_obj.rooms.filter(is_active=True)
    total_rooms = rooms.count()
    available_rooms = rooms.filter(room_status='available').count()
    
    # Get bookings count
    total_bookings = property_obj.bookings.filter(
        status__in=['confirmed', 'checked_in', 'checked_out', 'completed']
    ).count()
    
    # Get total views from analytics
    total_views = 0
    if hasattr(property_obj, 'analytics'):
        total_views = property_obj.analytics.total_views
    
    # Get property features
    property_features = property_obj.features.filter(is_active=True)
    
    # Get property images
    property_images = []
    if property_obj.main_image:
        property_images.append(property_obj.main_image.url)
    if property_obj.additional_images:
        property_images.extend(property_obj.additional_images)
    
    # ============================================================
    # AGENT / OWNER PROFILE HANDLING - FULLY FIXED
    # ============================================================
    
    owner_name = None
    owner_badge = 'agent'
    agent_profile = None
    is_owner = False
    user_can_edit = False
    owner_user_id = None
    
    # Get the owner
    if property_obj.owner:
        owner_user = property_obj.owner
        owner_user_id = owner_user.id
        
        # Check if owner has an agent profile
        try:
            agent_profile = AgentProfile.objects.get(user=owner_user)
            owner_name = agent_profile.display_name or owner_user.username
            owner_badge = 'agent'
        except AgentProfile.DoesNotExist:
            agent_profile = None
            owner_name = owner_user.username
            owner_badge = 'owner'
        except Exception:
            agent_profile = None
            owner_name = owner_user.username
            owner_badge = 'owner'
        
        # Check if current user is the owner
        if request.user.is_authenticated:
            is_owner = (request.user.id == owner_user.id)
            user_can_edit = is_owner
    
    # If no owner, check if there's a listing agent
    if not owner_name and property_obj.listing_agent:
        try:
            agent_profile = AgentProfile.objects.get(user=property_obj.listing_agent)
            owner_name = agent_profile.display_name or property_obj.listing_agent.username
            owner_badge = 'agent'
            owner_user_id = property_obj.listing_agent.id
        except AgentProfile.DoesNotExist:
            owner_name = property_obj.listing_agent.username
            owner_badge = 'agent'
            owner_user_id = property_obj.listing_agent.id
        except Exception:
            owner_name = property_obj.listing_agent.username
            owner_badge = 'agent'
            owner_user_id = property_obj.listing_agent.id
    
    # If still no owner, check company
    if not owner_name and property_obj.company:
        owner_name = property_obj.company.company_name
        owner_badge = 'business'
    
    # Default fallback
    if not owner_name:
        owner_name = 'Unknown Agent'
        owner_badge = 'agent'
    
    # ============================================================
    # PROPERTY STATS FOR SIDEBAR
    # ============================================================
    
    # Get additional stats
    total_reviews = property_obj.reviews.filter(is_approved=True).count()
    average_rating = property_obj.reviews.filter(is_approved=True).aggregate(
        avg=Avg('overall_rating')
    )['avg'] or 0
    
    # Get wishlist count
    wishlist_count = property_obj.wishlists.count()
    
    # Get property interactions
    likes_count = property_obj.likes_count or 0
    
    # ============================================================
    # CONTEXT FOR TEMPLATE - ALL VARIABLES
    # ============================================================
    context = {
        # Property data
        'property': property_obj,
        'property_images': property_images,
        'property_features': property_features,
        'main_image': property_obj.main_image.url if property_obj.main_image else None,
        
        # Stats
        'total_rooms': total_rooms,
        'available_rooms': available_rooms,
        'total_bookings': total_bookings,
        'total_views': total_views,
        'total_reviews': total_reviews,
        'average_rating': average_rating,
        'wishlist_count': wishlist_count,
        'likes_count': likes_count,
        
        # Google Maps
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        
        # Agent/Owner data - ALL NEEDED FOR TEMPLATE
        'owner_name': owner_name,
        'owner_badge': owner_badge,
        'agent_profile': agent_profile,
        'is_owner': is_owner,
        'user_can_edit': user_can_edit,
        'owner_user_id': owner_user_id,
    }
    
    return render(request, 'hiring/property_detail.html', context)

# ============================================================
# TRACK PROPERTY VIEW - HELPER FUNCTION
# ============================================================

def track_property_view(property_obj, request):
    """Track property view for analytics"""
    try:
        # Get or create analytics
        analytics, created = PropertyAnalytics.objects.get_or_create(
            property=property_obj
        )
        
        # Increment total views
        analytics.total_views += 1
        
        # Track unique views (based on session)
        session_key = f'viewed_property_{property_obj.id}'
        if not request.session.get(session_key, False):
            analytics.unique_views += 1
            request.session[session_key] = True
        
        # Track views in last 30 days
        analytics.views_last_30_days += 1
        
        # Track device
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if 'mobile' in user_agent:
            analytics.views_by_device['mobile'] = analytics.views_by_device.get('mobile', 0) + 1
        elif 'tablet' in user_agent:
            analytics.views_by_device['tablet'] = analytics.views_by_device.get('tablet', 0) + 1
        else:
            analytics.views_by_device['desktop'] = analytics.views_by_device.get('desktop', 0) + 1
        
        analytics.save()
        
    except Exception as e:
        # Don't let analytics errors break the page
        logger.error(f"Error tracking view for property {property_obj.id}: {e}")
# ============================================================
# PUBLIC PROPERTY PAGE - NO LOGIN REQUIRED (HTML)
# ============================================================
def public_property_page(request, property_id):
    """PUBLIC property detail page - NO LOGIN REQUIRED"""
    try:
        property_obj = Property.objects.get(id=property_id, is_active=True)
    except Property.DoesNotExist:
        raise Http404("Property not found")
    
    main_image = property_obj.get_main_image_url()
    property_images = property_obj.additional_images or []
    if main_image and main_image not in property_images:
        property_images = [main_image] + property_images
    
    property_features = property_obj.features.all() if hasattr(property_obj, 'features') else []
    
    total_rooms = property_obj.rooms.filter(is_active=True).count()
    available_rooms = property_obj.rooms.filter(room_status='available', is_active=True).count()
    total_bookings = property_obj.bookings.filter(status='confirmed').count()
    total_views = property_obj.views_count or 0
    
    property_obj.views_count = (property_obj.views_count or 0) + 1
    property_obj.save(update_fields=['views_count'])
    
    context = {
        'property': property_obj,
        'main_image': main_image,
        'property_images': property_images[:4],
        'property_features': property_features,
        'total_rooms': total_rooms,
        'available_rooms': available_rooms,
        'total_bookings': total_bookings,
        'total_views': total_views,
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        'user': request.user,
    }
    
    return render(request, 'hiring/property_detail.html', context)


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
# MAINTENANCE VIEWSETS
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
        request_status = 'pending'
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
            property_id = request.data.get('property_id', None)
            
            if not property_id:
                default_property = Property.objects.filter(owner=user).first()
                if not default_property:
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
                status=request_status,
                location=location,
                estimated_cost=estimated_cost,
                preferred_date=preferred_date,
                notes=notes,
                tenant=user,
                property_id=property_id
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
# JOB VIEWSET
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


# ============================================================
# PROPERTY INTERACTIONS (Like/Dislike)
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_property_interaction(request, property_id):
    """Like, dislike, or remove interaction from a property"""
    try:
        property_obj = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return Response(
            {'error': 'Property not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    action = request.data.get('action', '')
    
    if action not in ['like', 'dislike', 'unlike', 'undislike']:
        return Response(
            {'error': 'Invalid action. Use like, dislike, unlike, or undislike'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = request.user
    
    if action in ['unlike', 'undislike']:
        interaction_type = 'like' if action == 'unlike' else 'dislike'
        
        deleted_count, _ = PropertyInteraction.objects.filter(
            property=property_obj,
            user=user,
            interaction_type=interaction_type
        ).delete()
        
        if deleted_count > 0:
            if interaction_type == 'like':
                property_obj.likes_count = max(0, property_obj.likes_count - deleted_count)
            else:
                property_obj.dislikes_count = max(0, property_obj.dislikes_count - deleted_count)
            property_obj.save(update_fields=['likes_count', 'dislikes_count'])
        
        return Response({
            'success': True,
            'action': action,
            'likes_count': property_obj.likes_count,
            'dislikes_count': property_obj.dislikes_count
        })
    
    interaction_type = 'like' if action == 'like' else 'dislike'
    opposite_type = 'dislike' if action == 'like' else 'like'
    
    PropertyInteraction.objects.filter(
        property=property_obj,
        user=user,
        interaction_type=opposite_type
    ).delete()
    
    existing = PropertyInteraction.objects.filter(
        property=property_obj,
        user=user,
        interaction_type=interaction_type
    ).first()
    
    if existing:
        existing.delete()
        if interaction_type == 'like':
            property_obj.likes_count = max(0, property_obj.likes_count - 1)
        else:
            property_obj.dislikes_count = max(0, property_obj.dislikes_count - 1)
        property_obj.save(update_fields=['likes_count', 'dislikes_count'])
        
        return Response({
            'success': True,
            'action': 'removed',
            'likes_count': property_obj.likes_count,
            'dislikes_count': property_obj.dislikes_count
        })
    
    PropertyInteraction.objects.create(
        property=property_obj,
        user=user,
        interaction_type=interaction_type
    )
    
    if interaction_type == 'like':
        property_obj.likes_count += 1
    else:
        property_obj.dislikes_count += 1
    property_obj.save(update_fields=['likes_count', 'dislikes_count'])
    
    return Response({
        'success': True,
        'action': action,
        'likes_count': property_obj.likes_count,
        'dislikes_count': property_obj.dislikes_count
    })


# ============================================================
# RATE PROPERTY
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_property(request, property_id):
    """Rate a property (1-5 stars)"""
    try:
        property_obj = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return Response(
            {'error': 'Property not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    rating_value = request.data.get('rating')
    
    if not rating_value:
        return Response(
            {'error': 'Rating is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        rating_value = int(rating_value)
        if rating_value < 1 or rating_value > 5:
            raise ValueError
    except:
        return Response(
            {'error': 'Rating must be between 1 and 5'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    review = request.data.get('review', '')
    
    rating, created = PropertyRating.objects.update_or_create(
        property=property_obj,
        user=request.user,
        defaults={
            'rating': rating_value,
            'review': review
        }
    )
    
    ratings = PropertyRating.objects.filter(property=property_obj)
    count = ratings.count()
    
    if count > 0:
        avg = ratings.aggregate(avg=Avg('rating'))['avg'] or 0
        property_obj.average_rating = round(avg, 2)
    else:
        property_obj.average_rating = 0
    
    property_obj.rating_count = count
    property_obj.save(update_fields=['average_rating', 'rating_count'])
    
    cache.delete(f'rating_summary_{property_obj.id}')
    
    return Response({
        'success': True,
        'created': created,
        'rating': rating_value,
        'average_rating': property_obj.average_rating,
        'rating_count': property_obj.rating_count
    })


# ============================================================
# GET PROPERTY RATINGS
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_property_ratings(request, property_id):
    """Get all ratings for a property with pagination"""
    try:
        property_obj = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return Response(
            {'error': 'Property not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    
    ratings = PropertyRating.objects.filter(
        property=property_obj
    ).select_related('user').order_by('-created_at')
    
    total = ratings.count()
    paginated_ratings = ratings[start:end]
    
    serializer = PropertyRatingSerializer(paginated_ratings, many=True)
    
    return Response({
        'success': True,
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
        'ratings': serializer.data,
        'average': property_obj.average_rating or 0,
        'rating_count': property_obj.rating_count or 0
    })


# ============================================================
# GET RATING SUMMARY (Cached)
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_property_rating_summary(request, property_id):
    """Get rating summary for a property (cached for performance)"""
    try:
        property_obj = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return Response(
            {'error': 'Property not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    cache_key = f'rating_summary_{property_obj.id}'
    response_data = cache.get(cache_key)
    
    if response_data is None:
        user_rating = None
        if request.user.is_authenticated:
            user_rating = PropertyRating.objects.filter(
                property=property_obj,
                user=request.user
            ).values_list('rating', flat=True).first()
        
        distribution = get_rating_distribution(property_obj)
        
        response_data = {
            'average': float(property_obj.average_rating or 0.0),
            'count': property_obj.rating_count or 0,
            'distribution': distribution,
            'user_rating': user_rating
        }
        
        cache.set(cache_key, response_data, 300)
    
    return Response(response_data)


# ============================================================
# GET RATING DISTRIBUTION (Helper)
# ============================================================

def get_rating_distribution(property_obj):
    """Get rating distribution (how many 1-star, 2-star, etc.)"""
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    
    ratings = PropertyRating.objects.filter(property=property_obj)
    total = ratings.count()
    
    if total == 0:
        return distribution
    
    grouped = ratings.values('rating').annotate(count=Count('id'))
    
    for item in grouped:
        rating = item['rating']
        count = item['count']
        if rating in distribution:
            distribution[rating] = count
    
    for key in distribution:
        distribution[key] = round((distribution[key] / total) * 100, 1)
    
    return distribution


# ============================================================
# BATCH INTERACTION
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_property_interaction(request):
    """Batch like/dislike multiple properties at once"""
    property_ids = request.data.get('ids', [])
    action = request.data.get('action', '')
    
    if not property_ids:
        return Response(
            {'error': 'Property IDs required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if action not in ['like', 'dislike', 'unlike', 'undislike']:
        return Response(
            {'error': 'Invalid action'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = request.user
    
    properties = Property.objects.filter(id__in=property_ids, is_active=True)
    property_ids_found = list(properties.values_list('id', flat=True))
    
    if action in ['unlike', 'undislike']:
        interaction_type = 'like' if action == 'unlike' else 'dislike'
        
        deleted_count, _ = PropertyInteraction.objects.filter(
            property__in=properties,
            user=user,
            interaction_type=interaction_type
        ).delete()
        
        if deleted_count > 0:
            update_field = 'likes_count' if interaction_type == 'like' else 'dislikes_count'
            Property.objects.filter(id__in=property_ids_found).update(
                **{update_field: F(update_field) - 1}
            )
        
    else:
        interaction_type = 'like' if action == 'like' else 'dislike'
        opposite_type = 'dislike' if action == 'like' else 'like'
        
        PropertyInteraction.objects.filter(
            property__in=properties,
            user=user,
            interaction_type=opposite_type
        ).delete()
        
        existing = PropertyInteraction.objects.filter(
            property__in=properties,
            user=user,
            interaction_type=interaction_type
        ).values_list('property_id', flat=True)
        
        new_property_ids = [pid for pid in property_ids_found if pid not in existing]
        
        if new_property_ids:
            interactions_to_create = [
                PropertyInteraction(
                    property_id=pid,
                    user=user,
                    interaction_type=interaction_type
                )
                for pid in new_property_ids
            ]
            PropertyInteraction.objects.bulk_create(interactions_to_create)
            
            update_field = f'{interaction_type}s_count'
            Property.objects.filter(id__in=new_property_ids).update(
                **{update_field: F(update_field) + 1}
            )
    
    updated_properties = Property.objects.filter(id__in=property_ids_found)
    results = []
    for p in updated_properties:
        results.append({
            'id': str(p.id),
            'likes_count': p.likes_count,
            'dislikes_count': p.dislikes_count
        })
    
    return Response({
        'success': True,
        'action': action,
        'count': len(results),
        'results': results
    })


# ============================================================
# GET USER'S INTERACTIONS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_property_interactions(request):
    """Get all properties the user has liked or disliked"""
    user = request.user
    interaction_type = request.query_params.get('type')
    
    queryset = PropertyInteraction.objects.filter(user=user).select_related('property')
    
    if interaction_type in ['like', 'dislike']:
        queryset = queryset.filter(interaction_type=interaction_type)
    
    serializer = PropertyInteractionSerializer(queryset, many=True)
    
    return Response({
        'success': True,
        'count': queryset.count(),
        'interactions': serializer.data
    })


# ============================================================
# ADVANCED SEARCH
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def advanced_property_search(request):
    """Advanced search for properties with filters"""
    queryset = Property.objects.filter(is_active=True)
    
    query = request.query_params.get('q', '').strip()
    property_type = request.query_params.get('property_type', '')
    listing_type = request.query_params.get('listing_type', '')
    status = request.query_params.get('status', '')
    city = request.query_params.get('city', '')
    country = request.query_params.get('country', '')
    min_price = request.query_params.get('min_price', '')
    max_price = request.query_params.get('max_price', '')
    min_bedrooms = request.query_params.get('min_bedrooms', '')
    max_bedrooms = request.query_params.get('max_bedrooms', '')
    min_bathrooms = request.query_params.get('min_bathrooms', '')
    max_bathrooms = request.query_params.get('max_bathrooms', '')
    min_area = request.query_params.get('min_area', '')
    max_area = request.query_params.get('max_area', '')
    sort_by = request.query_params.get('sort_by', 'created_at')
    sort_order = request.query_params.get('sort_order', 'desc')
    is_featured = request.query_params.get('is_featured', '').lower() == 'true'
    is_premium = request.query_params.get('is_premium', '').lower() == 'true'
    
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(address__icontains=query) |
            Q(city__icontains=query) |
            Q(country__icontains=query) |
            Q(property_reference__icontains=query)
        )
    
    if property_type:
        queryset = queryset.filter(property_type_id=property_type)
    
    if listing_type:
        queryset = queryset.filter(listing_type=listing_type)
    
    if status:
        queryset = queryset.filter(status=status)
    
    if city:
        queryset = queryset.filter(city__icontains=city)
    
    if country:
        queryset = queryset.filter(country__icontains=country)
    
    if min_price:
        queryset = queryset.filter(base_price__gte=min_price)
    
    if max_price:
        queryset = queryset.filter(base_price__lte=max_price)
    
    if min_bedrooms:
        queryset = queryset.filter(bedrooms__gte=min_bedrooms)
    
    if max_bedrooms:
        queryset = queryset.filter(bedrooms__lte=max_bedrooms)
    
    if min_bathrooms:
        queryset = queryset.filter(bathrooms__gte=min_bathrooms)
    
    if max_bathrooms:
        queryset = queryset.filter(bathrooms__lte=max_bathrooms)
    
    if min_area:
        queryset = queryset.filter(total_area__gte=min_area)
    
    if max_area:
        queryset = queryset.filter(total_area__lte=max_area)
    
    if is_featured:
        queryset = queryset.filter(is_featured=True)
    
    if is_premium:
        queryset = queryset.filter(is_premium=True)
    
    valid_sort_fields = [
        'created_at', 'updated_at', 'base_price', 'bedrooms', 
        'bathrooms', 'average_rating', 'likes_count', 'views_count'
    ]
    if sort_by not in valid_sort_fields:
        sort_by = 'created_at'
    
    if sort_order == 'desc':
        sort_field = f'-{sort_by}'
    else:
        sort_field = sort_by
    
    queryset = queryset.order_by(sort_field)
    
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    
    total = queryset.count()
    results = queryset[start:end]
    
    serializer = PropertyListSerializer(results, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
        'results': serializer.data
    })


# ============================================================
# BOOKING DETAIL VIEW
# ============================================================

def booking_detail_view(request, pk):
    """View for booking detail page"""
    from django.shortcuts import render, get_object_or_404
    booking = get_object_or_404(Booking, id=pk, guest=request.user)
    
    context = {
        'booking': booking,
        'property': booking.property,
    }
    return render(request, 'hiring/booking_detail.html', context)


# ============================================================
# SHARE ENDPOINTS - PUBLIC ACCESS
# ============================================================

@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def share_property(request, property_id):
    """Share a property - returns share data"""
    try:
        property_obj = get_object_or_404(Property, id=property_id, is_active=True)
        
        share_data = {
            'success': True,
            'title': property_obj.title,
            'description': property_obj.description[:200] if property_obj.description else '',
            'url': f"/properties/{property_obj.id}/",
            'image': property_obj.get_main_image_url(),
            'price': f"{property_obj.price_currency} {property_obj.base_price}" if property_obj.base_price else None,
            'location': f"{property_obj.city}, {property_obj.country}" if property_obj.city else '',
            'type': 'property',
            'id': str(property_obj.id)
        }
        
        property_obj.shares_count = (getattr(property_obj, 'shares_count', 0) + 1)
        property_obj.save(update_fields=['shares_count'])
        
        return JsonResponse(share_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def share_post(request, post_id):
    """Share a post"""
    try:
        post_obj = get_object_or_404(Post, id=post_id, is_published=True)
        
        share_data = {
            'success': True,
            'title': post_obj.title or 'Post',
            'description': post_obj.content[:200] if post_obj.content else '',
            'url': f"/post/{post_obj.id}/",
            'image': post_obj.image.url if post_obj.image else None,
            'type': 'post',
            'id': str(post_obj.id),
            'author': post_obj.author.username if post_obj.author else 'Unknown'
        }
        
        post_obj.shares = (post_obj.shares or 0) + 1
        post_obj.save(update_fields=['shares'])
        
        return JsonResponse(share_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def share_job(request, job_id):
    """Share a job listing"""
    try:
        job_obj = get_object_or_404(JobListing, id=job_id)
        
        share_data = {
            'success': True,
            'title': job_obj.title,
            'description': job_obj.position_summary[:200] if job_obj.position_summary else '',
            'url': f"/jobs/{job_obj.id}/",
            'company': job_obj.company_name,
            'location': job_obj.location,
            'type': 'job',
            'id': str(job_obj.id)
        }
        
        return JsonResponse(share_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def share_education(request, type, item_id):
    """Share education content"""
    try:
        from education.models import Bursary, University, School, QuestionPaper
        
        share_data = {
            'success': True,
            'type': type,
            'id': str(item_id)
        }
        
        if type == 'bursary':
            item = get_object_or_404(Bursary, id=item_id, is_active=True)
            share_data['title'] = item.title
            share_data['description'] = item.description[:200] if item.description else ''
            share_data['url'] = f"/education/bursary/{item.id}/"
            share_data['provider'] = item.provider
            share_data['amount'] = item.amount
            
        elif type == 'university':
            item = get_object_or_404(University, id=item_id, is_active=True)
            share_data['title'] = item.name
            share_data['description'] = item.description[:200] if item.description else ''
            share_data['url'] = f"/education/university/{item.id}/"
            share_data['location'] = f"{item.city}, {item.province}" if item.city else ''
            
        elif type == 'school':
            item = get_object_or_404(School, id=item_id, is_active=True)
            share_data['title'] = item.name
            share_data['description'] = item.address[:200] if item.address else ''
            share_data['url'] = f"/education/school/{item.id}/"
            share_data['location'] = f"{item.city}, {item.province}" if item.city else ''
            
        elif type == 'paper':
            item = get_object_or_404(QuestionPaper, id=item_id)
            share_data['title'] = item.title
            share_data['description'] = f"{item.grade.name} - {item.subject.name}" if item.grade and item.subject else ''
            share_data['url'] = f"/education/paper/{item.id}/"
            share_data['year'] = item.year
            
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid education type'
            }, status=400)
        
        return JsonResponse(share_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================================
# AGENT PROFILE CREATE/EDIT VIEWS (HTML)
# ============================================================
# ============================================================
# AGENT PROFILE CREATE - FULLY FIXED
# ============================================================

def agent_profile_create(request):
    """
    Create agent profile page - Only accessible by property owners
    """
    # Check if user is logged in
    if not request.user.is_authenticated:
        messages.warning(request, 'Please login first.')
        return redirect('/login/')
    
    # Check if user already has an agent profile
    if AgentProfile.objects.filter(user=request.user).exists():
        messages.info(request, 'You already have an agent profile.')
        return redirect('agent_profile_edit', agent_id=request.user.agent_profile.id)
    
    # Check if user owns any properties
    if not Property.objects.filter(owner=request.user, is_active=True).exists():
        messages.warning(request, 'You need to own at least one property before creating an agent profile.')
        return redirect('properties_manage')
    
    if request.method == 'POST':
        try:
            # IMPORTANT: Use request.POST directly - NOT request.POST.dict()
            files_data = request.FILES
            
            # Create agent profile - using request.POST.get() for all fields
            agent = AgentProfile(
                user=request.user,
                display_name=request.POST.get('display_name', '').strip(),
                agent_type=request.POST.get('agent_type', 'independent'),
                custom_agent_type=request.POST.get('custom_agent_type', '').strip(),
                agency_name=request.POST.get('agency_name', '').strip(),
                phone_primary=request.POST.get('phone_primary', '').strip(),
                phone_secondary=request.POST.get('phone_secondary', '').strip(),
                email_primary=request.POST.get('email_primary', '').strip(),
                email_secondary=request.POST.get('email_secondary', '').strip(),
                website=request.POST.get('website', '').strip(),
                business_address=request.POST.get('business_address', '').strip(),
                city=request.POST.get('city', '').strip(),
                state_province=request.POST.get('state_province', '').strip(),
                postal_code=request.POST.get('postal_code', '').strip(),
                # Social Media
                whatsapp_number=request.POST.get('whatsapp_number', '').strip(),
                telegram_username=request.POST.get('telegram_username', '').strip(),
                linkedin_url=request.POST.get('linkedin_url', '').strip(),
                twitter_url=request.POST.get('twitter_url', '').strip(),
                facebook_url=request.POST.get('facebook_url', '').strip(),
                instagram_url=request.POST.get('instagram_url', '').strip(),
                youtube_url=request.POST.get('youtube_url', '').strip(),
                tiktok_url=request.POST.get('tiktok_url', '').strip(),
                property24_url=request.POST.get('property24_url', '').strip(),
                privateproperty_url=request.POST.get('privateproperty_url', '').strip(),
                signal_number=request.POST.get('signal_number', '').strip(),
                viber_number=request.POST.get('viber_number', '').strip(),
                wechat_id=request.POST.get('wechat_id', '').strip(),
                line_id=request.POST.get('line_id', '').strip(),
                kakao_id=request.POST.get('kakao_id', '').strip(),
                # Specializations - getlist() works on QueryDict
                specializations=request.POST.getlist('specializations', []),
                custom_specializations=request.POST.get('custom_specializations', '').strip(),
                # Bio
                bio=request.POST.get('bio', '').strip(),
                achievements=request.POST.get('achievements', '').strip(),
                services_offered=request.POST.get('services_offered', '').strip(),
                areas_served=request.POST.get('areas_served', '').strip(),
                # License
                license_number=request.POST.get('license_number', '').strip(),
                years_experience=int(request.POST.get('years_experience', 0) or 0),
                # Settings - Checkboxes return 'on' when checked
                show_social_links=request.POST.get('show_social_links', '') == 'on',
                show_contact_details=request.POST.get('show_contact_details', '') == 'on',
                auto_accept_messages=request.POST.get('auto_accept_messages', '') == 'on',
                receive_notifications=request.POST.get('receive_notifications', '') == 'on',
            )
            
            # Handle profile image
            if 'profile_image' in files_data and files_data['profile_image']:
                agent.profile_image = files_data['profile_image']
            
            # Clean phone numbers
            if agent.phone_primary:
                agent.phone_primary = agent.clean_phone_number(agent.phone_primary) or agent.phone_primary
            if agent.phone_secondary:
                agent.phone_secondary = agent.clean_phone_number(agent.phone_secondary) or agent.phone_secondary
            if agent.whatsapp_number:
                agent.whatsapp_number = agent.clean_phone_number(agent.whatsapp_number) or agent.whatsapp_number
            
            # Detect country from phone
            if agent.phone_primary:
                country = Country.detect_country(agent.phone_primary)
                if country:
                    agent.country = country
            
            agent.save()
            
            messages.success(request, 'Agent profile created successfully!')
            
            # Redirect to the property that triggered this
            property_id = request.GET.get('property_id')
            if property_id:
                return redirect('property_detail', pk=property_id)
            return redirect('agent_profile_view', agent_id=agent.id)
            
        except Exception as e:
            messages.error(request, f'Error creating agent profile: {str(e)}')
            # Log the error for debugging
            import traceback
            print(traceback.format_exc())
            return redirect('agent_profile_create')
    
    # GET request - show form
    context = {
        'agent': None,
        'property_id': request.GET.get('property_id'),
        'is_edit': False,
        'form': {}
    }
    return render(request, 'hiring/agent_profile_form.html', context)


# ============================================================
# AGENT PROFILE EDIT - FULLY FIXED
# ============================================================

def agent_profile_edit(request, agent_id):
    """
    Edit agent profile page
    """
    # Check if user is logged in
    if not request.user.is_authenticated:
        messages.warning(request, 'Please login first.')
        return redirect('/login/')
    
    try:
        agent = AgentProfile.objects.get(id=agent_id, user=request.user)
    except AgentProfile.DoesNotExist:
        messages.error(request, 'Agent profile not found or you do not have permission to edit it.')
        return redirect('properties_manage')
    
    if request.method == 'POST':
        try:
            files_data = request.FILES
            
            # Update all fields using request.POST directly
            agent.display_name = request.POST.get('display_name', '').strip()
            agent.agent_type = request.POST.get('agent_type', 'independent')
            agent.custom_agent_type = request.POST.get('custom_agent_type', '').strip()
            agent.agency_name = request.POST.get('agency_name', '').strip()
            agent.phone_primary = request.POST.get('phone_primary', '').strip()
            agent.phone_secondary = request.POST.get('phone_secondary', '').strip()
            agent.email_primary = request.POST.get('email_primary', '').strip()
            agent.email_secondary = request.POST.get('email_secondary', '').strip()
            agent.website = request.POST.get('website', '').strip()
            agent.business_address = request.POST.get('business_address', '').strip()
            agent.city = request.POST.get('city', '').strip()
            agent.state_province = request.POST.get('state_province', '').strip()
            agent.postal_code = request.POST.get('postal_code', '').strip()
            
            # Social Media
            agent.whatsapp_number = request.POST.get('whatsapp_number', '').strip()
            agent.telegram_username = request.POST.get('telegram_username', '').strip()
            agent.linkedin_url = request.POST.get('linkedin_url', '').strip()
            agent.twitter_url = request.POST.get('twitter_url', '').strip()
            agent.facebook_url = request.POST.get('facebook_url', '').strip()
            agent.instagram_url = request.POST.get('instagram_url', '').strip()
            agent.youtube_url = request.POST.get('youtube_url', '').strip()
            agent.tiktok_url = request.POST.get('tiktok_url', '').strip()
            agent.property24_url = request.POST.get('property24_url', '').strip()
            agent.privateproperty_url = request.POST.get('privateproperty_url', '').strip()
            agent.signal_number = request.POST.get('signal_number', '').strip()
            agent.viber_number = request.POST.get('viber_number', '').strip()
            agent.wechat_id = request.POST.get('wechat_id', '').strip()
            agent.line_id = request.POST.get('line_id', '').strip()
            agent.kakao_id = request.POST.get('kakao_id', '').strip()
            
            # Specializations - getlist() works on QueryDict
            agent.specializations = request.POST.getlist('specializations', [])
            agent.custom_specializations = request.POST.get('custom_specializations', '').strip()
            
            # Bio
            agent.bio = request.POST.get('bio', '').strip()
            agent.achievements = request.POST.get('achievements', '').strip()
            agent.services_offered = request.POST.get('services_offered', '').strip()
            agent.areas_served = request.POST.get('areas_served', '').strip()
            
            # License
            agent.license_number = request.POST.get('license_number', '').strip()
            agent.years_experience = int(request.POST.get('years_experience', 0) or 0)
            
            # Settings
            agent.show_social_links = request.POST.get('show_social_links', '') == 'on'
            agent.show_contact_details = request.POST.get('show_contact_details', '') == 'on'
            agent.auto_accept_messages = request.POST.get('auto_accept_messages', '') == 'on'
            agent.receive_notifications = request.POST.get('receive_notifications', '') == 'on'
            
            # Handle profile image
            if 'profile_image' in files_data and files_data['profile_image']:
                if agent.profile_image:
                    try:
                        agent.profile_image.delete(save=False)
                    except:
                        pass
                agent.profile_image = files_data['profile_image']
            
            # Clean phone numbers
            if agent.phone_primary:
                agent.phone_primary = agent.clean_phone_number(agent.phone_primary) or agent.phone_primary
            if agent.phone_secondary:
                agent.phone_secondary = agent.clean_phone_number(agent.phone_secondary) or agent.phone_secondary
            if agent.whatsapp_number:
                agent.whatsapp_number = agent.clean_phone_number(agent.whatsapp_number) or agent.whatsapp_number
            
            # Detect country from phone
            if agent.phone_primary:
                country = Country.detect_country(agent.phone_primary)
                if country:
                    agent.country = country
            
            agent.save()
            
            messages.success(request, 'Agent profile updated successfully!')
            
            # Redirect to the property that triggered this
            property_id = request.GET.get('property_id')
            if property_id:
                return redirect('property_detail', pk=property_id)
            return redirect('agent_profile_view', agent_id=agent.id)
            
        except Exception as e:
            messages.error(request, f'Error updating agent profile: {str(e)}')
            import traceback
            print(traceback.format_exc())
    
    # GET request - show form with existing data
    context = {
        'agent': agent,
        'property_id': request.GET.get('property_id'),
        'is_edit': True,
        'form': {
            'display_name': agent.display_name,
            'agent_type': agent.agent_type,
            'custom_agent_type': agent.custom_agent_type,
            'agency_name': agent.agency_name,
            'phone_primary': agent.phone_primary,
            'phone_secondary': agent.phone_secondary,
            'email_primary': agent.email_primary,
            'email_secondary': agent.email_secondary,
            'website': agent.website,
            'business_address': agent.business_address,
            'city': agent.city,
            'state_province': agent.state_province,
            'postal_code': agent.postal_code,
            'whatsapp_number': agent.whatsapp_number,
            'telegram_username': agent.telegram_username,
            'linkedin_url': agent.linkedin_url,
            'twitter_url': agent.twitter_url,
            'facebook_url': agent.facebook_url,
            'instagram_url': agent.instagram_url,
            'youtube_url': agent.youtube_url,
            'tiktok_url': agent.tiktok_url,
            'property24_url': agent.property24_url,
            'privateproperty_url': agent.privateproperty_url,
            'signal_number': agent.signal_number,
            'viber_number': agent.viber_number,
            'wechat_id': agent.wechat_id,
            'line_id': agent.line_id,
            'kakao_id': agent.kakao_id,
            'specializations': agent.specializations or [],
            'custom_specializations': agent.custom_specializations,
            'bio': agent.bio,
            'achievements': agent.achievements,
            'services_offered': agent.services_offered,
            'areas_served': agent.areas_served,
            'license_number': agent.license_number,
            'years_experience': agent.years_experience,
            'show_social_links': agent.show_social_links,
            'show_contact_details': agent.show_contact_details,
            'auto_accept_messages': agent.auto_accept_messages,
            'receive_notifications': agent.receive_notifications,
        }
    }
    return render(request, 'hiring/agent_profile_form.html', context)



def agent_profile_view(request, agent_id):
    """
    View agent profile page (public)
    """
    try:
        agent = AgentProfile.objects.get(id=agent_id)
    except AgentProfile.DoesNotExist:
        raise Http404("Agent profile not found")
    
    # Get properties by this agent
    properties = Property.objects.filter(
        owner=agent.user,
        is_active=True
    ).order_by('-created_at')[:6]
    
    # Get reviews
    reviews = AgentReview.objects.filter(
        agent=agent,
        is_public=True,
        is_approved=True
    ).order_by('-created_at')[:10]
    
    context = {
        'agent': agent,
        'properties': properties,
        'reviews': reviews,
        'is_owner': request.user.is_authenticated and agent.user == request.user,
    }
    return render(request, 'hiring/agent_profile.html', context)


# ============================================================
# AGENT PROFILE VIEWSET
# ============================================================
class AgentProfileViewSet(viewsets.ModelViewSet):
    """Complete Agent Profile ViewSet with social media and internal messaging"""
    
    queryset = AgentProfile.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'agent_type', 'is_verified', 'is_featured', 'is_online',
        'city', 'state_province', 'country'
    ]
    search_fields = [
        'display_name', 'agency_name', 'bio', 'city', 
        'state_province', 'custom_agent_type', 'custom_specializations'
    ]
    ordering_fields = [
        'average_rating', 'total_reviews', 'total_deals', 
        'years_experience', 'created_at', 'properties_sold'
    ]
    ordering = ['-is_featured', '-average_rating', '-total_deals']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AgentProfileListSerializer
        elif self.action == 'retrieve':
            return AgentProfileDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return AgentProfileSerializer
        return AgentProfileSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        if AgentProfile.objects.filter(user=self.request.user).exists():
            return Response({
                'success': False,
                'error': 'You already have an agent profile'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from hiring.models import BusinessProfile
            business = BusinessProfile.objects.get(user=self.request.user)
            if not serializer.validated_data.get('agency_name'):
                serializer.save(
                    user=self.request.user,
                    agency_name=business.company_name
                )
            else:
                serializer.save(user=self.request.user)
        except:
            serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        instance = self.get_object()
        
        # Clean phone numbers
        if 'phone_primary' in serializer.validated_data:
            serializer.validated_data['phone_primary'] = instance.clean_phone_number(
                serializer.validated_data['phone_primary']
            ) or serializer.validated_data['phone_primary']
        
        if 'phone_secondary' in serializer.validated_data:
            serializer.validated_data['phone_secondary'] = instance.clean_phone_number(
                serializer.validated_data['phone_secondary']
            ) or serializer.validated_data['phone_secondary']
        
        if 'whatsapp_number' in serializer.validated_data:
            serializer.validated_data['whatsapp_number'] = instance.clean_phone_number(
                serializer.validated_data['whatsapp_number']
            ) or serializer.validated_data['whatsapp_number']
        
        if 'signal_number' in serializer.validated_data:
            serializer.validated_data['signal_number'] = instance.clean_phone_number(
                serializer.validated_data['signal_number']
            ) or serializer.validated_data['signal_number']
        
        if 'viber_number' in serializer.validated_data:
            serializer.validated_data['viber_number'] = instance.clean_phone_number(
                serializer.validated_data['viber_number']
            ) or serializer.validated_data['viber_number']
        
        # Clean URLs
        url_fields = [
            'website', 'linkedin_url', 'twitter_url', 'facebook_url', 
            'instagram_url', 'youtube_url', 'tiktok_url', 'pinterest_url',
            'snapchat_url', 'reddit_url',
            'zillow_url', 'realtor_url', 'trulia_url', 'redfin_url', 'homescom_url',
            'rightmove_url', 'zoopla_url', 'onthemarket_url', 'primelocation_url',
            'property24_url', 'privateproperty_url',
            'realestatecomau_url', 'domaincomau_url',
            'propertyfinder_url', 'bayut_url', 'dubizzle_url',
            'propertyguru_url', 'rumah123_url', 'ninety_nine_co_url',
            'vivareal_url', 'properati_url',
            'indeed_url', 'glassdoor_url', 'angellist_url', 'crunchbase_url'
        ]
        
        for field in url_fields:
            if field in serializer.validated_data:
                serializer.validated_data[field] = instance.clean_url(
                    serializer.validated_data[field]
                ) or serializer.validated_data[field]
        
        # Clean Telegram username
        if 'telegram_username' in serializer.validated_data:
            username = serializer.validated_data['telegram_username'].strip()
            if username.startswith('@'):
                username = username[1:]
            serializer.validated_data['telegram_username'] = username
        
        # Clean LINE ID
        if 'line_id' in serializer.validated_data:
            line_id = serializer.validated_data['line_id'].strip()
            if line_id.startswith('@'):
                line_id = line_id[1:]
            serializer.validated_data['line_id'] = line_id
        
        # Detect country from phone
        if not serializer.validated_data.get('country') and serializer.validated_data.get('phone_primary'):
            country = instance.detect_country_from_number(
                serializer.validated_data['phone_primary']
            )
            if country:
                serializer.validated_data['country'] = country
        
        serializer.save()
    
    @action(detail=True, methods=['get'])
    def social_links(self, request, pk=None):
        agent = self.get_object()
        return Response({
            'success': True,
            'social_links': agent.get_active_social_links(),
            'contact_methods': agent.get_contact_methods(),
            'whatsapp_link': agent.get_whatsapp_link(),
            'telegram_link': agent.get_telegram_link(),
            'signal_link': agent.get_signal_link(),
            'viber_link': agent.get_viber_link(),
            'line_link': agent.get_line_link(),
            'kakao_link': agent.get_kakao_link(),
            'phone_display': agent.get_phone_display(),
            'detected_country': CountrySerializer(
                agent.detect_country_from_number(agent.phone_primary)
            ).data if agent.phone_primary else None
        })
    
    @action(detail=True, methods=['get'])
    def contact_methods(self, request, pk=None):
        agent = self.get_object()
        methods = agent.get_contact_methods()
        detected_country = None
        if agent.phone_primary:
            detected_country = agent.detect_country_from_number(agent.phone_primary)
        
        return Response({
            'success': True,
            'agent_id': str(agent.id),
            'agent_name': agent.display_name or agent.user.username,
            'contact_methods': methods,
            'internal_messaging_available': bool(agent.user and agent.user.id),
            'detected_country': CountrySerializer(detected_country).data if detected_country else None,
            'phone_formatted': agent.get_phone_display()
        })
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        agent = self.get_object()
        platform = request.data.get('platform')
        property_id = request.data.get('property_id')
        
        if not platform:
            return Response({
                'success': False,
                'error': 'Platform is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        valid_platforms = ['whatsapp', 'facebook', 'twitter', 'linkedin', 
                          'instagram', 'tiktok', 'youtube', 'telegram', 
                          'signal', 'viber', 'wechat', 'line', 'email', 'copy', 'other']
        if platform not in valid_platforms:
            return Response({
                'success': False,
                'error': f'Invalid platform. Must be one of: {", ".join(valid_platforms)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        property_obj = None
        if property_id:
            try:
                property_obj = Property.objects.get(id=property_id, is_active=True)
            except Property.DoesNotExist:
                pass
        
        share = AgentSocialShare.objects.create(
            agent=agent,
            property=property_obj,
            platform=platform,
            shared_by=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            country=agent.country
        )
        
        return Response({
            'success': True,
            'message': f'Share tracked on {platform}',
            'share_id': str(share.id),
            'platform': platform
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def add_review(self, request, pk=None):
        agent = self.get_object()
        user = request.user
        
        if not user.is_authenticated:
            return Response({
                'success': False,
                'error': 'You must be logged in to leave a review'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if AgentReview.objects.filter(agent=agent, user=user).exists():
            return Response({
                'success': False,
                'error': 'You have already reviewed this agent'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        rating = request.data.get('rating')
        if not rating:
            return Response({
                'success': False,
                'error': 'Rating is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except:
            return Response({
                'success': False,
                'error': 'Rating must be between 1 and 5'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        property_obj = None
        property_id = request.data.get('property_id')
        if property_id:
            try:
                property_obj = Property.objects.get(id=property_id, is_active=True)
            except Property.DoesNotExist:
                pass
        
        review = AgentReview.objects.create(
            agent=agent,
            user=user,
            rating=rating,
            professionalism=request.data.get('professionalism'),
            communication=request.data.get('communication'),
            knowledge=request.data.get('knowledge'),
            responsiveness=request.data.get('responsiveness'),
            negotiation=request.data.get('negotiation'),
            review_text=request.data.get('review_text', ''),
            review_title=request.data.get('review_title', ''),
            property=property_obj,
            is_verified=False
        )
        
        reviews = AgentReview.objects.filter(agent=agent)
        avg = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        agent.average_rating = round(avg, 2)
        agent.total_reviews = reviews.count()
        agent.save(update_fields=['average_rating', 'total_reviews'])
        
        cache.delete(f'agent_rating_{agent.id}')
        
        return Response({
            'success': True,
            'message': 'Review added successfully',
            'review': AgentReviewSerializer(review, context={'request': request}).data,
            'average_rating': agent.average_rating,
            'total_reviews': agent.total_reviews
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def connect(self, request, pk=None):
        agent = self.get_object()
        user = request.user
        
        if not user.is_authenticated:
            return Response({
                'success': False,
                'error': 'You must be logged in to connect with an agent'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        connection_type = request.data.get('connection_type', 'follower')
        valid_types = ['follower', 'saved', 'client', 'past_client', 'referral', 'collaborator']
        if connection_type not in valid_types:
            return Response({
                'success': False,
                'error': f'Invalid connection type. Must be one of: {", ".join(valid_types)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if agent.user == user:
            return Response({
                'success': False,
                'error': 'You cannot connect with yourself'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        connection, created = AgentConnection.objects.get_or_create(
            agent=agent,
            user=user,
            defaults={'connection_type': connection_type}
        )
        
        if not created:
            connection.connection_type = connection_type
            connection.notes = request.data.get('notes', connection.notes)
            connection.save()
        
        return Response({
            'success': True,
            'message': f'Successfully {connection_type}d {agent.display_name or agent.user.username}',
            'connection_type': connection.connection_type,
            'is_connected': True,
            'created': created
        })
    
    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        agent = self.get_object()
        user = request.user
        
        if not user.is_authenticated:
            return Response({
                'success': False,
                'error': 'You must be logged in to disconnect'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        deleted_count, _ = AgentConnection.objects.filter(
            agent=agent,
            user=user
        ).delete()
        
        if deleted_count > 0:
            return Response({
                'success': True,
                'message': f'Successfully disconnected from {agent.display_name or agent.user.username}',
                'is_connected': False
            })
        else:
            return Response({
                'success': False,
                'error': 'You are not connected to this agent'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        agent = self.get_object()
        
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        sort = request.query_params.get('sort', '-created_at')
        
        reviews = AgentReview.objects.filter(
            agent=agent,
            is_public=True,
            is_approved=True
        ).order_by(sort)
        
        total = reviews.count()
        start = (page - 1) * page_size
        end = start + page_size
        paginated_reviews = reviews[start:end]
        
        serializer = AgentReviewSerializer(paginated_reviews, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'reviews': serializer.data,
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
                'has_next': end < total,
                'has_previous': page > 1
            },
            'summary': {
                'average': agent.average_rating,
                'total': agent.total_reviews
            }
        })
    
    @action(detail=True, methods=['get'])
    def properties(self, request, pk=None):
        agent = self.get_object()
        
        properties = Property.objects.filter(
            owner=agent.user,
            is_active=True
        ).order_by('-created_at')
        
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = properties.count()
        paginated_properties = properties[start:end]
        
        property_data = []
        for prop in paginated_properties:
            property_data.append({
                'id': str(prop.id),
                'title': prop.title,
                'description': prop.description[:200] if prop.description else '',
                'city': prop.city,
                'state': prop.state,
                'country': prop.country,
                'price': f"{prop.price_currency} {prop.base_price}" if prop.base_price else 'Contact for price',
                'price_currency': prop.price_currency,
                'base_price': str(prop.base_price) if prop.base_price else None,
                'listing_type': prop.listing_type,
                'status': prop.status,
                'is_featured': prop.is_featured,
                'is_premium': prop.is_premium,
                'main_image_url': prop.get_main_image_url(),
                'bedrooms': prop.bedrooms,
                'bathrooms': prop.bathrooms,
                'garages': prop.garages,
                'average_rating': prop.average_rating,
                'created_at': prop.created_at
            })
        
        return Response({
            'success': True,
            'properties': property_data,
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
                'has_next': end < total,
                'has_previous': page > 1
            }
        })
    
    @action(detail=True, methods=['get'])
    def share_data(self, request, pk=None):
        agent = self.get_object()
        property_id = request.query_params.get('property_id')
        
        property_obj = None
        if property_id:
            try:
                property_obj = Property.objects.get(id=property_id, is_active=True)
            except Property.DoesNotExist:
                pass
        
        data = agent.get_social_share_data(property_obj)
        
        base_url = request.build_absolute_uri('/')
        share_url = f"{base_url}agent/{agent.id}/"
        
        share_links = {
            'whatsapp': f"https://wa.me/?text={data.get('agent_name', '')} - {data.get('property_title', '')}%0A{share_url}",
            'facebook': f"https://www.facebook.com/sharer/sharer.php?u={share_url}",
            'twitter': f"https://twitter.com/intent/tweet?text={data.get('agent_name', '')}&url={share_url}",
            'linkedin': f"https://www.linkedin.com/sharing/share-offsite/?url={share_url}",
        }
        
        data['share_links'] = share_links
        data['share_url'] = share_url
        
        return Response({
            'success': True,
            'share_data': data
        })
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        limit = int(request.query_params.get('limit', 10))
        agents = AgentProfile.objects.filter(
            is_featured=True,
            is_verified=True
        ).order_by('-average_rating', '-total_deals')[:limit]
        
        serializer = AgentProfileListSerializer(agents, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'agents': serializer.data,
            'count': agents.count()
        })
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '').strip()
        agent_type = request.query_params.get('agent_type', '')
        city = request.query_params.get('city', '')
        state_province = request.query_params.get('state_province', '')
        country_id = request.query_params.get('country', '')
        specialization = request.query_params.get('specialization', '')
        min_rating = request.query_params.get('min_rating', '')
        is_verified = request.query_params.get('is_verified', '').lower() == 'true'
        is_featured = request.query_params.get('is_featured', '').lower() == 'true'
        sort_by = request.query_params.get('sort_by', 'average_rating')
        sort_order = request.query_params.get('sort_order', 'desc')
        
        queryset = AgentProfile.objects.all()
        
        if query:
            queryset = queryset.filter(
                Q(display_name__icontains=query) |
                Q(agency_name__icontains=query) |
                Q(bio__icontains=query) |
                Q(city__icontains=query) |
                Q(state_province__icontains=query) |
                Q(custom_agent_type__icontains=query) |
                Q(custom_specializations__icontains=query) |
                Q(user__username__icontains=query)
            )
        
        if agent_type:
            if agent_type == 'custom':
                queryset = queryset.filter(agent_type='custom')
            else:
                queryset = queryset.filter(agent_type=agent_type)
        
        if city:
            queryset = queryset.filter(city__icontains=city)
        if state_province:
            queryset = queryset.filter(state_province__icontains=state_province)
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        
        if specialization:
            queryset = queryset.filter(
                Q(specializations__contains=[specialization]) |
                Q(custom_specializations__icontains=specialization)
            )
        
        if min_rating:
            try:
                min_rating = float(min_rating)
                queryset = queryset.filter(average_rating__gte=min_rating)
            except:
                pass
        
        if is_verified:
            queryset = queryset.filter(is_verified=True)
        if is_featured:
            queryset = queryset.filter(is_featured=True)
        
        if sort_by in ['average_rating', 'total_reviews', 'total_deals', 'years_experience', 'created_at']:
            if sort_order == 'desc':
                sort_by = f'-{sort_by}'
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-average_rating', '-total_deals')
        
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        paginated_agents = queryset[start:end]
        
        serializer = AgentProfileListSerializer(paginated_agents, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'agents': serializer.data,
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'has_next': end < total,
            'has_previous': page > 1
        })
    
    @action(detail=True, methods=['post'])
    def respond_to_review(self, request, pk=None):
        agent = self.get_object()
        user = request.user
        
        if agent.user != user:
            return Response({
                'success': False,
                'error': 'Only the agent can respond to reviews'
            }, status=status.HTTP_403_FORBIDDEN)
        
        review_id = request.data.get('review_id')
        response_text = request.data.get('response', '').strip()
        
        if not review_id:
            return Response({
                'success': False,
                'error': 'Review ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not response_text:
            return Response({
                'success': False,
                'error': 'Response text is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            review = AgentReview.objects.get(id=review_id, agent=agent)
        except AgentReview.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Review not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        review.agent_response = response_text
        review.agent_response_at = timezone.now()
        review.save(update_fields=['agent_response', 'agent_response_at'])
        
        return Response({
            'success': True,
            'message': 'Response added successfully',
            'review': AgentReviewSerializer(review, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def update_stats(self, request, pk=None):
        agent = self.get_object()
        user = request.user
        
        if agent.user != user and not user.is_superuser and user.user_type != 'admin':
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        fields_to_update = ['properties_sold', 'properties_rented', 'properties_listed', 'total_deals', 'total_volume']
        updated_fields = []
        
        for field in fields_to_update:
            if field in request.data:
                try:
                    value = float(request.data[field])
                    setattr(agent, field, value)
                    updated_fields.append(field)
                except:
                    pass
        
        if updated_fields:
            if 'total_deals' not in request.data:
                agent.total_deals = agent.properties_sold + agent.properties_rented
                updated_fields.append('total_deals')
            
            agent.save(update_fields=updated_fields)
        
        return Response({
            'success': True,
            'message': 'Stats updated successfully',
            'agent': AgentProfileSerializer(agent, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def detect_phone_country(self, request, pk=None):
        agent = self.get_object()
        phone_number = request.data.get('phone_number', '')
        
        if not phone_number:
            return Response({
                'success': False,
                'error': 'Phone number is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        country = agent.detect_country_from_number(phone_number)
        
        if country:
            return Response({
                'success': True,
                'country': CountrySerializer(country).data,
                'formatted_number': agent.clean_phone_number(phone_number)
            })
        else:
            return Response({
                'success': False,
                'error': 'Could not detect country from phone number'
            }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# API ENDPOINTS
# ============================================================

@api_view(['GET'])
def get_agent_for_property(request, property_id):
    try:
        property_obj = Property.objects.get(id=property_id, is_active=True)
        
        if not property_obj.owner:
            return Response({
                'success': False,
                'error': 'Property has no owner'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            agent_profile = AgentProfile.objects.get(user=property_obj.owner)
            serializer = AgentProfileDetailSerializer(
                agent_profile, 
                context={'request': request}
            )
            
            contact_methods = agent_profile.get_contact_methods()
            
            return Response({
                'success': True,
                'agent': serializer.data,
                'contact_methods': contact_methods,
                'social_links': agent_profile.get_active_social_links(),
                'internal_messaging_available': True,
                'detected_country': CountrySerializer(
                    agent_profile.detect_country_from_number(agent_profile.phone_primary)
                ).data if agent_profile.phone_primary else None
            })
        except AgentProfile.DoesNotExist:
            return Response({
                'success': True,
                'agent': None,
                'user': {
                    'id': str(property_obj.owner.id),
                    'username': property_obj.owner.username,
                    'full_name': property_obj.owner.get_full_name() or property_obj.owner.username,
                    'email': property_obj.owner.email
                },
                'contact_methods': [
                    {
                        'type': 'message',
                        'label': f'Message {property_obj.owner.username}',
                        'value': str(property_obj.owner.id),
                        'icon': 'fas fa-comment',
                        'priority': 1,
                        'is_primary': True,
                        'internal': True,
                        'action': 'message_property_owner'
                    }
                ],
                'internal_messaging_available': True
            })
            
    except Property.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Property not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def featured_agents(request):
    limit = int(request.query_params.get('limit', 10))
    agents = AgentProfile.objects.filter(
        is_featured=True,
        is_verified=True
    ).order_by('-average_rating', '-total_deals')[:limit]
    
    serializer = AgentProfileListSerializer(agents, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'agents': serializer.data,
        'count': agents.count()
    })


@api_view(['GET'])
def top_agents(request):
    limit = int(request.query_params.get('limit', 10))
    agents = AgentProfile.objects.filter(
        is_verified=True,
        total_reviews__gte=1
    ).order_by('-average_rating', '-total_reviews')[:limit]
    
    serializer = AgentProfileListSerializer(agents, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'agents': serializer.data,
        'count': agents.count()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def track_agent_contact(request):
    agent_id = request.data.get('agent_id')
    contact_method = request.data.get('contact_method')
    
    if not agent_id or not contact_method:
        return Response({
            'success': False,
            'error': 'agent_id and contact_method are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        agent = AgentProfile.objects.get(id=agent_id)
    except AgentProfile.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'success': True,
        'message': f'Contact tracked: {contact_method}',
        'agent': agent.display_name or agent.user.username
    })


@api_view(['GET'])
def agent_contact_methods(request, agent_id):
    try:
        agent = AgentProfile.objects.get(id=agent_id)
    except AgentProfile.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    methods = agent.get_contact_methods()
    
    return Response({
        'success': True,
        'agent_id': str(agent.id),
        'agent_name': agent.display_name or agent.user.username,
        'contact_methods': methods,
        'internal_messaging_available': bool(agent.user and agent.user.id),
        'phone_formatted': agent.get_phone_display(),
        'detected_country': CountrySerializer(
            agent.detect_country_from_number(agent.phone_primary)
        ).data if agent.phone_primary else None
    })


@api_view(['GET'])
def check_agent_availability(request, agent_id):
    try:
        agent = AgentProfile.objects.get(id=agent_id)
    except AgentProfile.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'success': True,
        'agent_id': str(agent.id),
        'agent_name': agent.display_name or agent.user.username,
        'is_online': agent.is_online,
        'auto_accept_messages': agent.auto_accept_messages,
        'available_for_messaging': True,
        'status': 'online' if agent.is_online else 'offline',
        'country': CountrySerializer(agent.country).data if agent.country else None
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detect_country_from_number(request):
    phone_number = request.data.get('phone_number', '')
    
    if not phone_number:
        return Response({
            'success': False,
            'error': 'Phone number is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    cleaned = ''.join(filter(str.isdigit, phone_number))
    if not cleaned:
        return Response({
            'success': False,
            'error': 'Invalid phone number'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    country = Country.detect_country(cleaned)
    
    if country:
        return Response({
            'success': True,
            'country': CountrySerializer(country).data,
            'formatted_number': AgentProfile().clean_phone_number(phone_number)
        })
    else:
        return Response({
            'success': False,
            'error': 'Could not detect country from phone number'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def list_countries(request):
    countries = Country.objects.filter(is_active=True).order_by('name')
    serializer = CountrySerializer(countries, many=True)
    
    return Response({
        'success': True,
        'countries': serializer.data,
        'count': countries.count()
    })


# ============================================================
# ADMIN ENDPOINTS
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_verify_agent(request, agent_id):
    user = request.user
    if not user.is_superuser and user.user_type != 'admin':
        return Response({
            'success': False,
            'error': 'Permission denied. Admin access required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        agent = AgentProfile.objects.get(id=agent_id)
    except AgentProfile.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    agent.is_verified = True
    agent.save(update_fields=['is_verified'])
    
    return Response({
        'success': True,
        'message': f'Agent {agent.display_name or agent.user.username} verified successfully',
        'agent': AgentProfileSerializer(agent, context={'request': request}).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_feature_agent(request, agent_id):
    user = request.user
    if not user.is_superuser and user.user_type != 'admin':
        return Response({
            'success': False,
            'error': 'Permission denied. Admin access required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        agent = AgentProfile.objects.get(id=agent_id)
    except AgentProfile.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Agent not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    agent.is_featured = not agent.is_featured
    agent.save(update_fields=['is_featured'])
    
    return Response({
        'success': True,
        'message': f'Agent {agent.display_name or agent.user.username} {"featured" if agent.is_featured else "unfeatured"}',
        'is_featured': agent.is_featured,
        'agent': AgentProfileSerializer(agent, context={'request': request}).data
    })