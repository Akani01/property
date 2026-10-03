from django.rest_framework import permissions

class IsAdvertiserOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow advertisers to edit their own ads.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.advertiser == request.user

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to approve/reject ads.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and (request.user.is_staff or request.user.is_superuser)