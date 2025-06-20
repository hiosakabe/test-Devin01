from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import UnoGame, UnoPlayer
import json
import uuid

def index(request):
    """Main page showing active games"""
    active_games = UnoGame.objects.filter(status__in=['waiting', 'in_progress']).order_by('-created_at')
    return render(request, 'uno_game/index.html', {'active_games': active_games})

def create_game(request):
    """Create a new UNO game"""
    if request.method == 'POST':
        host_name = request.POST.get('host_name', 'Host')
        game = UnoGame.objects.create(host_name=host_name)
        
        UnoPlayer.objects.create(
            game=game,
            name=host_name,
            position=0
        )
        
        request.session['player_name'] = host_name
        
        return redirect('uno_game:game_room', game_id=game.game_id)
    
    return render(request, 'uno_game/create_game.html')

def game_room(request, game_id):
    """Game room where players play UNO"""
    game = get_object_or_404(UnoGame, game_id=game_id)
    players = game.players.all().order_by('position')
    
    context = {
        'game': game,
        'players': players,
        'game_id': str(game.game_id),
    }
    
    return render(request, 'uno_game/game_room.html', context)

def join_game(request, game_id):
    """Join an existing game"""
    if request.method == 'POST':
        game = get_object_or_404(UnoGame, game_id=game_id)
        player_name = request.POST.get('player_name')
        
        if game.status != 'waiting':
            return JsonResponse({'error': 'Game already started'}, status=400)
        
        if game.players.count() >= 8:
            return JsonResponse({'error': 'Game is full'}, status=400)
        
        if game.players.filter(name=player_name).exists():
            return JsonResponse({'error': 'Player name already taken'}, status=400)
        
        position = game.players.count()
        UnoPlayer.objects.create(
            game=game,
            name=player_name,
            position=position
        )
        
        request.session['player_name'] = player_name
        
        return redirect('uno_game:game_room', game_id=game.game_id)
    
    game = get_object_or_404(UnoGame, game_id=game_id)
    return render(request, 'uno_game/join_game.html', {'game': game})

@csrf_exempt
def game_api(request, game_id):
    """API endpoint for game state"""
    game = get_object_or_404(UnoGame, game_id=game_id)
    
    if request.method == 'GET':
        players = []
        for player in game.players.all():
            players.append({
                'name': player.name,
                'card_count': len(player.hand),
                'position': player.position,
                'has_called_uno': player.has_called_uno
            })
        
        current_player_name = None
        if game.status == 'in_progress' and players:
            current_player_name = players[game.current_player_index]['name']
        
        return JsonResponse({
            'game_id': str(game.game_id),
            'status': game.status,
            'players': players,
            'current_player': current_player_name,
            'current_color': game.current_color,
            'current_number': game.current_number,
            'current_action': game.current_action,
            'direction': game.direction,
            'top_card': game.discard_pile[-1] if game.discard_pile else None,
            'draw_pile_count': len(game.draw_pile)
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
