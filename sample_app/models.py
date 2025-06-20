from django.db import models
from django.urls import reverse
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

class KaraokeScore(models.Model):
    player_name = models.CharField(max_length=100, verbose_name='プレイヤー名')
    song_title = models.CharField(max_length=200, verbose_name='楽曲名')
    artist_name = models.CharField(max_length=200, verbose_name='アーティスト名')
    
    total_score = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='総合得点')
    pitch_score = models.DecimalField(max_digits=5, decimal_places=3, verbose_name='音程得点')
    stability_score = models.DecimalField(max_digits=5, decimal_places=3, verbose_name='安定感得点')
    expression_score = models.DecimalField(max_digits=5, decimal_places=3, verbose_name='抑揚得点')
    long_tone_score = models.DecimalField(max_digits=5, decimal_places=3, verbose_name='ロングトーン得点')
    technique_score = models.DecimalField(max_digits=4, decimal_places=3, verbose_name='テクニック得点')
    
    overall_comment = models.TextField(verbose_name='総評', blank=True)
    kobushi_count = models.IntegerField(verbose_name='こぶし回数', default=0)
    shakuri_count = models.IntegerField(verbose_name='しゃくり回数', default=0)
    vibrato_count = models.IntegerField(verbose_name='ビブラート回数', default=0)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='記録日時')
    
    def __str__(self):
        return f"{self.player_name} - {self.song_title} ({self.total_score}点)"
    
    class Meta:
        verbose_name = 'カラオケ採点結果'
        verbose_name_plural = 'カラオケ採点結果'
        ordering = ['-created_at']
