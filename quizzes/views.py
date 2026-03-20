from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.cache import cache
from django.db.models import Count, Q
from .models import Category, Quiz, Question
from .serializers import (
    CategorySerializer, QuizListSerializer, QuizDetailSerializer,
    QuizDetailPlayerSerializer, QuizCreateSerializer, QuizUpdateSerializer
)
from accounts.permissions import IsAdmin
from .permissions import IsOwnerOrAdmin, IsQuizOwner
from .throttles import QuizCreateThrottle

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.annotate(quiz_count=Count('quizzes'))
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated, IsAdmin]
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        cache_key = 'categories_list'
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=300)
        return response

    def perform_create(self, serializer):
        serializer.save()
        cache.delete('categories_list')

    def perform_update(self, serializer):
        serializer.save()
        cache.delete('categories_list')

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete('categories_list')

class QuizViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']
    def get_throttles(self):
        if self.action == 'create':
            return [QuizCreateThrottle()]
        return super().get_throttles()

    
    def get_queryset(self):
        user = self.request.user
        queryset = Quiz.objects.select_related('category', 'created_by').prefetch_related('questions')

        if self.action == 'list':
            if user.is_admin:
                pass  # Admin sees all quizzes, no filter
            else:
                queryset = queryset.filter(
                    Q(is_published=True, status=Quiz.Status.READY) | Q(created_by=user)
                ).distinct()
        elif self.action == 'my_quizzes':
            queryset = queryset.filter(created_by=user)
        
        # Manual Filtering
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
            
        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
            
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(topic__icontains=search)
            )

        return queryset

    def get_serializer_class(self):
        if self.action in ['list', 'my_quizzes']:
            return QuizListSerializer
        if self.action == 'create':
            return QuizCreateSerializer
        if self.action in ['update', 'partial_update']:
            return QuizUpdateSerializer
        return QuizListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.is_admin or instance.created_by == request.user:
            serializer = QuizDetailSerializer(instance)
        else:
            serializer = QuizDetailPlayerSerializer(instance)
        return Response(serializer.data)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'my_quizzes']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        else:
            # update, partial_update, destroy, publish, regenerate
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        quiz = serializer.save(created_by=self.request.user)
        try:
            from ai_service.tasks import generate_quiz_questions_task
            generate_quiz_questions_task.delay(str(quiz.id))
        except Exception:
            from ai_service.generator import QuizGenerator
            generator = QuizGenerator()
            generator.generate_questions(quiz)

    @action(detail=False, methods=['get'])
    def my_quizzes(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        quiz = self.get_object()
        quiz.is_published = not quiz.is_published
        quiz.save()
        return Response({
            "status": "success",
            "is_published": quiz.is_published,
            "message": f"Quiz {'published' if quiz.is_published else 'unpublished'} successfully."
        })

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        quiz = self.get_object()
        if quiz.status != Quiz.Status.FAILED:
            return Response(
                {"error": "invalid_operation", "message": "Only quizzes with 'failed' status can be regenerated."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        Question.objects.filter(quiz=quiz).delete()
        quiz.status = Quiz.Status.PENDING
        quiz.save()
        
        try:
            from ai_service.tasks import generate_quiz_questions_task
            generate_quiz_questions_task.delay(str(quiz.id))
        except Exception:
            from ai_service.generator import QuizGenerator
            generator = QuizGenerator()
            generator.generate_questions(quiz)
            quiz.refresh_from_db()
        
        return Response({
            "status": "success",
            "message": "Quiz regeneration started.",
            "quiz_status": quiz.status
        })
