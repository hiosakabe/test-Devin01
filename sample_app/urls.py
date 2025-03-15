from django.urls import path
from .views import index, quiz_start, quiz_question, quiz_result, quiz_host, quiz_join, quiz_session, quiz_api

urlpatterns = [
    path('', index, name='index'),
    path('quiz/', quiz_start, name='quiz_start'),
    path('quiz/question/', quiz_question, name='quiz_question'),
    path('quiz/result/', quiz_result, name='quiz_result'),
    path('quiz/host/', quiz_host, name='quiz_host'),
    path('quiz/join/', quiz_join, name='quiz_join'),
    path('quiz/session/<uuid:session_id>/', quiz_session, name='quiz_session'),
    path('quiz/api/<uuid:session_id>/', quiz_api, name='quiz_api'),
]
