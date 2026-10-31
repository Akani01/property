import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import AppearancePreference

@require_http_methods(["GET", "POST"])
def appearance_preference(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=401)
    if request.method == "GET":
        obj = AppearancePreference.objects.filter(user=request.user).first()
        return JsonResponse({"authenticated": True, "theme": obj.theme if obj else None})
    try:
        theme = json.loads(request.body.decode("utf-8")).get("theme")
    except (ValueError, UnicodeDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    if theme not in ("light", "dark", "system"):
        return JsonResponse({"error": "Invalid theme"}, status=400)
    obj, _ = AppearancePreference.objects.update_or_create(user=request.user, defaults={"theme": theme})
    return JsonResponse({"authenticated": True, "theme": obj.theme})
