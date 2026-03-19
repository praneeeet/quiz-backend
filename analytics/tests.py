from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from quizzes.models import Quiz, Question
from attempts.models import QuizAttempt, AttemptAnswer

User = get_user_model()

class AnalyticsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username='admin', email='a@test.com', role='admin')
        self.player = User.objects.create_user(username='player', email='p@test.com', role='player')
        self.other = User.objects.create_user(username='other', email='o@test.com', role='player')
        self.quiz = Quiz.objects.create(
            title="Quiz", topic="Topic", created_by=self.admin,
            is_published=True, status=Quiz.Status.READY
        )
        self.q1 = Question.objects.create(
            quiz=self.quiz, question_text="Q1", options=["A","B","C","D"],
            correct_option=0, order=1
        )
        self.me_url = '/api/v1/analytics/me/'
        self.quiz_url = f'/api/v1/analytics/quizzes/{self.quiz.id}/'
        self.system_url = '/api/v1/analytics/system/'
        self.leaderboard_url = '/api/v1/analytics/leaderboard/'

    def test_user_stats_empty_for_new_user(self):
        # New users should have 0 stats
        self.client.force_authenticate(user=self.player)
        response = self.client.get(self.me_url)
        self.assertEqual(response.data['total_completed'], 0)
        self.assertIsNone(response.data['average_score_percentage'])

    def test_user_stats_updated_after_completion(self):
        # Stats should update when a quiz is completed
        self.client.force_authenticate(user=self.player)
        att = QuizAttempt.objects.create(user=self.player, quiz=self.quiz, total_questions=1)
        # Mock correct answer
        AttemptAnswer.objects.create(attempt=att, question=self.q1, selected_option=0)
        att.calculate_score()
        
        response = self.client.get(self.me_url)
        self.assertEqual(response.data['total_completed'], 1)
        self.assertEqual(float(response.data['average_score_percentage']), 100.0)

    def test_quiz_stats_access_permissions(self):
        # Only owners/admins can see specific quiz stats
        self.client.force_authenticate(user=self.other)
        response = self.client.get(self.quiz_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admin can access
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.quiz_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_system_stats_admin_only(self):
        # System-wide statistics are restricted to admins
        self.client.force_authenticate(user=self.player)
        response = self.client.get(self.system_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.system_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_leaderboard_returns_rankings(self):
        # Leaderboard should return user rankings
        self.client.force_authenticate(user=self.player)
        response = self.client.get(self.leaderboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be an array/list
        self.assertIsInstance(response.data, list)
