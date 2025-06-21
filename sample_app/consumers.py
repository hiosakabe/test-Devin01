import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import QuizSession, QuizParticipant, QuizQuestion, QuizAnswer, KnowledgeArticle, KnowledgeComment

class QuizConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.session_group_name = f'quiz_{self.session_id}'
        
        # Join session group
        await self.channel_layer.group_add(
            self.session_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave session group
        await self.channel_layer.group_discard(
            self.session_group_name,
            self.channel_name
        )
    
    async def receive_json(self, content):
        message_type = content.get('type')
        
        if message_type == 'participant_joined':
            # Handle participant joining
            participant_name = content.get('name')
            await self.channel_layer.group_send(
                self.session_group_name,
                {
                    'type': 'participant_joined',
                    'name': participant_name
                }
            )
        elif message_type == 'question_start':
            # Handle starting a question
            question_index = content.get('question_index')
            await self.update_session_question(question_index)
            question_data = await self.get_question_data(question_index)
            await self.channel_layer.group_send(
                self.session_group_name,
                {
                    'type': 'question_start',
                    'question': question_data
                }
            )
        elif message_type == 'answer_submitted':
            # Handle answer submission
            participant_name = content.get('name')
            answer_id = content.get('answer_id')
            is_correct = await self.check_answer(answer_id)
            if is_correct:
                await self.update_participant_score(participant_name)
            await self.channel_layer.group_send(
                self.session_group_name,
                {
                    'type': 'answer_submitted',
                    'name': participant_name,
                    'is_correct': is_correct
                }
            )
        elif message_type == 'question_end':
            # Handle ending a question
            await self.channel_layer.group_send(
                self.session_group_name,
                {
                    'type': 'question_end',
                    'correct_answer': content.get('correct_answer')
                }
            )
        elif message_type == 'session_end':
            # Handle ending the session
            await self.update_session_status('completed')
            await self.channel_layer.group_send(
                self.session_group_name,
                {
                    'type': 'session_end',
                    'results': await self.get_session_results()
                }
            )
    
    async def participant_joined(self, event):
        await self.send_json({
            'type': 'participant_joined',
            'name': event['name']
        })
    
    async def question_start(self, event):
        await self.send_json({
            'type': 'question_start',
            'question': event['question']
        })
    
    async def answer_submitted(self, event):
        await self.send_json({
            'type': 'answer_submitted',
            'name': event['name'],
            'is_correct': event['is_correct']
        })
    
    async def question_end(self, event):
        await self.send_json({
            'type': 'question_end',
            'correct_answer': event['correct_answer']
        })
    
    async def session_end(self, event):
        await self.send_json({
            'type': 'session_end',
            'results': event['results']
        })
    
    @database_sync_to_async
    def update_session_question(self, question_index):
        session = QuizSession.objects.get(session_id=self.session_id)
        session.current_question = question_index
        session.save()
    
    @database_sync_to_async
    def update_session_status(self, status):
        session = QuizSession.objects.get(session_id=self.session_id)
        session.status = status
        session.save()
    
    @database_sync_to_async
    def get_question_data(self, question_index):
        session = QuizSession.objects.get(session_id=self.session_id)
        questions = QuizQuestion.objects.filter(category=session.category)
        if question_index < questions.count():
            question = questions[question_index]
            answers = question.answers.all()
            return {
                'id': question.id,
                'text': question.question_text,
                'answers': [{'id': answer.id, 'text': answer.answer_text} for answer in answers]
            }
        return None
    
    @database_sync_to_async
    def check_answer(self, answer_id):
        answer = QuizAnswer.objects.get(id=answer_id)
        return answer.is_correct
    
    @database_sync_to_async
    def update_participant_score(self, participant_name):
        session = QuizSession.objects.get(session_id=self.session_id)
        participant = QuizParticipant.objects.get(session=session, name=participant_name)
        participant.score += 1
        participant.save()
    
    @database_sync_to_async
    def get_session_results(self):
        session = QuizSession.objects.get(session_id=self.session_id)
        participants = session.participants.all().order_by('-score')
        return [{'name': participant.name, 'score': participant.score} for participant in participants]


class KnowledgeArticleConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for real-time article collaboration features"""
    
    async def connect(self):
        self.article_slug = self.scope['url_route']['kwargs']['article_slug']
        self.article_group_name = f'article_{self.article_slug}'
        self.user = self.scope['user']
        
        await self.channel_layer.group_add(
            self.article_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        if self.user.is_authenticated:
            await self.channel_layer.group_send(
                self.article_group_name,
                {
                    'type': 'user_joined',
                    'user': self.user.username,
                    'user_id': self.user.id
                }
            )
    
    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_send(
                self.article_group_name,
                {
                    'type': 'user_left',
                    'user': self.user.username,
                    'user_id': self.user.id
                }
            )
        
        await self.channel_layer.group_discard(
            self.article_group_name,
            self.channel_name
        )
    
    async def receive_json(self, content):
        message_type = content.get('type')
        
        if message_type == 'new_comment':
            comment_data = content.get('comment')
            if self.user.is_authenticated:
                comment = await self.create_comment(comment_data)
                await self.channel_layer.group_send(
                    self.article_group_name,
                    {
                        'type': 'comment_added',
                        'comment': comment
                    }
                )
        
        elif message_type == 'editing_start':
            section = content.get('section', 'content')
            if self.user.is_authenticated:
                await self.channel_layer.group_send(
                    self.article_group_name,
                    {
                        'type': 'editing_started',
                        'user': self.user.username,
                        'user_id': self.user.id,
                        'section': section
                    }
                )
        
        elif message_type == 'editing_stop':
            section = content.get('section', 'content')
            if self.user.is_authenticated:
                await self.channel_layer.group_send(
                    self.article_group_name,
                    {
                        'type': 'editing_stopped',
                        'user': self.user.username,
                        'user_id': self.user.id,
                        'section': section
                    }
                )
        
        elif message_type == 'typing_indicator':
            is_typing = content.get('is_typing', False)
            if self.user.is_authenticated:
                await self.channel_layer.group_send(
                    self.article_group_name,
                    {
                        'type': 'user_typing',
                        'user': self.user.username,
                        'user_id': self.user.id,
                        'is_typing': is_typing
                    }
                )
        
        elif message_type == 'article_updated':
            # Handle article content updates
            if self.user.is_authenticated:
                update_data = content.get('update')
                await self.channel_layer.group_send(
                    self.article_group_name,
                    {
                        'type': 'article_content_updated',
                        'user': self.user.username,
                        'user_id': self.user.id,
                        'update': update_data
                    }
                )
    
    async def user_joined(self, event):
        await self.send_json({
            'type': 'user_joined',
            'user': event['user'],
            'user_id': event['user_id']
        })
    
    async def user_left(self, event):
        await self.send_json({
            'type': 'user_left',
            'user': event['user'],
            'user_id': event['user_id']
        })
    
    async def comment_added(self, event):
        await self.send_json({
            'type': 'comment_added',
            'comment': event['comment']
        })
    
    async def editing_started(self, event):
        if event['user_id'] != self.user.id:
            await self.send_json({
                'type': 'editing_started',
                'user': event['user'],
                'user_id': event['user_id'],
                'section': event['section']
            })
    
    async def editing_stopped(self, event):
        if event['user_id'] != self.user.id:
            await self.send_json({
                'type': 'editing_stopped',
                'user': event['user'],
                'user_id': event['user_id'],
                'section': event['section']
            })
    
    async def user_typing(self, event):
        if event['user_id'] != self.user.id:
            await self.send_json({
                'type': 'user_typing',
                'user': event['user'],
                'user_id': event['user_id'],
                'is_typing': event['is_typing']
            })
    
    async def article_content_updated(self, event):
        if event['user_id'] != self.user.id:
            await self.send_json({
                'type': 'article_content_updated',
                'user': event['user'],
                'user_id': event['user_id'],
                'update': event['update']
            })
    
    @database_sync_to_async
    def create_comment(self, comment_data):
        try:
            article = KnowledgeArticle.objects.get(slug=self.article_slug)
            comment = KnowledgeComment.objects.create(
                article=article,
                author=self.user,
                content=comment_data.get('content', ''),
                parent_id=comment_data.get('parent_id')
            )
            return {
                'id': comment.id,
                'content': comment.content,
                'author': comment.author.username,
                'author_id': comment.author.id,
                'created_at': comment.created_at.isoformat(),
                'parent_id': comment.parent_id
            }
        except Exception as e:
            return None


class KnowledgeSystemConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for general knowledge system notifications"""
    
    async def connect(self):
        self.user = self.scope['user']
        
        if self.user.is_authenticated:
            self.user_group_name = f'user_{self.user.id}'
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            
            self.system_group_name = 'knowledge_system'
            await self.channel_layer.group_add(
                self.system_group_name,
                self.channel_name
            )
            
            await self.accept()
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            await self.channel_layer.group_discard(
                self.system_group_name,
                self.channel_name
            )
    
    async def receive_json(self, content):
        message_type = content.get('type')
        
        if message_type == 'ping':
            # Handle ping for connection health
            await self.send_json({
                'type': 'pong',
                'timestamp': content.get('timestamp')
            })
    
    async def article_published(self, event):
        await self.send_json({
            'type': 'article_published',
            'article': event['article'],
            'author': event['author']
        })
    
    async def article_updated(self, event):
        await self.send_json({
            'type': 'article_updated',
            'article': event['article'],
            'author': event['author']
        })
    
    async def new_comment_notification(self, event):
        await self.send_json({
            'type': 'new_comment_notification',
            'article': event['article'],
            'comment_author': event['comment_author'],
            'comment_preview': event['comment_preview']
        })
