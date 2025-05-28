from django.contrib import admin
from .models import GPTPromptConfig

@admin.register(GPTPromptConfig)
class GPTPromptConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'system_prompt', 'user_prompt')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        ('Prompts', {
            'fields': ('system_prompt', 'user_prompt'),
            'description': 'Configure the prompts used for GPT extraction. Use {format_instructions} in system prompt and {text_content} in user prompt.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
