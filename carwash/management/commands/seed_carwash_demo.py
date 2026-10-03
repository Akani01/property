from decimal import Decimal

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from carwash.models import (
    CarWashBusiness,
    CarWashProviderLocation,
    CarWashService,
    CarWashWorker,
    ServiceVehiclePrice,
    VehicleType,
)


class Command(BaseCommand):
    help = 'Create demo OppoGlobe car wash data using normal addresses; Google resolves coordinates automatically.'

    def geocode(self, address):
        key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        if not key:
            return None
        try:
            r = requests.get(
                'https://maps.googleapis.com/maps/api/geocode/json',
                params={'address': address, 'key': key},
                timeout=8,
            )
            data = r.json()
            if data.get('status') == 'OK' and data.get('results'):
                first = data['results'][0]
                loc = first['geometry']['location']
                return {
                    'formatted_address': first.get('formatted_address', address),
                    'place_id': first.get('place_id', ''),
                    'latitude': Decimal(str(loc['lat'])),
                    'longitude': Decimal(str(loc['lng'])),
                }
        except requests.RequestException:
            return None
        return None

    def handle(self, *args, **options):
        User = get_user_model()
        demos = [
            {
                'username': 'sparklewash', 'email': 'sparkle@example.com', 'first_name': 'Thabo',
                'name': 'Sparkle Mobile Wash', 'address': 'Rosebank, Johannesburg, South Africa',
                'mode': 'both', 'radius': '25.00', 'free_km': '5.00', 'travel': '4.50', 'commission': '15.00',
                'vehicles': ['Hatchback', 'Sedan', 'SUV', 'Bakkie'],
                'services': [('Express Wash', 25, True, True), ('Full Wash', 45, True, True), ('Interior Deep Clean', 90, True, True)],
                'prices': {'Express Wash': [80, 90, 120, 130], 'Full Wash': [145, 160, 210, 230], 'Interior Deep Clean': [320, 390, 480, 520]},
            },
            {
                'username': 'aquamobile', 'email': 'aqua@example.com', 'first_name': 'Kabelo',
                'name': 'AquaGo Car Care', 'address': 'Sandton, Johannesburg, South Africa',
                'mode': 'mobile', 'radius': '30.00', 'free_km': '7.00', 'travel': '5.00', 'commission': '15.00',
                'vehicles': ['Sedan', 'SUV', 'Bakkie', 'Minibus / Taxi'],
                'services': [('Quick Wash', 20, True, False), ('Wash + Vacuum', 40, True, False), ('Mobile Valet', 80, True, False)],
                'prices': {'Quick Wash': [85, 110, 125, 180], 'Wash + Vacuum': [150, 190, 210, 280], 'Mobile Valet': [290, 360, 390, 520]},
            },
            {
                'username': 'freshride', 'email': 'freshride@example.com', 'first_name': 'Neo',
                'name': 'FreshRide Auto Spa', 'address': 'Midrand, Gauteng, South Africa',
                'mode': 'both', 'radius': '35.00', 'free_km': '8.00', 'travel': '4.00', 'commission': '12.50',
                'vehicles': ['Sedan', 'SUV', 'Motorcycle', 'Van'],
                'services': [('Essential Clean', 25, True, True), ('Complete Clean', 55, True, True), ('Signature Detail', 150, True, True)],
                'prices': {'Essential Clean': [95, 125, 65, 150], 'Complete Clean': [180, 230, 110, 290], 'Signature Detail': [700, 850, 350, 980]},
            },
        ]

        for demo in demos:
            user, created = User.objects.get_or_create(
                username=demo['username'],
                defaults={'email': demo['email'], 'first_name': demo['first_name']},
            )
            if created:
                user.set_password('Test12345!')
                user.save(update_fields=['password'])

            loc = self.geocode(demo['address']) or {}
            business, _ = CarWashBusiness.objects.update_or_create(
                owner=user,
                name=demo['name'],
                defaults={
                    'email': demo['email'],
                    'phone': '',
                    'description': 'Demo car wash provider for OppoGlobe Wash.',
                    'fulfilment_mode': demo['mode'],
                    'is_active': True,
                    'is_verified': True,
                    'is_accepting_jobs': True,
                    'address': loc.get('formatted_address', demo['address']),
                    'formatted_address': loc.get('formatted_address', demo['address']),
                    'place_id': loc.get('place_id', ''),
                    'latitude': loc.get('latitude'),
                    'longitude': loc.get('longitude'),
                    'service_radius_km': Decimal(demo['radius']),
                    'free_travel_km': Decimal(demo['free_km']),
                    'travel_fee_per_km': Decimal(demo['travel']),
                    'commission_rate': Decimal(demo['commission']),
                },
            )

            worker, _ = CarWashWorker.objects.get_or_create(
                business=business,
                user=user,
                defaults={'display_name': demo['first_name'], 'is_active': True, 'is_online': True, 'is_available': True},
            )
            worker.is_online = True
            worker.is_available = True
            worker.save(update_fields=['is_online', 'is_available', 'updated_at'])

            if business.latitude is not None and business.longitude is not None:
                CarWashProviderLocation.objects.update_or_create(
                    worker=worker,
                    defaults={
                        'latitude': business.latitude,
                        'longitude': business.longitude,
                        'is_active': True,
                        'recorded_at': timezone.now(),
                    },
                )

            vehicle_objs = []
            for i, name in enumerate(demo['vehicles'], 1):
                vehicle, _ = VehicleType.objects.update_or_create(
                    business=business,
                    name=name,
                    defaults={'sort_order': i, 'is_active': True},
                )
                vehicle_objs.append(vehicle)

            service_objs = {}
            for i, (name, minutes, mobile, onsite) in enumerate(demo['services'], 1):
                service, _ = CarWashService.objects.update_or_create(
                    business=business,
                    name=name,
                    defaults={
                        'estimated_minutes': minutes,
                        'mobile_available': mobile,
                        'onsite_available': onsite,
                        'sort_order': i,
                        'is_active': True,
                    },
                )
                service_objs[name] = service

            for service_name, amounts in demo['prices'].items():
                service = service_objs[service_name]
                for vehicle, amount in zip(vehicle_objs, amounts):
                    ServiceVehiclePrice.objects.update_or_create(
                        business=business,
                        service=service,
                        vehicle_type=vehicle,
                        defaults={'price': Decimal(str(amount)), 'currency': 'ZAR', 'is_active': True},
                    )

            self.stdout.write(self.style.SUCCESS(f'Created/updated {business.name}'))

        self.stdout.write(self.style.SUCCESS('OppoGlobe Wash demo data is ready.'))
