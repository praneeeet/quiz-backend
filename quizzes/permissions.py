from rest_framework import permissions

class IsQuizOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a quiz.
    """
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of a quiz or an admin.
    """
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user or (request.user and request.user.is_authenticated and request.user.is_admin)
