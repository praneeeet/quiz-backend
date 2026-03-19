from rest_framework import serializers
from .models import Category, Quiz, Question
from django.contrib.auth import get_user_model

User = get_user_model()

class CategorySerializer(serializers.ModelSerializer):
    quiz_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'created_at', 'quiz_count')
        read_only_fields = ('id', 'created_at')

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ('id', 'question_text', 'options', 'correct_option', 'explanation', 'order')

class QuestionPlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ('id', 'question_text', 'options', 'order')

class QuizListSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Quiz
        fields = (
            'id', 'title', 'topic', 'description', 'category', 'category_name', 
            'difficulty', 'number_of_questions', 'status', 'is_published', 
            'time_limit_seconds', 'created_by', 'created_at'
        )

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

class QuizDetailSerializer(QuizListSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta(QuizListSerializer.Meta):
        fields = QuizListSerializer.Meta.fields + ('questions',)

class QuizDetailPlayerSerializer(QuizListSerializer):
    """Quiz detail for players — hides correct answers"""
    questions = QuestionPlayerSerializer(many=True, read_only=True)

    class Meta(QuizListSerializer.Meta):
        fields = QuizListSerializer.Meta.fields + ('questions',)

class QuizCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = (
            'id', 'title', 'topic', 'description', 'category', 
            'difficulty', 'number_of_questions', 'time_limit_seconds'
        )
        read_only_fields = ('id',)

    def validate_number_of_questions(self, value):
        if value < 1 or value > 50:
            raise serializers.ValidationError("Number of questions must be between 1 and 50.")
        return value

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['status'] = Quiz.Status.PENDING
        return super().create(validated_data)

class QuizUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = (
            'title', 'description', 'category', 
            'difficulty', 'is_published', 'time_limit_seconds'
        )
