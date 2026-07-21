from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# ===== ALL IMPORTS =====
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
    
    # ============================================
    # IMAGE MANAGEMENT ACTIONS - FULLY FIXED
    # ============================================
    
    @action(detail=True, methods=['post'], url_path='update-image')
    def update_image(self, request, pk=None):
        """Update property main image"""
        property_obj = self.get_object()
        
        if 'main_image' not in request.FILES:
            return Response({
                'success': False,
                'error': 'No image file provided'
            }, status=400)
        
        try:
            file = request.FILES['main_image']
            
            # Validate file type
            valid_extensions = ['jpg', 'jpeg', 'png', 'webp', 'gif']
            ext = file.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                return Response({
                    'success': False,
                    'error': f'Invalid file type. Supported: {", ".join(valid_extensions)}'
                }, status=400)
            
            # Validate file size (10MB max)
            if file.size > 10 * 1024 * 1024:
                return Response({
                    'success': False,
                    'error': 'File too large. Max 10MB.'
                }, status=400)
            
            # Delete old image if exists
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
            }, status=500)
    
    @action(detail=True, methods=['post'], url_path='remove-image')
    def remove_image(self, request, pk=None):
        """Remove property main image"""
        property_obj = self.get_object()
        
        if not property_obj.main_image:
            return Response({
                'success': False,
                'error': 'No image to remove'
            }, status=400)
        
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
            }, status=500)
    
    @action(detail=True, methods=['post'], url_path='add-additional-image')
    def add_additional_image(self, request, pk=None):
        """Add an additional image to property"""
        property_obj = self.get_object()
        
        if 'image' not in request.FILES:
            return Response({
                'success': False,
                'error': 'No image file provided'
            }, status=400)
        
        try:
            file = request.FILES['image']
            
            # Validate file type
            valid_extensions = ['jpg', 'jpeg', 'png', 'webp', 'gif']
            ext = file.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                return Response({
                    'success': False,
                    'error': f'Invalid file type. Supported: {", ".join(valid_extensions)}'
                }, status=400)
            
            # Validate file size (10MB max)
            if file.size > 10 * 1024 * 1024:
                return Response({
                    'success': False,
                    'error': 'File too large. Max 10MB.'
                }, status=400)
            
            # Get current additional images
            additional_images = property_obj.additional_images or []
            
            # Generate unique filename
            import uuid
            import os
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            filename = f"additional_{uuid.uuid4().hex[:8]}.{ext}"
            path = f"properties/additional/{timezone.now().strftime('%Y/%m/%d')}/{filename}"
            
            # Save file
            saved_path = default_storage.save(path, ContentFile(file.read()))
            
            # Get URL
            try:
                file_url = default_storage.url(saved_path)
            except:
                file_url = f"/media/{saved_path}"
            
            # Add to list
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
            import traceback
            print(f"❌ Error adding additional image: {str(e)}")
            print(traceback.format_exc())
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    @action(detail=True, methods=['post'], url_path='remove-additional-image')
    def remove_additional_image(self, request, pk=None):
        """Remove an additional image from property"""
        property_obj = self.get_object()
        index = request.data.get('index')
        
        if index is None:
            return Response({
                'success': False,
                'error': 'Image index required'
            }, status=400)
        
        try:
            index = int(index)
            additional_images = property_obj.additional_images or []
            
            if 0 <= index < len(additional_images):
                removed_url = additional_images.pop(index)
                property_obj.additional_images = additional_images
                property_obj.save(update_fields=['additional_images', 'updated_at'])
                
                # Try to delete the file from storage
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
                }, status=400)
                
        except ValueError:
            return Response({
                'success': False,
                'error': 'Invalid index format'
            }, status=400)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)
    
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
        """Soft delete a property"""
        property_obj = self.get_object()
        property_obj.is_active = False
        property_obj.save()
        return Response({
            'success': True,
            'message': 'Property deleted successfully'
        })


class RoomViewSet(viewsets.ModelViewSet):
    """ViewSet for rooms/units"""
    queryset = Room.objects.filter(is_active=True)
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['property', 'room_type', 'room_status']
    search_fields = ['room_number', 'room_name', 'description']


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
            defaults={
                'latitude': lat,
                'longitude': lng,
                'is_active': True
            }
        )
        
        return Response(DriverLocationSerializer(location).data)


class AvailabilityCalendarViewSet(viewsets.ModelViewSet):
    queryset = AvailabilityCalendar.objects.all()
    serializer_class = AvailabilityCalendarSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['property', 'room', 'availability_type']


class BookingInquiryViewSet(viewsets.ModelViewSet):
    queryset = BookingInquiry.objects.all()
    serializer_class = BookingInquirySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'inquiry_type', 'property']
    search_fields = ['first_name', 'last_name', 'email']


