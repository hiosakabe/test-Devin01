from django.urls import path
from .views import (
    index, quiz_start, quiz_question, quiz_result, quiz_host, quiz_join, quiz_session, quiz_api,
    knowledge_home, knowledge_search, knowledge_article_list, knowledge_article_detail, knowledge_article_create,
    knowledge_article_edit, knowledge_article_delete, knowledge_category_list, knowledge_category_detail,
    knowledge_bookmark_toggle, knowledge_bookmarks, knowledge_api
)

urlpatterns = [
    path('', index, name='index'),
    path('quiz/', quiz_start, name='quiz_start'),
    path('quiz/question/', quiz_question, name='quiz_question'),
    path('quiz/result/', quiz_result, name='quiz_result'),
    path('quiz/host/', quiz_host, name='quiz_host'),
    path('quiz/join/', quiz_join, name='quiz_join'),
    path('quiz/session/<uuid:session_id>/', quiz_session, name='quiz_session'),
    path('quiz/api/<uuid:session_id>/', quiz_api, name='quiz_api'),
    
    path('knowledge/', knowledge_home, name='knowledge_home'),
    path('knowledge/search/', knowledge_search, name='knowledge_search'),
    path('knowledge/articles/', knowledge_article_list, name='knowledge_article_list'),
    path('knowledge/articles/create/', knowledge_article_create, name='knowledge_article_create'),
    path('knowledge/articles/<slug:slug>/', knowledge_article_detail, name='knowledge_article_detail'),
    path('knowledge/articles/<slug:slug>/edit/', knowledge_article_edit, name='knowledge_article_edit'),
    path('knowledge/articles/<slug:slug>/delete/', knowledge_article_delete, name='knowledge_article_delete'),
    path('knowledge/categories/', knowledge_category_list, name='knowledge_category_list'),
    path('knowledge/categories/<int:pk>/', knowledge_category_detail, name='knowledge_category_detail'),
    path('knowledge/bookmark/<slug:slug>/', knowledge_bookmark_toggle, name='knowledge_bookmark_toggle'),
    path('knowledge/bookmarks/', knowledge_bookmarks, name='knowledge_bookmarks'),
    path('knowledge/api/', knowledge_api, name='knowledge_api'),
]
