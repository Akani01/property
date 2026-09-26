from decimal import Decimal, InvalidOperation

from django.conf import settings
import requests
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import (
    BusinessPaymentGateway,
    CarWashBusiness,
    CarWashPayment,
    CarWashProviderLocation,
    CarWashQuote,
    CarWashRequest,
    CarWashReview,
    CarWashService,
    CarWashWorker,
    PaymentAttempt,
    PaymentGateway,
    ServiceVehiclePrice,
    VehicleType,
)
from .payments.registry import get_gateway
from .serializers import (
    BusinessPaymentGatewaySerializer,
    CarWashBusinessSerializer,
    CarWashPaymentSerializer,
    CarWashProviderLocationSerializer,
    CarWashQuoteSerializer,
    CarWashRequestSerializer,
    CarWashReviewSerializer,
    CarWashServiceSerializer,
    CarWashWorkerSerializer,
    CreatePaymentSerializer,
    PaymentGatewaySerializer,
    ProviderLocationUpdateSerializer,
    QuoteRequestSerializer,
    ServiceVehiclePriceSerializer,
    VehicleTypeSerializer,
)
from .services import calculate_quote, haversine_km, record_status, settle_completed_payment


def carwash_map(request):
    business = None
    worker = None
    is_business_account = False
    can_manage_business = False

    if request.user.is_authenticated:
        owned_business = CarWashBusiness.objects.filter(owner=request.user).first()
        worker = CarWashWorker.objects.filter(user=request.user, is_active=True).select_related('business').first()
        business = owned_business or (worker.business if worker else None)
        can_manage_business = bool(
            owned_business or request.user.is_superuser or getattr(request.user, 'user_type', '') == 'admin'
        )
        is_business_account = bool(can_manage_business or worker)

    return render(request, 'carwash/map.html', {
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        'carwash_business': business,
        'carwash_worker': worker,
        'is_carwash_business_user': is_business_account,
        'can_manage_carwash_business': can_manage_business,
    })


class BusinessOwnedMixin:
    def get_business_for_user(self):
        return get_object_or_404(CarWashBusiness, owner=self.request.user, is_active=True)


