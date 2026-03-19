from rest_framework import permissions

class IsAttemptOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a quiz attempt to interact with it.
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
