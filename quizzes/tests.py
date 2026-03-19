from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from unittest.mock import patch
from .models import Category, Quiz, Question

User = get_user_model()

class QuizzesTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username='admin', email='a@test.com', role='admin')
        self.player = User.objects.create_user(username='player', email='p@test.com', role='player')
        self.other = User.objects.create_user(username='other', email='o@test.com', role='player')
        self.category = Category.objects.create(name="Science")
        self.cat_url = '/api/v1/categories/'
        self.quiz_url = '/api/v1/quizzes/'
        
        # Published quiz by admin
        self.quiz = Quiz.objects.create(
            title="Quiz", topic="Topic", category=self.category,
            created_by=self.admin, is_published=True, status=Quiz.Status.READY
        )
        Question.objects.create(
            quiz=self.quiz, question_text="Q1", options=["A","B","C","D"],
            correct_option=0, explanation="Ex1", order=1
        )

    def test_admin_can_create_category(self):
        # Admin can create categories
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.cat_url, {'name': 'History'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_player_cannot_create_category(self):
        # Random player cannot create categories
        self.client.force_authenticate(user=self.player)
        response = self.client.post(self.cat_url, {'name': 'Geography'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('quizzes.views.QuizGenerator')
    def test_quiz_creation_mocks_ai(self, mock_gen):
        # Quiz creation should trigger AI generation (mocked)
        self.client.force_authenticate(user=self.player)
        data = {'title': 'Space', 'topic': 'Space', 'number_of_questions': 2}
        response = self.client.post(self.quiz_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(mock_gen.return_value.generate_questions.called)

    def test_admin_sees_all_quizzes_in_list(self):
        # Unpublihsed quiz should be visible to admin
        Quiz.objects.create(title="Private", created_by=self.player, is_published=False)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.quiz_url)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 2)

    def test_player_sees_only_published_or_own_quizzes(self):
        # Player should NOT see unpublished quizzes of others
        Quiz.objects.create(title="Secret", created_by=self.other, is_published=False)
        self.client.force_authenticate(user=self.player)
        response = self.client.get(self.quiz_url)
        results = response.data.get('results', response.data)
        # Should only see the global published quiz (1)
        self.assertEqual(len(results), 1)

    def test_quiz_detail_hides_answers_for_strangers(self):
        # Strangers cannot see correct answers
        self.client.force_authenticate(user=self.other)
        response = self.client.get(f"{self.quiz_url}{self.quiz.id}/")
        # Access first question
        question = response.data['questions'][0]
        self.assertNotIn('correct_option', question)

    def test_quiz_detail_shows_answers_for_owner(self):
        # Owners (admin in this case) can see their own quiz answers
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"{self.quiz_url}{self.quiz.id}/")
        question = response.data['questions'][0]
        self.assertIn('correct_option', question)

    def test_publish_toggle_works(self):
        # Publishing a quiz toggles its state
        self.client.force_authenticate(user=self.admin)
        self.client.post(f"{self.quiz_url}{self.quiz.id}/publish/")
        self.quiz.refresh_from_db()
        self.assertFalse(self.quiz.is_published)
