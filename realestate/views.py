from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings

# At the top of your views.py, add these imports if they don't exist:
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
    MaintenanceRequest,  # <-- ADD THIS
    MaintenanceComment,  # <-- ADD THIS
    DriverLocation,  # <-- ADD THIS
)

# Also make sure you have these serializers imported:
from .serializers import (
    PropertyCategorySerializer,
    PropertyTypeSerializer,
    PropertyFeatureSerializer,
    PropertySerializer,
    RoomSerializer,
    BookingSerializer,
    AvailabilityCalendarSerializer,
    BookingInquirySerializer,
    PropertyReviewSerializer,
    WishlistSerializer,
    PropertyAnalyticsSerializer,
    MaintenanceCategorySerializer,  # <-- ADD THIS
    MaintenanceRequestSerializer,   # <-- ADD THIS
    MaintenanceCommentSerializer,   # <-- ADD THIS
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
    """Main Property ViewSet with all features"""
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
    
    @action(detail=True, methods=['post'])
    def toggle_online(self, request, pk=None):
        property_obj = self.get_object()
        property_obj.is_online = not property_obj.is_online
        property_obj.save()
        return Response({
            'is_online': property_obj.is_online,
            'agent_status': property_obj.agent_status
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
        """Return only the current user's wishlists"""
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

@action(detail=True, methods=['post'])
def book(self, request, pk=None):
    """Book a property"""
    property_obj = self.get_object()
    
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if property_obj.status != 'available':
        return Response(
            {'error': 'Property is not available for booking'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create booking
    from datetime import datetime, timedelta
    check_in = timezone.now()
    check_out = check_in + timedelta(days=1)
    
    booking = Booking.objects.create(
        property=property_obj,
        guest=request.user,
        check_in=check_in,
        check_out=check_out,
        duration_days=1,
        subtotal=property_obj.base_price or 0,
        total_amount=property_obj.base_price or 0,
        status='pending',
        booking_mode='instant'
    )
    
    # Update property status
    property_obj.status = 'booked'
    property_obj.save()
    
    return Response({
        'success': True,
        'message': 'Property booked successfully',
        'booking_id': str(booking.id),
        'booking_reference': booking.booking_reference
    })


class MaintenanceCategoryViewSet(viewsets.ModelViewSet):
    """Complete CRUD for categories - simple and clean"""
    queryset = MaintenanceCategory.objects.filter(is_active=True)
    serializer_class = MaintenanceCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Admin can see all, others only active
        if self.request.user.user_type == 'admin' or self.request.user.is_superuser:
            return MaintenanceCategory.objects.all()
        return MaintenanceCategory.objects.filter(is_active=True)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle category active status"""
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
        
        # Admin sees all
        if user.user_type == 'admin' or user.is_superuser:
            return MaintenanceRequest.objects.all().select_related('category', 'tenant', 'property')
        
        # Tenant sees their own
        return MaintenanceRequest.objects.filter(tenant=user).select_related('category', 'property')
    
    def perform_create(self, serializer):
        """Auto-set tenant if not provided"""
        tenant = serializer.validated_data.get('tenant')
        if not tenant:
            tenant = self.request.user
        serializer.save(tenant=tenant)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Quick status update"""
        request_obj = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(MaintenanceRequest.Status.choices):
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Only admin or the tenant can update
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
        """Add a comment to a maintenance request"""
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
        """Get maintenance statistics"""
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
        
        # Category breakdown
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
    """Comments management"""
    serializer_class = MaintenanceCommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return MaintenanceComment.objects.filter(
            request__in=MaintenanceRequest.objects.filter(tenant=self.request.user)
        )
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)



@api_view(['GET'])
def get_property_types(request):
    """Get all property types for the frontend"""
    types = PropertyType.objects.all().order_by('name')
    serializer = PropertyTypeSerializer(types, many=True)
    return Response({
        'success': True,
        'types': serializer.data
    })