class CarWashBusinessViewSet(viewsets.ModelViewSet):
    serializer_class = CarWashBusinessSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = CarWashBusiness.objects.filter(is_active=True).select_related('owner')
        if self.request.user.is_authenticated and self.request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            if self.request.user.is_superuser:
                return CarWashBusiness.objects.all().select_related('owner')
            return CarWashBusiness.objects.filter(owner=self.request.user).select_related('owner')
        return qs

    def perform_create(self, serializer):
        if CarWashBusiness.objects.filter(owner=self.request.user).exists() and not self.request.user.is_superuser:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('You already have a car wash business profile.')
        business = serializer.save(owner=self.request.user)
        # The owner is the first washer by default, so a one-person mobile
        # business can go online and accept work immediately. Larger teams can
        # add additional worker profiles later.
        CarWashWorker.objects.get_or_create(
            business=business,
            user=self.request.user,
            defaults={
                'display_name': self.request.user.get_full_name() or self.request.user.get_username(),
                'is_active': True,
                'is_online': False,
                'is_available': False,
            },
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        business = CarWashBusiness.objects.filter(owner=request.user).first()
        if not business:
            return Response({'success': True, 'business': None})
        return Response({
            'success': True,
            'business': self.get_serializer(business).data,
        })


class VehicleTypeViewSet(BusinessOwnedMixin, viewsets.ModelViewSet):
    serializer_class = VehicleTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return VehicleType.objects.all()
        return VehicleType.objects.filter(business__owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(business=self.get_business_for_user())


class CarWashServiceViewSet(BusinessOwnedMixin, viewsets.ModelViewSet):
    serializer_class = CarWashServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return CarWashService.objects.all()
        return CarWashService.objects.filter(business__owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(business=self.get_business_for_user())


class ServiceVehiclePriceViewSet(BusinessOwnedMixin, viewsets.ModelViewSet):
    serializer_class = ServiceVehiclePriceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return ServiceVehiclePrice.objects.select_related('service', 'vehicle_type', 'business')
        return ServiceVehiclePrice.objects.filter(business__owner=self.request.user).select_related('service', 'vehicle_type')

    def perform_create(self, serializer):
        business = self.get_business_for_user()
        service = serializer.validated_data['service']
        vehicle_type = serializer.validated_data['vehicle_type']
        if service.business_id != business.id or vehicle_type.business_id != business.id:
            raise ValueError('Service and vehicle type must belong to your business.')
        serializer.save(business=business)


class CarWashWorkerViewSet(BusinessOwnedMixin, viewsets.ModelViewSet):
    serializer_class = CarWashWorkerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return CarWashWorker.objects.all().select_related('business', 'user')
        return CarWashWorker.objects.filter(business__owner=self.request.user).select_related('business', 'user')

    def perform_create(self, serializer):
        business = self.get_business_for_user()
        user = serializer.validated_data['user']
        if CarWashWorker.objects.filter(business=business, user=user).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError('This user is already a worker for your business.')
        serializer.save(business=business)


class BusinessPaymentGatewayViewSet(BusinessOwnedMixin, viewsets.ModelViewSet):
    serializer_class = BusinessPaymentGatewaySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return BusinessPaymentGateway.objects.select_related('business', 'gateway')
        return BusinessPaymentGateway.objects.filter(business__owner=self.request.user).select_related('business', 'gateway')

    def perform_create(self, serializer):
        serializer.save(business=self.get_business_for_user())


class CarWashPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CarWashPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return CarWashPayment.objects.filter(
            Q(wash_request__customer=user) |
            Q(wash_request__business__owner=user) |
            Q(wash_request__assigned_worker__user=user)
        ).select_related('wash_request', 'wash_request__business', 'gateway').distinct()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_business_location(request):
    """Save a business location detected by the device or Google Places.

    Latitude/longitude/place_id are backend values; they are never human input fields.
    """
    business = CarWashBusiness.objects.filter(owner=request.user).first()
    if not business:
        return Response({'success': False, 'error': 'Create your car wash business profile first.'}, status=404)

    lat = request.data.get('latitude')
    lng = request.data.get('longitude')
    formatted_address = (request.data.get('formatted_address') or request.data.get('address') or '').strip()
    place_id = (request.data.get('place_id') or '').strip()

    if lat is None or lng is None:
        return Response({'success': False, 'error': 'Location could not be detected.'}, status=400)

    try:
        lat = Decimal(str(lat))
        lng = Decimal(str(lng))
    except (InvalidOperation, TypeError, ValueError):
        return Response({'success': False, 'error': 'Invalid detected location.'}, status=400)

    # If Google Places did not already give us a label, reverse geocode on the server.
    if not formatted_address or not place_id:
        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        if api_key:
            try:
                response = requests.get(
                    'https://maps.googleapis.com/maps/api/geocode/json',
                    params={'latlng': f'{lat},{lng}', 'key': api_key},
                    timeout=8,
                )
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    first = data['results'][0]
                    formatted_address = formatted_address or first.get('formatted_address', '')
                    place_id = place_id or first.get('place_id', '')
            except requests.RequestException:
                pass

    business.latitude = lat
    business.longitude = lng
    business.place_id = place_id
    if formatted_address:
        business.address = formatted_address
        business.formatted_address = formatted_address
    business.save()

    return Response({
        'success': True,
        'business': CarWashBusinessSerializer(business, context={'request': request}).data,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def reverse_geocode(request):
    """Resolve the customer's map coordinates to a readable Google address."""
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')

    if not lat or not lng:
        return Response(
            {'success': False, 'error': 'lat and lng are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        lat = Decimal(str(lat))
        lng = Decimal(str(lng))
    except (InvalidOperation, TypeError, ValueError):
        return Response(
            {'success': False, 'error': 'Invalid coordinates'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    if not google_api_key:
        return Response(
            {'success': False, 'error': 'Google Maps API key is not configured'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        response = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={
                'latlng': f'{lat},{lng}',
                'key': google_api_key,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if data.get('status') != 'OK' or not data.get('results'):
            return Response({
                'success': False,
                'error': 'Could not resolve this location',
                'google_status': data.get('status', ''),
            }, status=status.HTTP_404_NOT_FOUND)

        first = data['results'][0]
        return Response({
            'success': True,
            'formatted_address': first.get('formatted_address', ''),
            'place_id': first.get('place_id', ''),
            'latitude': str(lat),
            'longitude': str(lng),
        })
    except requests.RequestException as exc:
        return Response(
            {'success': False, 'error': 'Google location service is temporarily unavailable'},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_providers(request):
    """Return providers that can actually serve the customer's current map position."""
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    fulfilment = request.GET.get('fulfilment', 'mobile').strip().lower()

    if fulfilment not in {'mobile', 'onsite'}:
        return Response(
            {'success': False, 'error': 'fulfilment must be mobile or onsite'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not lat or not lng:
        return Response(
            {'success': False, 'error': 'lat and lng are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        lat = Decimal(str(lat))
        lng = Decimal(str(lng))
        radius = Decimal(str(request.GET.get('radius', '25')))
    except (InvalidOperation, TypeError, ValueError):
        return Response(
            {'success': False, 'error': 'Invalid coordinates or radius'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if radius <= 0:
        radius = Decimal('25')
    radius = min(radius, Decimal('100'))

    businesses = CarWashBusiness.objects.filter(
        is_active=True,
        is_accepting_jobs=True,
    ).prefetch_related('vehicle_types', 'services')

    if fulfilment == 'mobile':
        businesses = businesses.filter(fulfilment_mode__in=['mobile', 'both'])
    else:
        businesses = businesses.filter(fulfilment_mode__in=['onsite', 'both'])

    results = []

    for business in businesses:
        worker = None

        if fulfilment == 'mobile':
            location = (
                CarWashProviderLocation.objects
                .filter(
                    worker__business=business,
                    worker__is_active=True,
                    worker__is_online=True,
                    worker__is_available=True,
                    is_active=True,
                )
                .select_related('worker', 'worker__user')
                .order_by('-recorded_at')
                .first()
            )

            if not location:
                continue

            b_lat = location.latitude
            b_lng = location.longitude
            worker = location.worker
        else:
            if business.latitude is None or business.longitude is None:
                continue
            b_lat = business.latitude
            b_lng = business.longitude

        distance = Decimal(str(round(haversine_km(lat, lng, b_lat, b_lng), 2)))

        if fulfilment == 'mobile':
            effective_radius = min(radius, business.service_radius_km)
        else:
            effective_radius = radius

        if distance > effective_radius:
            continue

        # A business should not be offered until it has at least one active,
        # priced service/vehicle combination for this mode.
        active_prices = ServiceVehiclePrice.objects.filter(
            business=business,
            is_active=True,
            vehicle_type__is_active=True,
            service__is_active=True,
        )
        if fulfilment == 'mobile':
            active_prices = active_prices.filter(service__mobile_available=True)
        else:
            active_prices = active_prices.filter(service__onsite_available=True)

        if not active_prices.exists():
            continue

        data = CarWashBusinessSerializer(
            business,
            context={'request': request},
        ).data
        data.update({
            'distance_km': str(distance),
            'map_latitude': str(b_lat),
            'map_longitude': str(b_lng),
            'available_worker_id': str(worker.id) if worker else None,
            'available_worker_name': (
                worker.display_name or worker.user.get_username()
            ) if worker else None,
            'available_options_count': active_prices.count(),
        })
        results.append(data)

    results.sort(key=lambda item: Decimal(item['distance_km']))
    return Response({
        'success': True,
        'providers': results,
        'count': len(results),
        'fulfilment': fulfilment,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def business_catalog(request, business_id):
    """
    Dynamic customer catalogue for one provider.

    Only return vehicle + service combinations that the business has priced,
    and filter them by mobile/on-site availability.
    """
    business = get_object_or_404(
        CarWashBusiness,
        id=business_id,
        is_active=True,
        is_accepting_jobs=True,
    )

    fulfilment = request.GET.get('fulfilment', 'mobile').strip().lower()
    if fulfilment not in {'mobile', 'onsite'}:
        return Response(
            {'success': False, 'error': 'fulfilment must be mobile or onsite'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if fulfilment == 'mobile' and not business.supports_mobile:
        return Response(
            {'success': False, 'error': 'This provider does not offer mobile washes.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if fulfilment == 'onsite' and not business.supports_onsite:
        return Response(
            {'success': False, 'error': 'This provider does not offer on-site washes.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    prices = (
        business.service_prices
        .filter(
            is_active=True,
            vehicle_type__is_active=True,
            service__is_active=True,
        )
        .select_related('service', 'vehicle_type')
    )

    if fulfilment == 'mobile':
        prices = prices.filter(service__mobile_available=True)
    else:
        prices = prices.filter(service__onsite_available=True)

    vehicle_ids = prices.values_list('vehicle_type_id', flat=True).distinct()
    service_ids = prices.values_list('service_id', flat=True).distinct()

    vehicles = business.vehicle_types.filter(
        id__in=vehicle_ids,
        is_active=True,
    )
    services = business.services.filter(
        id__in=service_ids,
        is_active=True,
    )

    return Response({
        'success': True,
        'fulfilment': fulfilment,
        'business': CarWashBusinessSerializer(
            business,
            context={'request': request},
        ).data,
        'vehicles': VehicleTypeSerializer(vehicles, many=True).data,
        'services': CarWashServiceSerializer(services, many=True).data,
        'prices': ServiceVehiclePriceSerializer(prices, many=True).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_quote(request):
    serializer = QuoteRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    business = get_object_or_404(CarWashBusiness, id=data['business_id'], is_active=True, is_accepting_jobs=True)
    vehicle = get_object_or_404(VehicleType, id=data['vehicle_type_id'], business=business, is_active=True)
    service = get_object_or_404(CarWashService, id=data['service_id'], business=business, is_active=True)

    fulfilment = data['fulfilment_mode']
    if fulfilment == 'mobile' and (not business.supports_mobile or not service.mobile_available):
        return Response({'success': False, 'error': 'Mobile service is not available for this selection.'}, status=400)
    if fulfilment == 'onsite' and (not business.supports_onsite or not service.onsite_available):
        return Response({'success': False, 'error': 'On-site service is not available for this selection.'}, status=400)

    price_row = get_object_or_404(
        ServiceVehiclePrice,
        business=business,
        vehicle_type=vehicle,
        service=service,
        is_active=True,
    )

    pricing = calculate_quote(
        business=business,
        price_row=price_row,
        fulfilment_mode=fulfilment,
        route_distance_km=data.get('route_distance_km', Decimal('0.00')),
    )

    if fulfilment == 'mobile':
        service_latitude = data.get('latitude')
        service_longitude = data.get('longitude')
        service_address = data.get('address', '')
        service_place_id = data.get('place_id', '')
    else:
        if business.latitude is None or business.longitude is None:
            return Response({'success': False, 'error': 'This business has not configured its Google Maps location yet.'}, status=400)
        service_latitude = business.latitude
        service_longitude = business.longitude
        service_address = business.formatted_address or business.address
        service_place_id = business.place_id

    quote = CarWashQuote.objects.create(
        customer=request.user,
        business=business,
        vehicle_type=vehicle,
        service=service,
        fulfilment_mode=fulfilment,
        service_latitude=service_latitude,
        service_longitude=service_longitude,
        service_address=service_address,
        service_place_id=service_place_id,
        route_distance_km=data.get('route_distance_km', Decimal('0.00')),
        currency=price_row.currency,
        expires_at=timezone.now() + timezone.timedelta(minutes=10),
        **pricing,
    )

    return Response({'success': True, 'quote': CarWashQuoteSerializer(quote).data}, status=201)


class CarWashRequestViewSet(viewsets.ModelViewSet):
    serializer_class = CarWashRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return CarWashRequest.objects.filter(
            Q(customer=user) |
            Q(business__owner=user) |
            Q(assigned_worker__user=user)
        ).select_related('quote', 'business', 'assigned_worker__user').distinct()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        quote_id = request.data.get('quote_id')
        quote = get_object_or_404(
            CarWashQuote.objects.select_for_update(),
            id=quote_id,
            customer=request.user,
            is_used=False,
        )
        if quote.expires_at <= timezone.now():
            return Response({'success': False, 'error': 'Quote has expired. Please request a new quote.'}, status=400)

        wash_request = CarWashRequest.objects.create(
            customer=request.user,
            business=quote.business,
            quote=quote,
            status='requested',
            customer_notes=request.data.get('customer_notes', ''),
        )
        quote.is_used = True
        quote.save(update_fields=['is_used', 'updated_at'])
        record_status(wash_request, 'requested', request.user, 'Customer requested wash')

        return Response({'success': True, 'request': self.get_serializer(wash_request).data}, status=201)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def accept(self, request, pk=None):
        wash_request = self.get_object()
        worker = get_object_or_404(
            CarWashWorker,
            user=request.user,
            business=wash_request.business,
            is_active=True,
            is_online=True,
        )
        if wash_request.status not in {'requested', 'searching'}:
            return Response({'error': 'This request is no longer available.'}, status=400)

        wash_request.assigned_worker = worker
        wash_request.status = 'accepted'
        wash_request.accepted_at = timezone.now()
        wash_request.save(update_fields=['assigned_worker', 'status', 'accepted_at', 'updated_at'])
        worker.is_available = False
        worker.save(update_fields=['is_available', 'updated_at'])
        record_status(wash_request, 'accepted', request.user, 'Washer accepted request')
        return Response({'success': True, 'request': self.get_serializer(wash_request).data})

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        wash_request = self.get_object()
        new_status = request.data.get('status')
        valid = {choice[0] for choice in CarWashRequest.STATUS_CHOICES}
        if new_status not in valid:
            return Response({'error': 'Invalid status'}, status=400)

        is_customer = wash_request.customer_id == request.user.id
        is_worker = wash_request.assigned_worker and wash_request.assigned_worker.user_id == request.user.id
        is_owner = wash_request.business.owner_id == request.user.id
        if not (is_customer or is_worker or is_owner or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=403)

        allowed = {
            'accepted': {'en_route', 'cancelled'},
            'en_route': {'arrived', 'cancelled'},
            'arrived': {'washing', 'cancelled'},
            'washing': {'completed'},
            'requested': {'cancelled', 'accepted'},
        }
        if new_status not in allowed.get(wash_request.status, set()) and not request.user.is_superuser:
            return Response({'error': f'Cannot move from {wash_request.status} to {new_status}'}, status=400)

        now = timezone.now()
        wash_request.status = new_status
        field_map = {
            'en_route': 'en_route_at',
            'arrived': 'arrived_at',
            'washing': 'started_at',
            'completed': 'completed_at',
            'cancelled': 'cancelled_at',
        }
        if new_status in field_map:
            setattr(wash_request, field_map[new_status], now)
        wash_request.save()

        record_status(
            wash_request,
            new_status,
            request.user,
            request.data.get('note', ''),
            request.data.get('latitude'),
            request.data.get('longitude'),
        )

        if new_status == 'completed' and wash_request.assigned_worker:
            worker = wash_request.assigned_worker
            worker.completed_washes += 1
            worker.is_available = True
            worker.save(update_fields=['completed_washes', 'is_available', 'updated_at'])
            try:
                payment = wash_request.payment
                if payment.payment_method == 'cash' and payment.status != 'paid':
                    payment.status = 'paid'
                    payment.paid_at = now
                    payment.save(update_fields=['status', 'paid_at', 'updated_at'])
                if payment.status == 'paid':
                    settle_completed_payment(payment)
            except CarWashPayment.DoesNotExist:
                pass

        return Response({'success': True, 'request': self.get_serializer(wash_request).data})

    @action(detail=True, methods=['get'])
    def tracking(self, request, pk=None):
        wash_request = self.get_object()
        location = None
        if wash_request.assigned_worker:
            location = CarWashProviderLocation.objects.filter(
                worker=wash_request.assigned_worker,
                is_active=True,
            ).first()
        return Response({
            'success': True,
            'request': self.get_serializer(wash_request).data,
            'provider_location': CarWashProviderLocationSerializer(location).data if location else None,
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_provider_location(request):
    worker = get_object_or_404(CarWashWorker, user=request.user, is_active=True)
    serializer = ProviderLocationUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    location, _ = CarWashProviderLocation.objects.update_or_create(
        worker=worker,
        defaults={
            'latitude': data['latitude'],
            'longitude': data['longitude'],
            'heading': data.get('heading'),
            'speed_kph': data.get('speed_kph'),
            'accuracy_m': data.get('accuracy_m'),
            'is_active': True,
            'recorded_at': timezone.now(),
        },
    )
    return Response({'success': True, 'location': CarWashProviderLocationSerializer(location).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment(request, request_id):
    wash_request = get_object_or_404(CarWashRequest, id=request_id, customer=request.user)
    if hasattr(wash_request, 'payment'):
        return Response({'success': False, 'error': 'Payment already exists for this request.'}, status=400)

    serializer = CreatePaymentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    method = serializer.validated_data['payment_method']
    gateway_code = serializer.validated_data.get('gateway_code', '')

    gateway_obj = None
    settlement_mode = 'cash' if method == 'cash' else 'platform_collects'

    if method != 'cash':
        if gateway_code:
            gateway_obj = get_object_or_404(PaymentGateway, code=gateway_code, is_active=True)
        else:
            capability = {
                'card': 'supports_card',
                'eft': 'supports_eft',
                'wallet': 'supports_wallet',
            }[method]
            gateway_obj = PaymentGateway.objects.filter(is_active=True, **{capability: True}).order_by('priority').first()
            if not gateway_obj:
                return Response({'success': False, 'error': f'No active gateway supports {method}.'}, status=400)
        if gateway_obj.supports_split_payments:
            settlement_mode = 'gateway_split'

    quote = wash_request.quote
    payment = CarWashPayment.objects.create(
        wash_request=wash_request,
        gateway=gateway_obj,
        payment_method=method,
        settlement_mode=settlement_mode,
        currency=quote.currency,
        gross_amount=quote.total,
        platform_commission=quote.platform_commission,
        provider_amount=quote.provider_amount,
    )

    if method == 'cash':
        gateway = get_gateway('cash')
        result = gateway.initialize_payment(payment, request)
        return Response({'success': True, 'payment': CarWashPaymentSerializer(payment).data, **result}, status=201)

    attempt = PaymentAttempt.objects.create(
        payment=payment,
        gateway=gateway_obj,
        amount=payment.gross_amount,
        status='created',
    )

    try:
        gateway = get_gateway(gateway_obj.code)
        result = gateway.initialize_payment(payment, request)
        attempt.status = 'initialized'
        attempt.response_data = result
        attempt.save(update_fields=['status', 'response_data', 'updated_at'])
        return Response({'success': True, 'payment': CarWashPaymentSerializer(payment).data, **result}, status=201)
    except Exception as exc:
        attempt.status = 'failed'
        attempt.response_data = {'error': str(exc)}
        attempt.save(update_fields=['status', 'response_data', 'updated_at'])
        payment.status = 'failed'
        payment.save(update_fields=['status', 'updated_at'])
        return Response({'success': False, 'error': str(exc), 'payment': CarWashPaymentSerializer(payment).data}, status=400)


class PaymentGatewayViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentGateway.objects.filter(is_active=True)
    serializer_class = PaymentGatewaySerializer
    permission_classes = [AllowAny]


class CarWashReviewViewSet(viewsets.ModelViewSet):
    serializer_class = CarWashReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CarWashReview.objects.filter(Q(customer=self.request.user) | Q(business__owner=self.request.user))

    def perform_create(self, serializer):
        wash_request = serializer.validated_data['wash_request']
        if wash_request.customer_id != self.request.user.id or wash_request.status != 'completed':
            raise ValueError('You can only review your own completed wash.')
        serializer.save(
            customer=self.request.user,
            business=wash_request.business,
            worker=wash_request.assigned_worker,
        )
