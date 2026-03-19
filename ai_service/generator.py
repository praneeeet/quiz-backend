import json
import time
from django.conf import settings
from quizzes.models import Quiz
from .models import AIGenerationLog

class BaseQuizProvider:
    """Interface that all AI providers must implement"""
    name = 'base'
    
    def generate(self, topic, difficulty, count):
        """
        Call the AI API and return raw text response.
        Raises Exception on failure.
        """
        raise NotImplementedError

    def _build_prompt(self, topic, difficulty, count):
        return f"""Generate exactly {count} multiple choice questions about: {topic}
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

class GroqProvider(BaseQuizProvider):
    name = 'groq'
    
    def generate(self, topic, difficulty, count):
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {"role": "system", "content": "You are a quiz generator. Respond ONLY with valid JSON, no markdown, no code blocks."},
                {"role": "user", "content": self._build_prompt(topic, difficulty, count)}
            ],
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content

class GeminiProvider(BaseQuizProvider):
    name = 'gemini'
    
    def generate(self, topic, difficulty, count):
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Fix model name if needed, using gemini-2.0-flash
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(self._build_prompt(topic, difficulty, count))
        return response.text

class OpenRouterProvider(BaseQuizProvider):
    name = 'openrouter'
    
    def generate(self, topic, difficulty, count):
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
        response = client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages=[
                {"role": "system", "content": "You are a quiz generator. Respond ONLY with valid JSON, no markdown, no code blocks."},
                {"role": "user", "content": self._build_prompt(topic, difficulty, count)}
            ],
            temperature=0.7,
            max_tokens=4096,
        )
        return response.choices[0].message.content

class QuizGenerator:
    def __init__(self):
        self.providers = []
        # Only add providers that have API keys configured
        if settings.GROQ_API_KEY:
            self.providers.append(GroqProvider())
        if settings.GEMINI_API_KEY:
            self.providers.append(GeminiProvider())
        if settings.OPENROUTER_API_KEY:
            self.providers.append(OpenRouterProvider())
    
    def generate_questions(self, quiz):
        quiz.status = Quiz.Status.GENERATING
        quiz.save()
        
        count = quiz.number_of_questions
        topic = quiz.topic
        difficulty = quiz.difficulty
        
        for provider in self.providers:
            log = AIGenerationLog.objects.create(
                quiz=quiz,
                provider=provider.name,
                prompt_sent=provider._build_prompt(topic, difficulty, count),
                status=AIGenerationLog.Status.PENDING
            )
            
            start_time = time.time()
            try:
                raw_text = provider.generate(topic, difficulty, count)
                duration_ms = int((time.time() - start_time) * 1000)
                log.raw_response = raw_text
                log.response_time_ms = duration_ms
                
                # Parse and validate
                questions = self._parse_response(raw_text)
                
                if questions:
                    self._save_questions(quiz, questions)
                    quiz.status = Quiz.Status.READY
                    quiz.save()
                    log.status = AIGenerationLog.Status.SUCCESS
                    log.save()
                    return True  # Success - stop trying other providers
                else:
                    log.status = AIGenerationLog.Status.FAILED
                    log.error_message = f"No valid questions parsed from {provider.name} response"
                    log.save()
                    # Continue to next provider
                    
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                log.response_time_ms = duration_ms
                log.status = AIGenerationLog.Status.FAILED
                log.error_message = f"{provider.name} failed: {str(e)}"
                log.save()
                print(f"Provider {provider.name} failed: {str(e)}, trying next...")
                # Continue to next provider
        
        # All providers failed
        quiz.status = Quiz.Status.FAILED
        quiz.save()
        return False
    
    def _parse_response(self, raw_text):
        """Parse AI response into list of valid question dicts"""
        try:
            raw_text = raw_text.strip()
            # Strip markdown code blocks
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
            
            valid_questions = []
            for q in questions_data:
                # Basic validation
                if not q.get('question_text') or len(q.get('options', [])) != 4:
                    continue
                correct_idx = q.get('correct_option')
                if not isinstance(correct_idx, int) or not (0 <= correct_idx <= 3):
                    continue
                valid_questions.append(q)
            
            return valid_questions
        except Exception:
            return []
    
    def _save_questions(self, quiz, questions_data):
        """Bulk create Question objects from validated data"""
        from quizzes.models import Question
        new_questions = [
            Question(
                quiz=quiz,
                question_text=q.get('question_text'),
                options=q.get('options'),
                correct_option=q.get('correct_option'),
                explanation=q.get('explanation'),
                order=i
            )
            for i, q in enumerate(questions_data)
        ]
        Question.objects.bulk_create(new_questions)
