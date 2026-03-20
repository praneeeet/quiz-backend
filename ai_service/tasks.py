from celery import shared_task

@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def generate_quiz_questions_task(self, quiz_id):
    from quizzes.models import Quiz
    from .generator import QuizGenerator
    
    try:
        quiz = Quiz.objects.get(id=quiz_id)
        generator = QuizGenerator()
        generator.generate_questions(quiz)
    except Quiz.DoesNotExist:
        print(f"Quiz {quiz_id} not found")
    except Exception as exc:
        print(f"Task failed for quiz {quiz_id}: {exc}")
        raise self.retry(exc=exc)
