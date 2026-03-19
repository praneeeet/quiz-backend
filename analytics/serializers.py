from rest_framework import serializers

class UserStatsSerializer(serializers.Serializer):
    total_quizzes_attempted = serializers.IntegerField()
    total_completed = serializers.IntegerField()
    total_in_progress = serializers.IntegerField()
    average_score_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    best_score_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    total_questions_answered = serializers.IntegerField()
    correct_answers_total = serializers.IntegerField()
    overall_accuracy = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)

class CategoryPerformanceSerializer(serializers.Serializer):
    category_id = serializers.UUIDField(allow_null=True)
    category_name = serializers.CharField(allow_null=True)
    quizzes_attempted = serializers.IntegerField()
    average_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    best_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    total_attempts = serializers.IntegerField()

class QuestionBreakdownSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    question_text = serializers.CharField()
    total_answers = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    accuracy_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)

class QuizStatsSerializer(serializers.Serializer):
    quiz_id = serializers.UUIDField()
    quiz_title = serializers.CharField()
    total_attempts = serializers.IntegerField()
    total_completed = serializers.IntegerField()
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    average_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    highest_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    lowest_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    question_breakdown = serializers.ListField(child=serializers.DictField())

class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    user_id = serializers.UUIDField()
    username = serializers.CharField()
    total_quizzes_completed = serializers.IntegerField()
    average_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_correct_answers = serializers.IntegerField()

class SystemStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    total_quizzes = serializers.IntegerField()
    published_quizzes = serializers.IntegerField()
    total_attempts = serializers.IntegerField()
    completed_attempts = serializers.IntegerField()
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    most_popular_quizzes = serializers.ListField(child=serializers.DictField())
