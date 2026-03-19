from django.contrib import admin
from .models import AIGenerationLog

@admin.register(AIGenerationLog)
class AIGenerationLogAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'provider', 'status', 'response_time_ms', 'created_at')
    list_filter = ('status', 'provider')
    readonly_fields = ('quiz', 'provider', 'prompt_sent', 'raw_response', 'error_message', 'response_time_ms', 'created_at')
    search_fields = ('quiz__title', 'error_message')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
