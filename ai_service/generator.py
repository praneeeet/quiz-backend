import json
import time
from groq import Groq
from django.conf import settings
from quizzes.models import Quiz, Question
from .models import AIGenerationLog

class QuizGenerator:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def generate_questions(self, quiz: Quiz):
        """
        Generates questions for a quiz using Groq AI.
        Updates quiz status through the lifecycle and logs the attempt.
        """
        quiz.status = Quiz.Status.GENERATING
        quiz.save()

        count = quiz.number_of_questions
        topic = quiz.topic
        difficulty = quiz.difficulty

        prompt = f"""Generate exactly {count} multiple choice questions about: {topic}
Difficulty level: {difficulty}

Rules:
- Each question must have exactly 4 options
- Only one option should be correct
- Provide a brief explanation for the correct answer
- Questions should be {difficulty} level appropriate

Respond ONLY with valid JSON in this exact format, no other text:
{{
    "questions": [
        {{
            "question_text": "What is ...?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_option": 0,
            "explanation": "Brief explanation"
        }}
    ]
}}

IMPORTANT: correct_option is a 0-based index (0, 1, 2, or 3). Respond with ONLY the JSON."""

        log = AIGenerationLog.objects.create(
            quiz=quiz,
            prompt_sent=prompt,
            status=AIGenerationLog.Status.PENDING
        )

        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[
                    {"role": "system", "content": "You are a quiz generator. Respond ONLY with valid JSON, no markdown, no code blocks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4096,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            raw_text = response.choices[0].message.content
            log.response_time_ms = duration_ms
            log.raw_response = raw_text

            # Strip markdown code blocks if present
            raw_text = raw_text.strip()
            if raw_text.startswith('```json'):
                raw_text = raw_text.replace('```json', '', 1)
                if raw_text.endswith('```'):
                    raw_text = raw_text[:-3]
            elif raw_text.startswith('```'):
                raw_text = raw_text.replace('```', '', 1)
                if raw_text.endswith('```'):
                    raw_text = raw_text[:-3]

            data = json.loads(raw_text.strip())
            questions_data = data.get('questions', [])

            new_questions = []
            for i, q_data in enumerate(questions_data):
                if len(q_data.get('options', [])) != 4:
                    print(f"Skipping question {i} due to invalid option count.")
                    continue

                correct_idx = q_data.get('correct_option')
                if not isinstance(correct_idx, int) or not (0 <= correct_idx <= 3):
                    print(f"Skipping question {i} due to invalid correct_option.")
                    continue

                new_questions.append(Question(
                    quiz=quiz,
                    question_text=q_data.get('question_text'),
                    options=q_data.get('options'),
                    correct_option=correct_idx,
                    explanation=q_data.get('explanation'),
                    order=i
                ))

            if new_questions:
                Question.objects.bulk_create(new_questions)
                quiz.status = Quiz.Status.READY
                log.status = AIGenerationLog.Status.SUCCESS
            else:
                quiz.status = Quiz.Status.FAILED
                log.status = AIGenerationLog.Status.FAILED
                log.error_message = "No valid questions were generated."

            quiz.save()
            log.save()
            return quiz.status == Quiz.Status.READY

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log.response_time_ms = duration_ms
            log.status = AIGenerationLog.Status.FAILED
            log.error_message = str(e)
            log.save()

            quiz.status = Quiz.Status.FAILED
            quiz.save()
            print(f"Generation failed: {str(e)}")
            return False
