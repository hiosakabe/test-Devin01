from django.db import models
import uuid
import random

class UnoGame(models.Model):
    STATUS_CHOICES = [
        ('waiting', '待機中'),
        ('in_progress', '進行中'),
        ('completed', '完了'),
    ]
    
    DIRECTION_CHOICES = [
        ('clockwise', '時計回り'),
        ('counterclockwise', '反時計回り'),
    ]
    
    game_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    host_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    current_player_index = models.IntegerField(default=0)
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='clockwise')
    current_color = models.CharField(max_length=10, null=True, blank=True)
    current_number = models.IntegerField(null=True, blank=True)
    current_action = models.CharField(max_length=20, null=True, blank=True)
    draw_pile = models.JSONField(default=list)
    discard_pile = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"UNO Game {self.game_id} ({self.get_status_display()})"
    
    def initialize_deck(self):
        """Initialize a standard UNO deck"""
        deck = []
        colors = ['red', 'yellow', 'green', 'blue']
        
        for color in colors:
            deck.append({'color': color, 'type': 'number', 'value': 0})
            for number in range(1, 10):
                deck.extend([{'color': color, 'type': 'number', 'value': number}] * 2)
        
        for color in colors:
            for action in ['skip', 'reverse', 'draw_two']:
                deck.extend([{'color': color, 'type': 'action', 'value': action}] * 2)
        
        for _ in range(4):
            deck.append({'color': 'wild', 'type': 'wild', 'value': 'wild'})
            deck.append({'color': 'wild', 'type': 'wild', 'value': 'wild_draw_four'})
        
        random.shuffle(deck)
        return deck
    
    def deal_initial_cards(self):
        """Deal 7 cards to each player"""
        if not self.draw_pile:
            self.draw_pile = self.initialize_deck()
        
        for player in self.players.all():
            hand = []
            for _ in range(7):
                if self.draw_pile:
                    hand.append(self.draw_pile.pop())
            player.hand = hand
            player.save()
        
        if self.draw_pile:
            first_card = self.draw_pile.pop()
            self.discard_pile = [first_card]
            self.current_color = first_card['color']
            if first_card['type'] == 'number':
                self.current_number = first_card['value']
            elif first_card['type'] == 'action':
                self.current_action = first_card['value']
        
        self.save()

class UnoPlayer(models.Model):
    game = models.ForeignKey(UnoGame, on_delete=models.CASCADE, related_name='players')
    name = models.CharField(max_length=100)
    hand = models.JSONField(default=list)
    position = models.IntegerField()
    has_called_uno = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['game', 'position']
        ordering = ['position']
    
    def __str__(self):
        return f"{self.name} in {self.game}"
    
    def card_count(self):
        return len(self.hand)
    
    def can_play_card(self, card, game):
        """Check if a card can be played given current game state"""
        if card['type'] == 'wild':
            return True
        
        if game.current_color == 'wild':
            return False
        
        if card['color'] == game.current_color:
            return True
        
        if card['type'] == 'number' and game.current_number is not None:
            return card['value'] == game.current_number
        
        if card['type'] == 'action' and game.current_action is not None:
            return card['value'] == game.current_action
        
        return False
