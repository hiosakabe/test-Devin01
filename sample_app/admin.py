from django.contrib import admin
from django.utils.html import format_html
from .models import (
    QuizCategory, QuizQuestion, QuizAnswer, QuizResult, QuizSession, QuizParticipant,
    KnowledgeCategory, KnowledgeArticle, KnowledgeTag, KnowledgeComment
)

admin.site.register(QuizCategory)
admin.site.register(QuizQuestion)
admin.site.register(QuizAnswer)
admin.site.register(QuizResult)
admin.site.register(QuizSession)
admin.site.register(QuizParticipant)


@admin.register(KnowledgeCategory)
class KnowledgeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'article_count', 'created_at')
    list_filter = ('parent', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = 'Articles'
    
    fieldsets = (
        (None, {
            'fields': ('name', 'parent', 'description')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at',)


@admin.register(KnowledgeTag)
class KnowledgeTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_preview', 'article_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    def color_preview(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color,
            obj.name
        )
    color_preview.short_description = 'Color Preview'
    
    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = 'Articles'


@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'status', 'featured', 'view_count', 'created_at')
    list_filter = ('status', 'featured', 'category', 'author', 'created_at', 'tags')
    search_fields = ('title', 'content', 'summary')
    ordering = ('-created_at',)
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'category', 'author', 'status')
        }),
        ('Content', {
            'fields': ('summary', 'content', 'tags', 'featured')
        }),
        ('Statistics', {
            'fields': ('view_count',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('view_count', 'created_at', 'updated_at')
    
    actions = ['make_published', 'make_draft', 'make_featured', 'remove_featured']
    
    def make_published(self, request, queryset):
        updated = queryset.update(status='published')
        self.message_user(request, f'{updated} articles were successfully marked as published.')
    make_published.short_description = "Mark selected articles as published"
    
    def make_draft(self, request, queryset):
        updated = queryset.update(status='draft')
        self.message_user(request, f'{updated} articles were successfully marked as draft.')
    make_draft.short_description = "Mark selected articles as draft"
    
    def make_featured(self, request, queryset):
        updated = queryset.update(featured=True)
        self.message_user(request, f'{updated} articles were successfully marked as featured.')
    make_featured.short_description = "Mark selected articles as featured"
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(featured=False)
        self.message_user(request, f'{updated} articles were successfully removed from featured.')
    remove_featured.short_description = "Remove featured status from selected articles"
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new article
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(KnowledgeComment)
class KnowledgeCommentAdmin(admin.ModelAdmin):
    list_display = ('article', 'author', 'content_preview', 'parent', 'created_at')
    list_filter = ('article', 'author', 'created_at')
    search_fields = ('content', 'article__title', 'author__username')
    ordering = ('-created_at',)
    raw_id_fields = ('article', 'parent')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    fieldsets = (
        (None, {
            'fields': ('article', 'author', 'parent', 'content')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    
    actions = ['delete_selected_comments']
    
    def delete_selected_comments(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} comments were successfully deleted.')
    delete_selected_comments.short_description = "Delete selected comments"


admin.site.site_header = "Knowledge Management System Admin"
admin.site.site_title = "Knowledge System Admin"
admin.site.index_title = "Welcome to Knowledge Management System Administration"
