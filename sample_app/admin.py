from django.contrib import admin
from .models import QuizCategory, QuizQuestion, QuizAnswer, QuizResult, QuizSession, QuizParticipant

admin.site.register(QuizCategory)
admin.site.register(QuizQuestion)
admin.site.register(QuizAnswer)
admin.site.register(QuizResult)
admin.site.register(QuizSession)
admin.site.register(QuizParticipant)
