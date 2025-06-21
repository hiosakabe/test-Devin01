from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/quiz/(?P<session_id>[0-9a-f-]+)/$', consumers.QuizConsumer.as_asgi()),
    
    re_path(r'ws/knowledge/article/(?P<article_slug>[\w-]+)/$', consumers.KnowledgeArticleConsumer.as_asgi()),
    re_path(r'ws/knowledge/system/$', consumers.KnowledgeSystemConsumer.as_asgi()),
]
