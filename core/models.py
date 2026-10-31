from django.conf import settings
from django.db import models

class AppearancePreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appearance_preference")
    theme = models.CharField(max_length=10, choices=[("light", "Light"), ("dark", "Dark"), ("system", "System")], default="system")
    updated_at = models.DateTimeField(auto_now=True)
