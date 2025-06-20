import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import UnoGame, UnoPlayer
import random

class UnoGameConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'uno_{self.game_id}'
        
        await self.channel_layer.group_add(
            self.game_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )
    
    async def receive_json(self, content):
        message_type = content.get('type')
        
        if message_type == 'player_joined':
            player_name = content.get('name')
            await self.add_player(player_name)
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'player_joined',
                    'name': player_name,
                    'game_state': await self.get_game_state()
                }
            )
        
        elif message_type == 'start_game':
            await self.start_game()
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'game_started',
                    'game_state': await self.get_game_state()
                }
            )
        
        elif message_type == 'play_card':
            player_name = content.get('player_name')
            card = content.get('card')
            chosen_color = content.get('chosen_color')
            
            result = await self.play_card(player_name, card, chosen_color)
            if result['success']:
                await self.channel_layer.group_send(
                    self.game_group_name,
                    {
                        'type': 'card_played',
                        'player_name': player_name,
                        'card': card,
                        'game_state': await self.get_game_state(),
                        'winner': result.get('winner')
                    }
                )
            else:
                await self.send_json({
                    'type': 'error',
                    'message': result['error']
                })
        
        elif message_type == 'draw_card':
            player_name = content.get('player_name')
            result = await self.draw_card(player_name)
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'card_drawn',
                    'player_name': player_name,
                    'cards_drawn': result['cards_drawn'],
                    'game_state': await self.get_game_state()
                }
            )
        
        elif message_type == 'call_uno':
            player_name = content.get('player_name')
            await self.call_uno(player_name)
            await self.channel_layer.group_send(
                self.game_group_name,
                {
                    'type': 'uno_called',
                    'player_name': player_name
                }
            )
    
    async def player_joined(self, event):
        await self.send_json({
            'type': 'player_joined',
            'name': event['name'],
            'game_state': event['game_state']
        })
    
    async def game_started(self, event):
        await self.send_json({
            'type': 'game_started',
            'game_state': event['game_state']
        })
    
    async def card_played(self, event):
        await self.send_json({
            'type': 'card_played',
            'player_name': event['player_name'],
            'card': event['card'],
            'game_state': event['game_state'],
            'winner': event.get('winner')
        })
    
    async def card_drawn(self, event):
        await self.send_json({
            'type': 'card_drawn',
            'player_name': event['player_name'],
            'cards_drawn': event['cards_drawn'],
            'game_state': event['game_state']
        })
    
    async def uno_called(self, event):
        await self.send_json({
            'type': 'uno_called',
            'player_name': event['player_name']
        })
    
    @database_sync_to_async
    def add_player(self, player_name):
        game = UnoGame.objects.get(game_id=self.game_id)
        if game.status != 'waiting':
            return False
        
        existing_players = game.players.count()
        if existing_players >= 8:  # Max 8 players
            return False
        
        player, created = UnoPlayer.objects.get_or_create(
            game=game,
            name=player_name,
            defaults={'position': existing_players}
        )
        return created
    
    @database_sync_to_async
    def start_game(self):
        game = UnoGame.objects.get(game_id=self.game_id)
        if game.status != 'waiting' or game.players.count() < 2:
            return False
        
        game.status = 'in_progress'
        game.deal_initial_cards()
        return True
    
    @database_sync_to_async
    def play_card(self, player_name, card, chosen_color=None):
        game = UnoGame.objects.get(game_id=self.game_id)
        
        if game.status != 'in_progress':
            return {'success': False, 'error': 'Game not in progress'}
        
        try:
            player = game.players.get(name=player_name)
        except UnoPlayer.DoesNotExist:
            return {'success': False, 'error': 'Player not found'}
        
        current_player = game.players.all()[game.current_player_index]
        if player != current_player:
            return {'success': False, 'error': 'Not your turn'}
        
        if card not in player.hand:
            return {'success': False, 'error': 'Card not in hand'}
        
        if not player.can_play_card(card, game):
            return {'success': False, 'error': 'Invalid card play'}
        
        player.hand.remove(card)
        player.save()
        
        game.discard_pile.append(card)
        
        if card['type'] == 'wild':
            game.current_color = chosen_color or 'red'
            game.current_number = None
            game.current_action = card['value']
        else:
            game.current_color = card['color']
            if card['type'] == 'number':
                game.current_number = card['value']
                game.current_action = None
            else:
                game.current_action = card['value']
                game.current_number = None
        
        skip_next = False
        if card['value'] == 'skip':
            skip_next = True
        elif card['value'] == 'reverse':
            game.direction = 'counterclockwise' if game.direction == 'clockwise' else 'clockwise'
        elif card['value'] == 'draw_two':
            next_player = self._get_next_player(game)
            self._draw_cards_for_player(next_player, 2)
            skip_next = True
        elif card['value'] == 'wild_draw_four':
            next_player = self._get_next_player(game)
            self._draw_cards_for_player(next_player, 4)
            skip_next = True
        
        winner = None
        if len(player.hand) == 0:
            game.status = 'completed'
            winner = player.name
        
        if not winner:
            game.current_player_index = self._get_next_player_index(game, skip_next)
        
        game.save()
        
        return {'success': True, 'winner': winner}
    
    @database_sync_to_async
    def draw_card(self, player_name):
        game = UnoGame.objects.get(game_id=self.game_id)
        
        try:
            player = game.players.get(name=player_name)
        except UnoPlayer.DoesNotExist:
            return {'cards_drawn': 0}
        
        current_player = game.players.all()[game.current_player_index]
        if player != current_player:
            return {'cards_drawn': 0}
        
        cards_drawn = self._draw_cards_for_player(player, 1)
        
        game.current_player_index = self._get_next_player_index(game, False)
        game.save()
        
        return {'cards_drawn': cards_drawn}
    
    @database_sync_to_async
    def call_uno(self, player_name):
        try:
            game = UnoGame.objects.get(game_id=self.game_id)
            player = game.players.get(name=player_name)
            player.has_called_uno = True
            player.save()
        except (UnoGame.DoesNotExist, UnoPlayer.DoesNotExist):
            pass
    
    @database_sync_to_async
    def get_game_state(self):
        game = UnoGame.objects.get(game_id=self.game_id)
        players = []
        
        for player in game.players.all():
            players.append({
                'name': player.name,
                'card_count': len(player.hand),
                'hand': player.hand,
                'position': player.position,
                'has_called_uno': player.has_called_uno
            })
        
        current_player_name = None
        if game.status == 'in_progress' and players:
            current_player_name = players[game.current_player_index]['name']
        
        return {
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
        }
    
    def _get_next_player(self, game):
        next_index = self._get_next_player_index(game, False)
        return game.players.all()[next_index]
    
    def _get_next_player_index(self, game, skip_next=False):
        player_count = game.players.count()
        if player_count <= 1:
            return 0
        
        if game.direction == 'clockwise':
            next_index = (game.current_player_index + 1) % player_count
        else:
            next_index = (game.current_player_index - 1) % player_count
        
        if skip_next:
            if game.direction == 'clockwise':
                next_index = (next_index + 1) % player_count
            else:
                next_index = (next_index - 1) % player_count
        
        return next_index
    
    def _draw_cards_for_player(self, player, count):
        game = player.game
        cards_drawn = 0
        
        for _ in range(count):
            if not game.draw_pile:
                if len(game.discard_pile) > 1:
                    top_card = game.discard_pile.pop()
                    game.draw_pile = game.discard_pile[:-1]
                    game.discard_pile = [top_card]
                    random.shuffle(game.draw_pile)
                else:
                    break
            
            if game.draw_pile:
                card = game.draw_pile.pop()
                player.hand.append(card)
                cards_drawn += 1
        
        player.save()
        game.save()
        return cards_drawn
