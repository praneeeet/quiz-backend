from django.contrib import admin
from .models import QuizAttempt, AttemptAnswer

class AttemptAnswerInline(admin.TabularInline):
    model = AttemptAnswer
    extra = 0
    readonly_fields = ('question', 'selected_option', 'is_correct', 'answered_at')

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'status', 'score', 'score_percentage', 'total_questions', 'started_at', 'completed_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'quiz__title')
    readonly_fields = ('user', 'quiz', 'total_questions', 'status', 'score', 'correct_answers', 'score_percentage', 'started_at', 'completed_at')
    inlines = [AttemptAnswerInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
