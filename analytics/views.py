from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Avg, Count, Max, Min, Sum, Q
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from quizzes.models import Quiz, Question
from attempts.models import QuizAttempt, AttemptAnswer
from .serializers import (
    UserStatsSerializer, CategoryPerformanceSerializer,
    QuizStatsSerializer, LeaderboardEntrySerializer
)
from django.core.cache import cache

User = get_user_model()

class UserStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # Get all completed attempts for this user
        attempts = QuizAttempt.objects.filter(user=user)
        completed_attempts = attempts.filter(status=QuizAttempt.Status.COMPLETED)
        
        # Aggregate stats
        stats = completed_attempts.aggregate(
            average_score_percentage=Avg('score_percentage'),
            best_score_percentage=Max('score_percentage'),
        )
        
        # Count total answers and correct answers
        answer_stats = AttemptAnswer.objects.filter(
            attempt__user=user, 
            attempt__status=QuizAttempt.Status.COMPLETED
        ).aggregate(
            total_questions_answered=Count('id'),
            correct_answers_total=Count('id', filter=Q(is_correct=True)),
        )
        
        # Calculate overall accuracy
        total_answered = answer_stats['total_questions_answered'] or 0
        total_correct = answer_stats['correct_answers_total'] or 0
        overall_accuracy = (total_correct / total_answered * 100) if total_answered > 0 else None
        
        data = {
            'total_quizzes_attempted': attempts.count(),
            'total_completed': completed_attempts.count(),
            'total_in_progress': attempts.filter(status=QuizAttempt.Status.IN_PROGRESS).count(),
            'average_score_percentage': stats['average_score_percentage'],
            'best_score_percentage': stats['best_score_percentage'],
            'total_questions_answered': total_answered,
            'correct_answers_total': total_correct,
            'overall_accuracy': overall_accuracy,
        }
        
        serialized = UserStatsSerializer(data).data
        return Response(serialized)

class CategoryPerformanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # Get completed attempts grouped by quiz category
        category_stats = (
            QuizAttempt.objects
            .filter(user=user, status=QuizAttempt.Status.COMPLETED)
            .values('quiz__category__id', 'quiz__category__name')
            .annotate(
                quizzes_attempted=Count('quiz', distinct=True),
                average_score=Avg('score_percentage'),
                best_score=Max('score_percentage'),
                total_attempts=Count('id'),
            )
            .order_by('-average_score')
        )
        
        data = [
            {
                'category_id': stat['quiz__category__id'],
                'category_name': stat['quiz__category__name'] or 'Uncategorized',
                'quizzes_attempted': stat['quizzes_attempted'],
                'average_score': stat['average_score'],
                'best_score': stat['best_score'],
                'total_attempts': stat['total_attempts'],
            }
            for stat in category_stats
        ]
        
        serialized = CategoryPerformanceSerializer(data, many=True).data
        return Response(serialized)

class QuizStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        
        # Only quiz owner or admin can see quiz stats
        if quiz.created_by != request.user and not request.user.is_admin:
            return Response(
                {'error': 'permission_denied', 'message': 'You do not have permission to view these stats.'},
                status=status.HTTP_403_FORBIDDEN
            )
        # Permission check (already exists)
        if quiz.created_by != request.user and not request.user.is_admin:
            return Response(...)


        cache_key = f'quiz_stats_{quiz_id}'
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        # Rest of computation stays the same...
        # Aggregate attempt stats
        all_attempts = QuizAttempt.objects.filter(quiz=quiz)
        completed = all_attempts.filter(status=QuizAttempt.Status.COMPLETED)
        
        attempt_stats = completed.aggregate(
            average_score=Avg('score_percentage'),
            highest_score=Max('score_percentage'),
            lowest_score=Min('score_percentage'),
        )
        
        total_attempts = all_attempts.count()
        total_completed = completed.count()
        completion_rate = (total_completed / total_attempts * 100) if total_attempts > 0 else None
        
        # Per-question breakdown
        questions = quiz.questions.all()
        question_breakdown = []
        for q in questions:
            answer_stats = AttemptAnswer.objects.filter(
                question=q,
                attempt__status=QuizAttempt.Status.COMPLETED
            ).aggregate(
                total_answers=Count('id'),
                correct_count=Count('id', filter=Q(is_correct=True)),
            )
            total = answer_stats['total_answers'] or 0
            correct = answer_stats['correct_count'] or 0
            question_breakdown.append({
                'question_id': q.id,
                'question_text': q.question_text,
                'total_answers': total,
                'correct_count': correct,
                'accuracy_percentage': round((correct / total * 100), 2) if total > 0 else 0,
            })
        
        data = {
            'quiz_id': quiz.id,
            'quiz_title': quiz.title,
            'total_attempts': total_attempts,
            'total_completed': total_completed,
            'completion_rate': completion_rate,
            'average_score': attempt_stats['average_score'],
            'highest_score': attempt_stats['highest_score'],
            'lowest_score': attempt_stats['lowest_score'],
            'question_breakdown': question_breakdown,
        }
        
        serialized = QuizStatsSerializer(data).data
        cache.set(cache_key, serialized, timeout=120)
        return Response(serialized)

class SystemStatsView(APIView):
    """System-wide analytics — admin only"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.is_admin:
            return Response(
                {'error': 'permission_denied', 'message': 'Admin access required.'},
                status=status.HTTP_403_FORBIDDEN
            )

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_quizzes = Quiz.objects.count()
        published_quizzes = Quiz.objects.filter(is_published=True).count()
        total_attempts = QuizAttempt.objects.count()
        completed_attempts = QuizAttempt.objects.filter(status=QuizAttempt.Status.COMPLETED).count()

        avg_score = QuizAttempt.objects.filter(
            status=QuizAttempt.Status.COMPLETED
        ).aggregate(avg=Avg('score_percentage'))['avg']

        popular_quizzes = (
            Quiz.objects.filter(attempts__isnull=False)
            .annotate(attempt_count=Count('attempts'))
            .order_by('-attempt_count')[:5]
            .values('id', 'title', 'attempt_count')
        )

        completion_rate = (completed_attempts / total_attempts * 100) if total_attempts > 0 else 0

        data = {
            'total_users': total_users,
            'active_users': active_users,
            'total_quizzes': total_quizzes,
            'published_quizzes': published_quizzes,
            'total_attempts': total_attempts,
            'completed_attempts': completed_attempts,
            'completion_rate': round(completion_rate, 2),
            'average_score': avg_score,
            'most_popular_quizzes': list(popular_quizzes),
        }

        return Response(data)


class LeaderboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        category_id = request.query_params.get('category')
        # Base queryset: users with completed attempts
        attempts_qs = QuizAttempt.objects.filter(status=QuizAttempt.Status.COMPLETED)

        if category_id:
            attempts_qs = attempts_qs.filter(quiz__category_id=category_id)
        
        # Aggregate per user
        leaderboard = (
            attempts_qs
            .values('user__id', 'user__username')
            .annotate(
                total_quizzes_completed=Count('id'),
                average_score=Avg('score_percentage'),
                total_correct_answers=Sum('correct_answers'),
            )
            .order_by('-average_score', '-total_quizzes_completed')[:20]  # Top 20
        )
        
        data = [
            {
                'rank': idx + 1,
                'user_id': entry['user__id'],
                'username': entry['user__username'],
                'total_quizzes_completed': entry['total_quizzes_completed'],
                'average_score': entry['average_score'],
                'total_correct_answers': entry['total_correct_answers'] or 0,
            }
            for idx, entry in enumerate(leaderboard)
        ]
        
        serialized = LeaderboardEntrySerializer(data, many=True).data
        return Response(serialized)