class PropertyReviewViewSet(viewsets.ModelViewSet):
    queryset = PropertyReview.objects.filter(is_approved=True)
    serializer_class = PropertyReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['property', 'overall_rating']
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


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


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    """Simple maintenance request management"""
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin' or user.is_superuser:
            return MaintenanceRequest.objects.all().select_related('category', 'tenant', 'property')
        return MaintenanceRequest.objects.filter(tenant=user).select_related('category', 'property')
    
    def perform_create(self, serializer):
        tenant = serializer.validated_data.get('tenant')
        if not tenant:
            tenant = self.request.user
        serializer.save(tenant=tenant)
    
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


class MaintenanceCommentViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceCommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return MaintenanceComment.objects.filter(
            request__in=MaintenanceRequest.objects.filter(tenant=self.request.user)
        )
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# ============================================
# API ENDPOINTS FOR PROPERTY ADD
# ============================================

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
        }, status=400)
    
    if PropertyType.objects.filter(name__iexact=name).exists():
        return Response({
            'success': False,
            'error': f'Property type "{name}" already exists'
        }, status=400)
    
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
        }, status=500)


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
        }, status=400)
    
    if PropertyFeature.objects.filter(name__iexact=name).exists():
        return Response({
            'success': False,
            'error': f'Feature "{name}" already exists'
        }, status=400)
    
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
        }, status=500)


# ============================================
# 🗺️ GEOCODING & MAP ENDPOINTS
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def geocode_address_api(request):
    """Convert address to coordinates - user friendly!"""
    address = request.data.get('address', '').strip()
    city = request.data.get('city', '').strip()
    country = request.data.get('country', 'South Africa')
    
    if not address:
        return Response({
            'success': False,
            'error': 'Street address is required'
        }, status=400)
    
    if not city:
        return Response({
            'success': False,
            'error': 'City is required'
        }, status=400)
    
    full_address = f"{address}, {city}, {country}"
    
    google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    
    if not google_api_key:
        return Response({
            'success': False,
            'error': 'Google Maps API key not configured'
        }, status=500)
    
    try:
        import requests
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
            }, status=404)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


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
        }, status=400)
    
    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        return Response({
            'success': False,
            'error': 'Invalid coordinates'
        }, status=400)
    
    properties = Property.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('property_type')
    
    nearby = []
    user_location = (lat, lng)
    
    try:
        from geopy.distance import geodesic
        
        for property in properties:
            if property.latitude and property.longitude:
                prop_location = (float(property.latitude), float(property.longitude))
                distance = geodesic(user_location, prop_location).kilometers
                
                if distance <= radius:
                    nearby.append({
                        'id': str(property.id),
                        'title': property.title,
                        'description': property.description[:200] if property.description else '',
                        'address': property.address,
                        'city': property.city,
                        'country': property.country,
                        'price': float(property.base_price) if property.base_price else 0,
                        'latitude': float(property.latitude),
                        'longitude': float(property.longitude),
                        'distance': round(distance, 1),
                        'main_image_url': property.get_main_image_url(),
                        'is_featured': property.is_featured,
                        'is_premium': property.is_premium,
                        'is_online': property.is_online,
                        'status': property.status,
                        'bedrooms': property.bedrooms,
                        'bathrooms': property.bathrooms,
                        'property_type': property.property_type.name if property.property_type else 'Property',
                    })
        
        nearby.sort(key=lambda x: x['distance'])
        
    except ImportError:
        for property in properties:
            if property.latitude and property.longitude:
                lat_diff = abs(float(property.latitude) - lat) * 111
                lng_diff = abs(float(property.longitude) - lng) * 111 * 0.9
                distance = (lat_diff**2 + lng_diff**2)**0.5
                
                if distance <= radius:
                    nearby.append({
                        'id': str(property.id),
                        'title': property.title,
                        'description': property.description[:200] if property.description else '',
                        'address': property.address,
                        'city': property.city,
                        'country': property.country,
                        'price': float(property.base_price) if property.base_price else 0,
                        'latitude': float(property.latitude),
                        'longitude': float(property.longitude),
                        'distance': round(distance, 1),
                        'main_image_url': property.get_main_image_url(),
                        'is_featured': property.is_featured,
                        'is_premium': property.is_premium,
                        'is_online': property.is_online,
                        'status': property.status,
                        'bedrooms': property.bedrooms,
                        'bathrooms': property.bathrooms,
                        'property_type': property.property_type.name if property.property_type else 'Property',
                    })
        
        nearby.sort(key=lambda x: x['distance'])
    
    return Response({
        'success': True,
        'properties': nearby,
        'count': len(nearby),
        'user_location': {
            'lat': lat,
            'lng': lng
        }
    })


# ============================================
# BUSINESS BOOKINGS API
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_business_bookings(request):
    """Get bookings for business admin"""
    if request.user.user_type != 'admin':
        return Response({'error': 'Unauthorized'}, status=403)
    
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
        }, status=500)