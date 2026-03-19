import uuid
from django.db import models
from quizzes.models import Quiz

class AIGenerationLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        TIMEOUT = 'timeout', 'Timeout'
        PENDING = 'pending', 'Pending'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='generation_logs'
    )
    provider = models.CharField(max_length=50, default='groq')
    prompt_sent = models.TextField()
    raw_response = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    response_time_ms = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_generation_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Log for Quiz {self.quiz.title} ({self.status})"
