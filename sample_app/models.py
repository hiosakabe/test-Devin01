from django.db import models

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
