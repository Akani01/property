from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings

from .models import (
    PropertyCategory, PropertyType, PropertyFeature, Property,
    Room, Booking, DriverLocation, AvailabilityCalendar,
    BookingInquiry, PropertyReview, Wishlist, PropertyAnalytics
)
from .serializers import (
    PropertyCategorySerializer, PropertyTypeSerializer, PropertyFeatureSerializer,
    PropertySerializer, PropertyListSerializer, PropertyDetailSerializer,
    PropertyCreateSerializer, RoomSerializer, BookingSerializer,
    BookingCreateSerializer, DriverLocationSerializer,
    AvailabilityCalendarSerializer, BookingInquirySerializer,
    PropertyReviewSerializer, WishlistSerializer, PropertyAnalyticsSerializer
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