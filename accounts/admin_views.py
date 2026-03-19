from rest_framework import status, permissions
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from accounts.permissions import IsAdmin
from .serializers import AdminUserSerializer

User = get_user_model()


class AdminUserListView(ListAPIView):
    """List all users — admin only"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()

    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')

        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(username__icontains=search) | Q(email__icontains=search)
            )

        return queryset


class AdminUserDetailView(RetrieveUpdateAPIView):
    """View or update any user — admin only"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()
    lookup_field = 'id'

    def patch(self, request, *args, **kwargs):
        user = self.get_object()

        # Prevent admin from deactivating themselves
        if user == request.user and request.data.get('is_active') == False:
            return Response(
                {'error': 'invalid_operation', 'message': 'You cannot deactivate your own account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().patch(request, *args, **kwargs)
