from django.urls import path
from .views import index, quiz_start, quiz_question, quiz_result

urlpatterns = [
    path('', index, name='index'),
    path('quiz/', quiz_start, name='quiz_start'),
    path('quiz/question/', quiz_question, name='quiz_question'),
    path('quiz/result/', quiz_result, name='quiz_result'),
]
