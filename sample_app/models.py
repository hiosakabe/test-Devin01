from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
import uuid

class QuizCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    def __str__(self):
        return self.name

class QuizQuestion(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', '簡単'),
        ('medium', '普通'),
        ('hard', '難しい'),
    ]
    
    category = models.ForeignKey(QuizCategory, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    
    def __str__(self):
        return self.question_text

class QuizAnswer(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.answer_text

class QuizResult(models.Model):
    player_name = models.CharField(max_length=100)
    score = models.IntegerField()
    date_taken = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.player_name}: {self.score}"

class QuizSession(models.Model):
    STATUS_CHOICES = [
        ('waiting', '待機中'),
        ('in_progress', '進行中'),
        ('completed', '完了'),
    ]
    
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    quiz_master = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    category = models.ForeignKey(QuizCategory, on_delete=models.CASCADE, related_name='sessions')
    current_question = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Session {self.session_id} ({self.get_status_display()})"
    
    def get_absolute_url(self):
        return reverse('quiz_session', kwargs={'session_id': self.session_id})

class QuizParticipant(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='participants')
    name = models.CharField(max_length=100)
    score = models.IntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} in {self.session}"


class KnowledgeCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Knowledge Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('knowledge_category', kwargs={'pk': self.pk})


class KnowledgeTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#007bff')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class KnowledgeArticle(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    content = models.TextField()
    summary = models.TextField(max_length=500, blank=True)
    category = models.ForeignKey(KnowledgeCategory, on_delete=models.CASCADE, related_name='articles')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles')
    tags = models.ManyToManyField(KnowledgeTag, blank=True, related_name='articles')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['status', '-updated_at']),
            models.Index(fields=['category', '-updated_at']),
            models.Index(fields=['author', '-updated_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('knowledge_article_detail', kwargs={'slug': self.slug})


class KnowledgeComment(models.Model):
    article = models.ForeignKey(KnowledgeArticle, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='knowledge_comments')
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['article', 'created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.article.title}"


class KnowledgeBookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    article = models.ForeignKey(KnowledgeArticle, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'article']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} bookmarked {self.article.title}"


class KnowledgeView(models.Model):
    article = models.ForeignKey(KnowledgeArticle, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='article_views')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    time_spent = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['article', '-viewed_at']),
        ]
    
    def __str__(self):
        user_info = self.user.username if self.user else self.ip_address
        return f"View by {user_info} on {self.article.title}"


class KnowledgeRevision(models.Model):
    article = models.ForeignKey(KnowledgeArticle, on_delete=models.CASCADE, related_name='revisions')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='revisions')
    title = models.CharField(max_length=200)
    content = models.TextField()
    summary = models.TextField(max_length=500, blank=True)
    change_summary = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['article', '-created_at']),
        ]
    
    def __str__(self):
        return f"Revision of {self.article.title} by {self.author.username}"
