from django.contrib import admin
from .models import Category, Quiz, Question

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ('question_text', 'options', 'correct_option', 'order')

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'topic', 'category', 'difficulty', 
        'status', 'is_published', 'created_by', 'created_at'
    )
    list_filter = ('difficulty', 'status', 'is_published', 'category')
    search_fields = ('title', 'topic')
    inlines = [QuestionInline]
