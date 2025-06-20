from django.urls import path
from . import views

app_name = 'uno_game'

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_game, name='create_game'),
    path('game/<uuid:game_id>/', views.game_room, name='game_room'),
    path('join/<uuid:game_id>/', views.join_game, name='join_game'),
    path('api/game/<uuid:game_id>/', views.game_api, name='game_api'),
]
