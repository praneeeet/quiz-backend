import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

class QuizAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        TIMED_OUT = 'timed_out', 'Timed Out'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quiz_attempts'
    )
    quiz = models.ForeignKey(
        'quizzes.Quiz',
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS
    )
    score = models.PositiveIntegerField(null=True, blank=True)
    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField(null=True, blank=True)
    score_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'quiz_attempts'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'quiz']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} ({self.status})"

    def calculate_score(self):
        correct_count = self.answers.filter(is_correct=True).count()
        self.correct_answers = correct_count
        self.score = correct_count
        if self.total_questions > 0:
            self.score_percentage = Decimal(correct_count) / Decimal(self.total_questions) * 100
        else:
            self.score_percentage = Decimal('0.00')
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save()
        return self

class AttemptAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    question = models.ForeignKey(
        'quizzes.Question',
        on_delete=models.CASCADE,
        related_name='attempt_answers'
    )
    selected_option = models.PositiveSmallIntegerField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'attempt_answers'
        ordering = ['answered_at']
        unique_together = ('attempt', 'question')
        indexes = [
            models.Index(fields=['question', 'is_correct']),
        ]

    def save(self, *args, **kwargs):
        if self.selected_option is not None:
            self.is_correct = (self.selected_option == self.question.correct_option)
        else:
            self.is_correct = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Answer for {self.question.question_text[:30]}"
