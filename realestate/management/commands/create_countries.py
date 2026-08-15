# Create a file: realestate/management/commands/create_countries.py

from django.core.management.base import BaseCommand
from realestate.models import Country

class Command(BaseCommand):
    help = 'Create all countries with their calling codes'

    def handle(self, *args, **options):
        countries = [
            # Africa
            {'name': 'South Africa', 'code': 'ZA', 'code3': 'ZAF', 'calling_code': '27', 'flag': '🇿🇦'},
            {'name': 'Nigeria', 'code': 'NG', 'code3': 'NGA', 'calling_code': '234', 'flag': '🇳🇬'},
            {'name': 'Egypt', 'code': 'EG', 'code3': 'EGY', 'calling_code': '20', 'flag': '🇪🇬'},
            {'name': 'Kenya', 'code': 'KE', 'code3': 'KEN', 'calling_code': '254', 'flag': '🇰🇪'},
            {'name': 'Ghana', 'code': 'GH', 'code3': 'GHA', 'calling_code': '233', 'flag': '🇬🇭'},
            {'name': 'Morocco', 'code': 'MA', 'code3': 'MAR', 'calling_code': '212', 'flag': '🇲🇦'},
            {'name': 'Tanzania', 'code': 'TZ', 'code3': 'TZA', 'calling_code': '255', 'flag': '🇹🇿'},
            {'name': 'Uganda', 'code': 'UG', 'code3': 'UGA', 'calling_code': '256', 'flag': '🇺🇬'},
            {'name': 'Zambia', 'code': 'ZM', 'code3': 'ZMB', 'calling_code': '260', 'flag': '🇿🇲'},
            {'name': 'Zimbabwe', 'code': 'ZW', 'code3': 'ZWE', 'calling_code': '263', 'flag': '🇿🇼'},
            {'name': 'Botswana', 'code': 'BW', 'code3': 'BWA', 'calling_code': '267', 'flag': '🇧🇼'},
            {'name': 'Namibia', 'code': 'NA', 'code3': 'NAM', 'calling_code': '264', 'flag': '🇳🇦'},
            {'name': 'Mozambique', 'code': 'MZ', 'code3': 'MOZ', 'calling_code': '258', 'flag': '🇲🇿'},
            {'name': 'Angola', 'code': 'AO', 'code3': 'AGO', 'calling_code': '244', 'flag': '🇦🇴'},
            {'name': 'Ethiopia', 'code': 'ET', 'code3': 'ETH', 'calling_code': '251', 'flag': '🇪🇹'},
            
            # North America
            {'name': 'United States', 'code': 'US', 'code3': 'USA', 'calling_code': '1', 'flag': '🇺🇸'},
            {'name': 'Canada', 'code': 'CA', 'code3': 'CAN', 'calling_code': '1', 'flag': '🇨🇦'},
            {'name': 'Mexico', 'code': 'MX', 'code3': 'MEX', 'calling_code': '52', 'flag': '🇲🇽'},
            
            # South America
            {'name': 'Brazil', 'code': 'BR', 'code3': 'BRA', 'calling_code': '55', 'flag': '🇧🇷'},
            {'name': 'Argentina', 'code': 'AR', 'code3': 'ARG', 'calling_code': '54', 'flag': '🇦🇷'},
            {'name': 'Colombia', 'code': 'CO', 'code3': 'COL', 'calling_code': '57', 'flag': '🇨🇴'},
            {'name': 'Chile', 'code': 'CL', 'code3': 'CHL', 'calling_code': '56', 'flag': '🇨🇱'},
            {'name': 'Peru', 'code': 'PE', 'code3': 'PER', 'calling_code': '51', 'flag': '🇵🇪'},
            
            # Europe
            {'name': 'United Kingdom', 'code': 'GB', 'code3': 'GBR', 'calling_code': '44', 'flag': '🇬🇧'},
            {'name': 'France', 'code': 'FR', 'code3': 'FRA', 'calling_code': '33', 'flag': '🇫🇷'},
            {'name': 'Germany', 'code': 'DE', 'code3': 'DEU', 'calling_code': '49', 'flag': '🇩🇪'},
            {'name': 'Italy', 'code': 'IT', 'code3': 'ITA', 'calling_code': '39', 'flag': '🇮🇹'},
            {'name': 'Spain', 'code': 'ES', 'code3': 'ESP', 'calling_code': '34', 'flag': '🇪🇸'},
            {'name': 'Portugal', 'code': 'PT', 'code3': 'PRT', 'calling_code': '351', 'flag': '🇵🇹'},
            {'name': 'Netherlands', 'code': 'NL', 'code3': 'NLD', 'calling_code': '31', 'flag': '🇳🇱'},
            {'name': 'Switzerland', 'code': 'CH', 'code3': 'CHE', 'calling_code': '41', 'flag': '🇨🇭'},
            {'name': 'Sweden', 'code': 'SE', 'code3': 'SWE', 'calling_code': '46', 'flag': '🇸🇪'},
            {'name': 'Norway', 'code': 'NO', 'code3': 'NOR', 'calling_code': '47', 'flag': '🇳🇴'},
            {'name': 'Denmark', 'code': 'DK', 'code3': 'DNK', 'calling_code': '45', 'flag': '🇩🇰'},
            {'name': 'Finland', 'code': 'FI', 'code3': 'FIN', 'calling_code': '358', 'flag': '🇫🇮'},
            {'name': 'Poland', 'code': 'PL', 'code3': 'POL', 'calling_code': '48', 'flag': '🇵🇱'},
            {'name': 'Greece', 'code': 'GR', 'code3': 'GRC', 'calling_code': '30', 'flag': '🇬🇷'},
            {'name': 'Turkey', 'code': 'TR', 'code3': 'TUR', 'calling_code': '90', 'flag': '🇹🇷'},
            {'name': 'Russia', 'code': 'RU', 'code3': 'RUS', 'calling_code': '7', 'flag': '🇷🇺'},
            {'name': 'Ukraine', 'code': 'UA', 'code3': 'UKR', 'calling_code': '380', 'flag': '🇺🇦'},
            
            # Asia
            {'name': 'China', 'code': 'CN', 'code3': 'CHN', 'calling_code': '86', 'flag': '🇨🇳'},
            {'name': 'India', 'code': 'IN', 'code3': 'IND', 'calling_code': '91', 'flag': '🇮🇳'},
            {'name': 'Japan', 'code': 'JP', 'code3': 'JPN', 'calling_code': '81', 'flag': '🇯🇵'},
            {'name': 'South Korea', 'code': 'KR', 'code3': 'KOR', 'calling_code': '82', 'flag': '🇰🇷'},
            {'name': 'Singapore', 'code': 'SG', 'code3': 'SGP', 'calling_code': '65', 'flag': '🇸🇬'},
            {'name': 'Malaysia', 'code': 'MY', 'code3': 'MYS', 'calling_code': '60', 'flag': '🇲🇾'},
            {'name': 'Philippines', 'code': 'PH', 'code3': 'PHL', 'calling_code': '63', 'flag': '🇵🇭'},
            {'name': 'Indonesia', 'code': 'ID', 'code3': 'IDN', 'calling_code': '62', 'flag': '🇮🇩'},
            {'name': 'Thailand', 'code': 'TH', 'code3': 'THA', 'calling_code': '66', 'flag': '🇹🇭'},
            {'name': 'Vietnam', 'code': 'VN', 'code3': 'VNM', 'calling_code': '84', 'flag': '🇻🇳'},
            {'name': 'Pakistan', 'code': 'PK', 'code3': 'PAK', 'calling_code': '92', 'flag': '🇵🇰'},
            {'name': 'Bangladesh', 'code': 'BD', 'code3': 'BGD', 'calling_code': '880', 'flag': '🇧🇩'},
            {'name': 'Saudi Arabia', 'code': 'SA', 'code3': 'SAU', 'calling_code': '966', 'flag': '🇸🇦'},
            {'name': 'UAE', 'code': 'AE', 'code3': 'ARE', 'calling_code': '971', 'flag': '🇦🇪'},
            {'name': 'Israel', 'code': 'IL', 'code3': 'ISR', 'calling_code': '972', 'flag': '🇮🇱'},
            
            # Oceania
            {'name': 'Australia', 'code': 'AU', 'code3': 'AUS', 'calling_code': '61', 'flag': '🇦🇺'},
            {'name': 'New Zealand', 'code': 'NZ', 'code3': 'NZL', 'calling_code': '64', 'flag': '🇳🇿'},
        ]
        
        for country_data in countries:
            country, created = Country.objects.get_or_create(
                code=country_data['code'],
                defaults={
                    'name': country_data['name'],
                    'code3': country_data['code3'],
                    'calling_code': country_data['calling_code'],
                    'flag': country_data['flag'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f"✅ Created: {country}")
            else:
                self.stdout.write(f"⏭️ Already exists: {country}")
        
        self.stdout.write(self.style.SUCCESS('✅ All countries created successfully!'))