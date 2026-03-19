from django.urls import path
from .views import UserStatsView, CategoryPerformanceView, QuizStatsView, LeaderboardView

urlpatterns = [
    path('analytics/me/', UserStatsView.as_view(), name='user-stats'),
    path('analytics/me/categories/', CategoryPerformanceView.as_view(), name='category-performance'),
    path('analytics/quizzes/<uuid:quiz_id>/', QuizStatsView.as_view(), name='quiz-stats'),
    path('analytics/leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]
