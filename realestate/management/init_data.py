from django.core.management.base import BaseCommand
from realestate.models import PropertyCategory, PropertyFeature


class Command(BaseCommand):
    help = 'Initialize real estate data'

    def handle(self, *args, **options):
        # Create categories
        categories = [
            {'name': 'Residential', 'category_type': 'residential', 'is_system': True},
            {'name': 'Commercial', 'category_type': 'commercial', 'is_system': True},
            {'name': 'Student Housing', 'category_type': 'student_housing', 'is_system': True},
            {'name': 'Hospitality', 'category_type': 'hospitality', 'is_system': True},
            {'name': 'Retail', 'category_type': 'retail', 'is_system': True},
            {'name': 'Industrial', 'category_type': 'industrial', 'is_system': True},
            {'name': 'Entertainment', 'category_type': 'entertainment', 'is_system': True},
        ]
        
        for cat in categories:
            obj, created = PropertyCategory.objects.get_or_create(name=cat['name'], defaults=cat)
            self.stdout.write(f"{'Created' if created else 'Found'}: {cat['name']}")
        
        # Create features
        features = [
            'Swimming Pool', 'Garage', 'Garden', 'Security System',
            'Air Conditioning', 'Solar Panels', 'Balcony', 'Fireplace',
            'WiFi', 'Smart Home', 'Gym', 'Playground', 'Clubhouse',
            'Elevator', 'Parking', 'Pet Friendly', 'Furnished',
            'DStv', 'Generator', 'Borehole', 'Study', 'Scenic View'
        ]
        
        for feature in features:
            obj, created = PropertyFeature.objects.get_or_create(name=feature, defaults={'is_active': True})
            self.stdout.write(f"{'Created' if created else 'Found'}: {feature}")
        
        self.stdout.write(self.style.SUCCESS('Real estate data initialized successfully!'))