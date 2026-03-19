from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from quizzes.models import Quiz, Question
from .models import QuizAttempt, AttemptAnswer
from .serializers import (
    QuizAttemptListSerializer, QuizAttemptDetailSerializer, 
    AttemptAnswerSubmitSerializer, AttemptAnswerDuringSerializer,
    AttemptStartSerializer, AttemptCompleteSerializer
)
from .permissions import IsAttemptOwner
from django.core.cache import cache

class QuizAttemptViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = QuizAttempt.objects.select_related('quiz', 'user').prefetch_related('answers', 'answers__question')
        if self.request.user.is_admin:
            return queryset
        return queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return QuizAttemptListSerializer
        if self.action == 'retrieve':
            return QuizAttemptDetailSerializer
        if self.action == 'start_attempt':
            return AttemptStartSerializer
        if self.action == 'submit_answer':
            return AttemptAnswerSubmitSerializer
        if self.action == 'complete':
            return AttemptCompleteSerializer
        return QuizAttemptListSerializer

    def get_permissions(self):
        if self.action in ['submit_answer', 'complete']:
            permission_classes = [permissions.IsAuthenticated, IsAttemptOwner]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'], url_path='start/(?P<quiz_id>[^/.]+)')
    def start_attempt(self, request, quiz_id=None):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        
        # Validation
        if quiz.status != Quiz.Status.READY:
            return Response({"error": "quiz_not_ready", "message": "Quiz is not ready."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not (quiz.is_published or quiz.created_by == request.user):
            return Response({"error": "quiz_unavailable", "message": "Quiz is not available."}, status=status.HTTP_403_FORBIDDEN)
        
        if QuizAttempt.objects.filter(user=request.user, quiz=quiz, status=QuizAttempt.Status.IN_PROGRESS).exists():
            return Response({"error": "attempt_in_progress", "message": "You already have an in-progress attempt for this quiz."}, status=status.HTTP_409_CONFLICT)
        
        # Create Attempt
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            total_questions=quiz.questions.count(),
            status=QuizAttempt.Status.IN_PROGRESS
        )
        
        serializer = QuizAttemptDetailSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        attempt = self.get_object()
        
        if attempt.status != QuizAttempt.Status.IN_PROGRESS:
            return Response({"error": "attempt_already_completed", "message": "This attempt is already completed."}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AttemptAnswerSubmitSerializer(data=request.data)
        if serializer.is_valid():
            question_id = serializer.validated_data['question_id']
            selected_option = serializer.validated_data.get('selected_option')
            
            question = get_object_or_404(Question, id=question_id, quiz=attempt.quiz)
            
            if AttemptAnswer.objects.filter(attempt=attempt, question=question).exists():
                 return Response({"error": "question_already_answered", "message": "You have already answered this question."}, status=status.HTTP_409_CONFLICT)
            
            answer = AttemptAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_option=selected_option
            )
            
            return Response({
                "answer": AttemptAnswerDuringSerializer(answer).data,
                "progress": {
                    "answered": attempt.answers.count(),
                    "total": attempt.total_questions
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        attempt = self.get_object()
        
        if attempt.status != QuizAttempt.Status.IN_PROGRESS:
            return Response({"error": "attempt_already_completed", "message": "This attempt is already completed."}, status=status.HTTP_400_BAD_REQUEST)
        
        attempt.calculate_score()
        cache.delete(f'quiz_stats_{attempt.quiz.id}')
        serializer = QuizAttemptDetailSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_200_OK)
