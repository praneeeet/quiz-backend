from rest_framework import serializers
from .models import QuizAttempt, AttemptAnswer
from quizzes.serializers import QuestionSerializer, QuestionPlayerSerializer

class AttemptAnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    selected_option = serializers.IntegerField(min_value=0, max_value=3, required=False, allow_null=True)

    def validate_selected_option(self, value):
        if value is not None and (value < 0 or value > 3):
             raise serializers.ValidationError("Selected option must be between 0 and 3.")
        return value

class AttemptAnswerResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttemptAnswer
        fields = ('id', 'question_id', 'selected_option', 'is_correct', 'answered_at')

class AttemptAnswerDuringSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttemptAnswer
        fields = ('id', 'question_id', 'selected_option', 'answered_at')

class QuizAttemptListSerializer(serializers.ModelSerializer):
    quiz_title = serializers.SerializerMethodField()
    user = serializers.StringRelatedField()

    class Meta:
        model = QuizAttempt
        fields = (
            'id', 'quiz', 'quiz_title', 'user', 'status', 'score', 
            'total_questions', 'correct_answers', 'score_percentage', 
            'started_at', 'completed_at'
        )

    def get_quiz_title(self, obj):
        return obj.quiz.title

class QuizAttemptDetailSerializer(serializers.ModelSerializer):
    answers = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    quiz_title = serializers.SerializerMethodField()
    user = serializers.StringRelatedField()

    class Meta:
        model = QuizAttempt
        fields = (
            'id', 'quiz', 'quiz_title', 'user', 'status', 'score', 
            'total_questions', 'correct_answers', 'score_percentage', 
            'started_at', 'completed_at', 'answers', 'questions'
        )

    def get_quiz_title(self, obj):
        return obj.quiz.title

    def get_answers(self, obj):
        if obj.status == QuizAttempt.Status.COMPLETED:
            return AttemptAnswerResponseSerializer(obj.answers.all(), many=True).data
        return AttemptAnswerDuringSerializer(obj.answers.all(), many=True).data

    def get_questions(self, obj):
        questions = obj.quiz.questions.all()
        if obj.status == QuizAttempt.Status.COMPLETED:
            return QuestionSerializer(questions, many=True).data
        return QuestionPlayerSerializer(questions, many=True).data

class AttemptStartSerializer(serializers.Serializer):
    pass # No input data for start_attempt

class AttemptCompleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = (
            'id', 'quiz', 'status', 'score', 'total_questions', 
            'correct_answers', 'score_percentage', 'started_at', 'completed_at'
        )
        read_only_fields = fields
