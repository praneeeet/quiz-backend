from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from quizzes.models import Quiz, Question
from .models import QuizAttempt

User = get_user_model()

class AttemptsTests(APITestCase):
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
        self.attempts_url = '/api/v1/attempts/'

    def test_start_attempt_hides_answers(self):
        # Starting an attempt should not show correct answers
        self.client.force_authenticate(user=self.player)
        url = f"{self.attempts_url}start/{self.quiz.id}/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('correct_option', response.data['questions'][0])

    def test_player_cannot_start_on_unpublished_quiz(self):
        # Players cannot attempt someone else's unpublished quiz
        self.quiz.is_published = False
        self.quiz.save()
        self.client.force_authenticate(user=self.player)
        url = f"{self.attempts_url}start/{self.quiz.id}/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_attempt_forbidden(self):
        # Cannot start a new attempt if one is already in progress
        QuizAttempt.objects.create(user=self.player, quiz=self.quiz, total_questions=1)
        self.client.force_authenticate(user=self.player)
        url = f"{self.attempts_url}start/{self.quiz.id}/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_submit_answer_works(self):
        # Submitting an answer should return successful (201)
        self.client.force_authenticate(user=self.player)
        att = QuizAttempt.objects.create(user=self.player, quiz=self.quiz, total_questions=1)
        url = f"{self.attempts_url}{att.id}/submit_answer/"
        response = self.client.post(url, {'question_id': str(self.q1.id), 'selected_option': 0})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_complete_calculates_score_reveals_answers(self):
        # Completing an attempt should reveal correct answers and set the score
        self.client.force_authenticate(user=self.player)
        att = QuizAttempt.objects.create(user=self.player, quiz=self.quiz, total_questions=1)
        # Manually submit the answer to avoid prefetch issues in view
        self.client.post(f"{self.attempts_url}{att.id}/submit_answer/", {'question_id': str(self.q1.id), 'selected_option': 0})
        # Call complete
        self.client.post(f"{self.attempts_url}{att.id}/complete/")
        # Fetch fresh detail to handle view state correctly
        response = self.client.get(f"{self.attempts_url}{att.id}/")
        
        # Verify score and answers revealed
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['correct_answers'], 1)
        self.assertIn('correct_option', response.data['questions'][0])

    def test_submit_after_completion_fails(self):
        # Cannot submit answers once the quiz is completed
        self.client.force_authenticate(user=self.player)
        att = QuizAttempt.objects.create(user=self.player, quiz=self.quiz, total_questions=1, status='completed')
        url = f"{self.attempts_url}{att.id}/submit_answer/"
        response = self.client.post(url, {'question_id': str(self.q1.id), 'selected_option': 0})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_player_visibility(self):
        # Player only sees their own attempts
        QuizAttempt.objects.create(user=self.player, quiz=self.quiz, total_questions=1)
        QuizAttempt.objects.create(user=self.other, quiz=self.quiz, total_questions=1)
        self.client.force_authenticate(user=self.player)
        response = self.client.get(self.attempts_url)
        data = response.data.get('results', response.data)
        self.assertEqual(len(data), 1)
