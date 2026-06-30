from django.apps import AppConfig
from django.conf import settings


class RealestateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'realestate'
    verbose_name = 'Real Estate Management'
    
    def ready(self):
        # Import signals if real-time tracking is enabled
        if getattr(settings, 'REALESTATE_SETTINGS', {}).get('ENABLE_REAL_TIME_TRACKING', False):
            import realestate.signals  # noqa